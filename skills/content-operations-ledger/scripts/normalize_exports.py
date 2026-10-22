#!/usr/bin/env python3
"""Normalize official platform exports plus separately observed inventory identity/state.
Only stdlib is needed; XLSX is read, never authored. No network or browser control.
"""
import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def xlsx_rows(path):
    with zipfile.ZipFile(path) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS)]
        # Official exports handled here use their first worksheet, named Sheet1.
        sheets=sorted(n for n in z.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+.xml',n))
        if not sheets:raise ValueError('XLSX无工作表')
        out=[]
        for row in ET.fromstring(z.read(sheets[0])).findall('.//m:sheetData/m:row',NS):
            cells={}
            for c in row.findall('m:c',NS):
                col=re.match(r'[A-Z]+',c.attrib['r'])[0];i=0
                for letter in col:i=i*26+ord(letter)-64
                t=c.attrib.get('t');v=c.find('m:v',NS)
                if t=='inlineStr':value=''.join(c.find('m:is',NS).itertext())
                elif t=='s':value=strings[int(v.text)]
                else:value=v.text if v is not None and v.text else ''
                cells[i-1]=value
            out.append([cells.get(i,'') for i in range(max(cells,default=-1)+1)])
        # Official exports sometimes write duplicate strings into covered merged cells.
        # Match the visible worksheet / openpyxl semantics: only the top-left cell exists.
        def coordinate(ref):
            match=re.fullmatch(r'([A-Z]+)([0-9]+)',ref);col=0
            for letter in match[1]:col=col*26+ord(letter)-64
            return int(match[2])-1,col-1
        for merged in ET.fromstring(z.read(sheets[0])).findall('.//m:mergeCell',NS):
            first,last=merged.attrib['ref'].split(':');r0,c0=coordinate(first);r1,c1=coordinate(last)
            for r in range(r0,min(r1+1,len(out))):
                for c in range(c0,min(c1+1,len(out[r]))):
                    if (r,c)!=(r0,c0):out[r][c]=''
        return out

def iso_date(text,tz):
    if not text:return ''
    if '年' in text:
        n=list(map(int,re.findall(r'\d+',text)));return datetime(*n,tzinfo=tz).isoformat(timespec='seconds')
    d=datetime.fromisoformat(text.replace('Z','+00:00'))
    return (d.replace(tzinfo=tz) if not d.tzinfo else d.astimezone(tz)).isoformat(timespec='seconds')

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--config',type=Path,required=True);a.add_argument('--manifest',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    root=args.root.resolve();cfg=json.loads(args.config.read_text());tz=ZoneInfo(cfg['timezone']);manifest=json.loads(args.manifest.read_text())
    existing=list(csv.DictReader((root/cfg['paths']['publications']).open()))
    items=list(csv.DictReader((root/cfg['paths']['content_index']).open()))
    seq=max([int(p['id'].split('-')[-1]) for p in existing]+[0])+1
    sources={};patches={};metrics=[];checks=[];tasks=list(manifest.get('maintenance',[]));inventory_lookup={}
    def source(path):
        p=root/path
        if not p.is_file():raise ValueError('缺原件：'+str(p))
        sources[path]={'path':path,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        return path
    def find_pub(acc,title,native=''):
        candidates=[p for p in existing if p['platform_account_id']==acc and p['status']!='cancelled']
        exact=[p for p in candidates if native and p.get('native_id')==native]
        if not exact:exact=[p for p in candidates if p.get('title')==title]
        if not exact:
            for p in candidates:
                item=next((i for i in items if i['id']==p['item_id']),None)
                if not item:continue
                path=root/item['artifact_path'];jp=path if path.suffix=='.json' else path.parent/'item.json'
                if jp.is_file() and json.loads(jp.read_text()).get('copy',{}).get('post_title')==title:exact.append(p)
        if len(exact)>1:raise ValueError('标题匹配不唯一，需核对原生ID／日期：'+title)
        return exact[0] if exact else None
    for inv in manifest['inventories']:
        acc=inv['platform_account_id'];assert acc in cfg['platform_accounts']
        source(inv['source_path']);source(inv['identity_evidence'])
        assert len(inv['cards'])==int(inv['observed_total']),'未覆盖全部分页／懒加载'
        for c in inv['cards']:
            native=c.get('native_id','');title=c['title'];old=find_pub(acc,title,native)
            if old is None:
                old={'id':f'pub-{seq:03d}','item_id':'','platform_account_id':acc,'status':''};seq+=1;existing.append(old)
            pid=old['id'];captured=c.get('captured_at') or inv['captured_at'];proof=c.get('evidence_path') or inv['source_path'];source(proof)
            scope=c.get('scope') or old.get('scope') or ('legacy-account' if c.get('published_at','')[:10] < (cfg.get('legacy_before') or '0000') and c.get('published_at') else cfg.get('primary_scope','project'))
            p=dict(id=pid,item_id=old['item_id'],platform_account_id=acc,title=title,status=c['status'],content_type=c.get('content_type',''),scope=scope,visibility=c.get('visibility','unknown'),last_verified_at=captured,evidence_path=proof,verification_level='creator-manager-live',platform_review_status=c.get('platform_review_status') or c['status'],identity_basis=c.get('identity_basis') or ('原生ID／平台链接' if native else '标题＋首次发表时间＋时长，后台未提供原生ID'))
            if native:p['native_id']=native
            elif old.get('native_id')==cfg['platform_accounts'][acc].get('native_id') and sum(x.get('native_id')==old.get('native_id') and x['platform_account_id']==acc for x in existing)>1:
                p['native_id']=''
                p['identity_basis']+='；旧稿件native_id实际误填成账号ID，已清空，旧值保留在变更回执与旧账'
            if c.get('url'):p['url']=c['url']
            if c.get('scheduled_at'):p['scheduled_at']=c['scheduled_at'];p['published_at']=''
            if c.get('published_at'):
                when=iso_date(c['published_at'],tz);precision=c.get('timestamp_precision','minute')
                if precision=='minute' and old.get('published_at') and old['published_at'][:16]==when[:16]:when=old['published_at'];precision=old.get('timestamp_precision') or 'second'
                p.update(published_at=when,timestamp_precision=precision)
            if scope=='legacy-account':p['notes']='账号历史；没有本地制作包，不伪造item，不混入项目内容效果'
            patches[pid]=p;inventory_lookup[acc,title]=pid
        checks.append(dict(id=inv['check_id'],platform_account_id=acc,captured_at=inv['captured_at'],observed_total=str(inv['observed_total']),observed_published=str(sum(c['status']=='published' for c in inv['cards'])),observed_scheduled=str(sum(c['status']=='scheduled' for c in inv['cards'])),observed_private=str(sum(c.get('visibility')=='private' for c in inv['cards'])),evidence_path=inv['source_path'],identity_evidence=inv['identity_evidence'],notes=inv['notes']))
    def resolve(acc,title,native=''):
        if native:
            ps=[p for p in patches.values() if p['platform_account_id']==acc and p.get('native_id')==native]
        else:
            ps=[p for p in patches.values() if p['platform_account_id']==acc and (title==p['title'] or title.startswith(p['title']+' '))]
        if len(ps)!=1:raise ValueError('导出行无法唯一关联：'+title+' / '+native)
        return ps[0]
    def add(p,name,value,unit,ex,kind='cumulative',start='',end='',window=''):
        if value in ('','-',None):return
        value=str(value)
        if value.endswith('%'):value=format(float(value[:-1])/100,'.12g')
        float(value)
        target=''
        if kind in ('cumulative','rolling') and p.get('published_at') and p.get('scope','project')==cfg.get('primary_scope','project') and p.get('visibility')!='private':
            age=(datetime.fromisoformat(ex['captured_at'].replace('Z','+00:00'))-datetime.fromisoformat(p['published_at'])).total_seconds()/3600
            candidates=[h for h in cfg.get('observation_hours',[24,72,168]) if abs(age-h)<=cfg.get('observation_tolerance_hours',4)]
            target=str(min(candidates,key=lambda h:abs(age-h))) if candidates else ''
        metrics.append(dict(subject_type='publication',subject_id=p['id'],metric=name,value=value,unit=unit,captured_at=ex['captured_at'],source=ex['path'],window=window or '官方导出累计；本次采集；数据可能延迟，非历史D+N',window_kind=kind,period_start=start,period_end=end,data_as_of=ex.get('data_as_of','') or end,source_kind='official-export',capture_precision=ex.get('capture_precision','actual-download'),observation_target_hours=target))
    for ex in manifest['exports']:
        source(ex['path']);acc=ex['platform_account_id'];platform=cfg['platform_accounts'][acc]['platform']
        if ex.get('unit_evidence_path'):source(ex['unit_evidence_path'])
        if platform in ('xiaohongshu','douyin'):
            rows=xlsx_rows(root/ex['path']);header='笔记标题' if platform=='xiaohongshu' else '作品名称';pos=next(i for i,r in enumerate(rows) if r and r[0]==header);headers=rows[pos]
            mapping={'曝光':('impression_count','次'),'观看量':('view_count','次'),'封面点击率':('cover_ctr','ratio'),'点赞':('like_count','次'),'评论':('comment_count','次'),'收藏':('favorite_count','次'),'涨粉':('follower_gain','人'),'分享':('share_count','次'),'弹幕':('danmaku_count','次'),'播放量':('view_count','次'),'完播率':('completion_rate','ratio'),'5s完播率':('completion_5s_rate','ratio'),'2s跳出率':('skip_2s_rate','ratio'),'点赞量':('like_count','次'),'分享量':('share_count','次'),'评论量':('comment_count','次'),'收藏量':('favorite_count','次'),'主页访问量':('profile_visit_count','次'),'粉丝增量':('follower_gain','人')}
            for raw in rows[pos+1:]:
                if not raw or not raw[0]:continue
                row=dict(zip(headers,raw));p=resolve(acc,raw[0]);date=row.get('首次发布时间') or row.get('发布时间')
                p.update(published_at=iso_date(date,tz),timestamp_precision='second',last_verified_at=ex['captured_at'],evidence_path=ex['path'],verification_level='creator-export-live')
                for label,(name,unit) in mapping.items():
                    if label in row:add(p,name,row[label],unit,ex)
                for label in ('人均观看时长','平均播放时长'):
                    if label in row:
                        seconds=ex.get('watch_duration_unit')=='seconds' and ex.get('unit_evidence_path')
                        add(p,'avg_watch_seconds' if seconds else 'avg_watch_duration_raw',row[label],'秒' if seconds else '原值，单位未注明',ex)
        elif platform=='bilibili':
            p=resolve(acc,'',ex['native_id']);raw=list(csv.DictReader((root/ex['path']).open(encoding='utf-8-sig',newline='')))
            assert raw and '时间' in raw[0]
            daily=[r for r in raw if r['时间']!='累计'];dates=[datetime.strptime(r['时间'],'%Y/%m/%d').date().isoformat() for r in daily]
            start=min(dates) if dates else '';end=max(dates) if dates else ''
            summary=next(r for r in raw if r['时间']=='累计')
            ex={**ex,'data_as_of':end}
            mapping={'播放量':('view_count','次'),'涨粉':('follower_gain','人'),'取关':('unfollow_count','人'),'点赞':('like_count','次'),'弹幕':('danmaku_count','次'),'评论':('comment_count','次'),'分享':('share_count','次'),'收藏':('favorite_count','次'),'投币':('coin_count','次')}
            for label,(name,unit) in mapping.items():
                add(p,name,summary.get(label),unit,ex,'rolling',start,end,f'官方CSV所选范围合计；{start or "尚无日期"}—{end or "尚无日期"}；非生命周期累计')
            for row,date in zip(daily,dates):
                if p.get('published_at') and date<p['published_at'][:10]:continue # padded pre-publication zeros are not activity
                for label,(name,unit) in mapping.items():add(p,name,row.get(label),unit,ex,'daily',date,date,f'官方CSV逐日值；{date}；不与范围合计重复相加')
        else:raise ValueError('此格式尚无适配：'+platform)
    for availability in manifest.get('metric_availability',[]):
        evidence=source(availability['evidence_path'])
        p=resolve(availability['platform_account_id'],availability.get('title',''),availability.get('native_id',''))
        for m in metrics:
            if m['subject_id']==p['id'] and m['metric'] in availability['metrics']:
                m.update(quality=availability['quality'],quality_reason=availability['reason'],quality_evidence=evidence)
    for f in manifest.get('extra_sources',[]):source(f)
    for t in tasks:
        if t.get('evidence_path'):source(t['evidence_path'])
    snapshot=dict(schema_version=1,snapshot_id=manifest['snapshot_id'],sources=list(sources.values()),publications=list(patches.values()),metrics=metrics,checks=checks,maintenance=tasks)
    args.out.parent.mkdir(parents=True,exist_ok=True);payload=json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n'
    if args.out.exists() and args.out.read_text()!=payload:raise ValueError('输出已存在且内容不同；新一轮使用新运行ID，不覆盖旧快照')
    args.out.write_text(payload)
    print(json.dumps({'publication_patches':len(patches),'metric_values':len(metrics),'official_exports':len(manifest['exports']),'checks':len(checks)},ensure_ascii=False))

if __name__=='__main__':main()
