#!/usr/bin/env python3
"""Portable local ledger. Platform acquisition is deliberately outside this engine."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PUB_FIELDS = 'id item_id platform_account_id status published_at url evidence_path title content_type native_id planned_at scheduled_at submitted_at last_verified_at platform_review_status verification_level notes scope visibility timestamp_precision identity_basis'.split()
MET_FIELDS = 'id subject_type subject_id metric value unit captured_at source window window_kind observation_target_hours capture_precision period_start period_end data_as_of source_kind quality quality_reason quality_evidence'.split()
CHECK_FIELDS = 'id platform_account_id captured_at observed_total observed_published observed_scheduled observed_private evidence_path identity_evidence notes'.split()
TASK_FIELDS = 'id platform_account_id publication_id kind state reason next_action next_check_at evidence_path updated_at'.split()
STATE = {'planned':'计划／未提交','draft-uploaded':'草稿已上传','submitted':'已提交／待核','scheduled':'已定时','published':'已发表','failed':'失败','cancelled':'已取消','removed':'已下架／删除'}
VIS = {'public':'公开','private':'仅自己可见','friends':'限定可见','unknown':'可见性未核','':'可见性未核'}
BEGIN, END = '<!-- BEGIN GENERATED -->', '<!-- END GENERATED -->'
LABELS = {'impression_count':'曝光','view_count':'观看／播放','like_count':'赞','favorite_count':'藏','comment_count':'评','share_count':'分享','follower_gain':'涨粉','cover_ctr':'封面点击率','completion_rate':'完播率','completion_5s_rate':'5秒完播率','skip_2s_rate':'2秒跳出率','average_play_ratio':'平均播放占比','avg_watch_seconds':'平均观看时长（秒）','avg_watch_duration_raw':'平均观看时长原值（单位待核）','profile_visit_count':'主页访问','coin_count':'投币','danmaku_count':'弹幕','follower_count':'粉丝总数','unfollow_count':'取关'}

def clean(x):
    return str(x if x not in ('',None) else '—').replace('|','｜').replace('\n',' ')

def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def read_csv(path):
    if not path.exists():return [],[]
    with path.open(newline='') as f:
        r=csv.DictReader(f);return list(r.fieldnames),list(r)

def csv_bytes(fields, rows):
    f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);return f.getvalue().encode()

def commit_files(files):
    """Stage first, then replace; restore previous bytes if a local write fails."""
    changed={p:b for p,b in files.items() if not p.exists() or p.read_bytes()!=b}
    before={p:p.read_bytes() if p.exists() else None for p in changed}
    staged={}
    try:
        for p,b in changed.items():
            p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+'.ledger-tmp');q.write_bytes(b);staged[p]=q
        for p,q in staged.items():os.replace(q,p)
    except Exception:
        for p,b in before.items():
            if b is None:p.unlink(missing_ok=True)
            else:p.write_bytes(b)
        raise
    finally:
        for q in staged.values():q.unlink(missing_ok=True)

class Ledger:
    def __init__(self, root, config):
        self.root=root.resolve();self.cfg=json.loads(config.read_text());self.tz=ZoneInfo(self.cfg['timezone'])
        if self.cfg.get('schema_version')!=1:raise ValueError('不支持配置版本')
        self.paths={k:self.root/v for k,v in self.cfg['paths'].items()}
        self.accounts=self.cfg['platform_accounts'];self.scope=self.cfg.get('primary_scope','project')
        self.tables={}
        for key,defaults in [('publications',PUB_FIELDS),('metrics',MET_FIELDS),('checks',CHECK_FIELDS),('maintenance',TASK_FIELDS)]:
            fields,rows=read_csv(self.paths[key]);fields += [f for f in defaults if f not in fields]
            for r in rows:
                for f in fields:r.setdefault(f,'')
            self.tables[key]=[fields,rows]
        self.pubs=self.tables['publications'][1];self.mets=self.tables['metrics'][1];self.checks=self.tables['checks'][1];self.tasks=self.tables['maintenance'][1]
        self.items={}
        for r in read_csv(self.paths['content_index'])[1]:
            p=self.root/r.get('artifact_path','');jp=p if p.suffix=='.json' else p.parent/'item.json'
            d=json.loads(jp.read_text()) if jp.is_file() else {}
            self.items[r['id']]={**r,'title':r.get('title') or d.get('copy',{}).get('post_title') or r['id']}

    def time(self,s):
        if not s:return None
        d=datetime.fromisoformat(s.replace('Z','+00:00'))
        if not d.tzinfo:raise ValueError('时间必须带时区：'+s)
        return d.astimezone(self.tz)

    def fmt(self,s,full=False):
        return self.time(s).strftime('%Y-%m-%d %H:%M' if full else '%m-%d %H:%M') if s else '—'

    def link(self,label,path):
        if not path:return clean(label)
        p=path if str(path).startswith(('https://','http://')) else str(self.root/path)
        return f'[{clean(label)}](<{p}>)'

    def title(self,p):return p.get('title') or self.items.get(p['item_id'],{}).get('title') or p['id']
    def label(self,p):return STATE[p['status']]+('／'+VIS.get(p.get('visibility',''),'未知') if p['status']=='published' else '')
    def name(self,p):return self.accounts[p['platform_account_id']]['name']
    def primary(self,p):return (p.get('scope') or self.scope)==self.scope
    def itemlink(self,p):return self.link(p['item_id'],self.items[p['item_id']]['artifact_path']) if p['item_id'] in self.items else ('历史无制作包' if p.get('scope')=='legacy-account' else '待关联')
    def titlelink(self,p):return self.link(self.title(p),p['url']) if p['url'] else clean(self.title(p))
    def cumulative(self,m):return m.get('window_kind')=='cumulative' or (not m.get('window_kind') and ('累计' in m['window'] or m['window'].startswith('D+')))

    def validate(self):
        by={p['id']:p for p in self.pubs}
        for key,(_,rows) in self.tables.items():
            if len({r['id'] for r in rows})!=len(rows):raise ValueError('重复ID：'+key)
        native=set()
        for p in self.pubs:
            assert p['status'] in STATE,(p['id'],'非法状态')
            assert p['platform_account_id'] in self.accounts,(p['id'],'账号未配置')
            assert not p['item_id'] or p['item_id'] in self.items,(p['id'],'作品关联失效')
            assert p.get('visibility','') in ('','public','private','friends','unknown')
            if p['native_id']:
                k=p['platform_account_id'],p['native_id'];assert k not in native,('原生ID重复',k);native.add(k)
            if p['evidence_path']:assert (self.root/p['evidence_path']).is_file(),(p['id'],'证据缺失')
            if p['status']=='published':assert p['published_at'],(p['id'],'首次时间缺失')
            if p['status']=='scheduled':assert p['scheduled_at'] and not p['published_at'],(p['id'],'定时与实际时间冲突')
            if p['status']=='submitted':assert not p['published_at'],(p['id'],'提交不能冒充公开')
            for f in ('planned_at','scheduled_at','published_at','submitted_at','last_verified_at'):
                if p.get(f):self.time(p[f])
        seen=set()
        for m in self.mets:
            k=tuple(m[x] for x in ('subject_type','subject_id','metric','captured_at','source','window_kind','period_start','period_end'))
            assert k not in seen,('重复快照',k);seen.add(k)
            assert m['value'] not in ('','-') and math.isfinite(float(m['value'])),(m['id'],'非法数值')
            assert m.get('quality','') in ('','observed','pending-platform-update','conflicting','unavailable'),(m['id'],'未知数据质量状态')
            if m.get('quality_evidence'):assert (self.root/m['quality_evidence']).is_file()
            if m['unit']=='ratio':assert 0<=float(m['value'])<=1,(m['id'],'比例不在0—1')
            assert (self.root/m['source']).is_file(),(m['id'],'指标来源缺失')
            self.time(m['captured_at'])
            if m['subject_type']=='publication':
                assert m['subject_id'] in by,(m['id'],'发布关联失效')
                p=by[m['subject_id']]
                assert p['published_at'] and self.time(m['captured_at'])>=self.time(p['published_at']),(m['id'],'未发表的占位数不是成绩')
                if m.get('observation_target_hours'):
                    age=(self.time(m['captured_at'])-self.time(p['published_at'])).total_seconds()/3600
                    assert (self.cumulative(m) or m.get('window_kind')=='rolling') and abs(age-float(m['observation_target_hours']))<=self.cfg.get('observation_tolerance_hours',4),(m['id'],'不能伪造同龄窗口')
            elif m['subject_type']=='platform_account':assert m['subject_id'] in self.accounts
        for c in self.checks:
            assert c['platform_account_id'] in self.accounts
            self.time(c['captured_at'])
            for f in ('evidence_path','identity_evidence'):
                if c[f]:assert (self.root/c[f]).is_file(),('核对证据缺失',c['id'])
        for t in self.tasks:
            assert t['state'] in ('open','deferred','needs-auth','resolved','unavailable')
            assert not t['platform_account_id'] or t['platform_account_id'] in self.accounts
            assert not t['publication_id'] or t['publication_id'] in by
            if t['next_check_at']:self.time(t['next_check_at'])
            if t['evidence_path']:assert (self.root/t['evidence_path']).is_file()

    def import_snapshot(self,path):
        s=json.loads(path.read_text());assert s['schema_version']==1
        sid=s['snapshot_id'];assert re.fullmatch(r'[A-Za-z0-9_.-]+',sid), '快照ID不能是路径'
        receipt=self.paths['import_receipts']/(sid+'.json');payload=hashlib.sha256(path.read_bytes()).hexdigest()
        for item in s['sources']:
            assert digest(self.root/item['path'])==item['sha256'],('原件哈希已变化',item['path'])
        if receipt.exists():
            assert json.loads(receipt.read_text())['payload_sha256']==payload,'快照ID重用且内容不同'
            print('重复导入：已存在相同回执，保留台账');return
        manifest={x['path']:x['sha256'] for x in s['sources']}
        for p,h in manifest.items():assert digest(self.root/p)==h,('原件哈希已变化',p)
        for rows,fields in [(s.get('publications',[]),['evidence_path']),(s.get('metrics',[]),['source','quality_evidence']),(s.get('checks',[]),['evidence_path','identity_evidence']),(s.get('maintenance',[]),['evidence_path'])]:
            for r in rows:
                for f in fields:
                    if r.get(f):assert r[f] in manifest,('来源未登记哈希',r[f])
        changes=[];by={r['id']:r for r in self.pubs}
        for patch in s.get('publications',[]):
            assert set(patch)<=set(self.tables['publications'][0]),('未知发布字段',set(patch)-set(self.tables['publications'][0]))
            old=by.get(patch['id']);before=dict(old) if old else None
            if old is None:
                old=dict.fromkeys(self.tables['publications'][0],'');old['id']=patch['id'];self.pubs.append(old);by[old['id']]=old
            if old['last_verified_at'] and patch.get('last_verified_at') and self.time(old['last_verified_at'])>self.time(patch['last_verified_at']):continue
            if old['status']=='published' and patch.get('status',old['status']) not in ('published','removed'):raise ValueError('旧回执不能降级已发布记录：'+old['id'])
            old.update(patch)
            if before!=old:changes.append({'table':'publications','id':old['id'],'before':before,'after':dict(old)})
        key=lambda r:tuple(r[x] for x in ('subject_type','subject_id','metric','captured_at','source','window_kind','period_start','period_end'))
        seen={key(r):r for r in self.mets};seq=max([int(r['id'].split('-')[-1]) for r in self.mets]+[0])+1;added=0
        for incoming in s.get('metrics',[]):
            m=dict.fromkeys(self.tables['metrics'][0],'');m.update(incoming)
            if key(m) in seen:
                assert all(seen[key(m)].get(f,'')==str(m[f]) for f in ('value','unit','window','window_kind','observation_target_hours','capture_precision','period_start','period_end','data_as_of','source_kind','quality','quality_reason','quality_evidence')),('同键指标冲突',key(m));continue
            m['id']=f'metric-{seq:03d}';seq+=1;self.mets.append(m);seen[key(m)]=m;added+=1
        for correction in s.get('metric_metadata_corrections',[]):
            assert correction['source'] in manifest,'元数据修正必须登记原表哈希'
            allowed={'data_as_of','capture_precision','window','quality','quality_reason','quality_evidence'}
            if correction['set'].get('quality_evidence'):assert correction['set']['quality_evidence'] in manifest,'质量修正缺证据哈希'
            assert set(correction['set'])<=allowed,'数值、身份或统计窗口不能以元数据修正名义覆盖'
            matched=[m for m in self.mets if m['subject_id']==correction['subject_id'] and m['source']==correction['source'] and m['captured_at']==correction['captured_at'] and all(m.get(k,'')==v for k,v in correction.get('match',{}).items())]
            assert matched,'元数据修正没有匹配的指标'
            for m in matched:
                before={k:m.get(k,'') for k in correction['set']}
                if before!=correction['set']:
                    m.update(correction['set']);changes.append({'table':'metrics-metadata','id':m['id'],'before':before,'after':correction['set'],'reason':correction['reason']})
        for name in ('checks','maintenance'):
            current={r['id']:r for r in self.tables[name][1]}
            for p in s.get(name,[]):
                assert set(p)<=set(self.tables[name][0]),('未知字段',name)
                if p['id'] in current:
                    if name=='checks':assert current[p['id']]=={k:p.get(k,'') for k in self.tables[name][0]},'核对快照不可覆盖'
                    else:current[p['id']].update(p)
                else:
                    r=dict.fromkeys(self.tables[name][0],'');r.update(p);self.tables[name][1].append(r);current[r['id']]=r
        self.pubs.sort(key=lambda r:r['id']);self.validate()
        note={'snapshot_id':sid,'payload_sha256':payload,'imported_at':datetime.now(self.tz).isoformat(),'metrics_added':added,'changes':changes,'source_manifest':s['sources']}
        files={self.paths[k]:csv_bytes(*self.tables[k]) for k in self.tables}
        files[receipt]=(json.dumps(note,ensure_ascii=False,indent=2)+'\n').encode();commit_files(files)
        print(f'已导入 {sid}：{sum(c['table']=='publications' for c in changes)}条发布变更，{added}项新指标，{sum(c['table']=='metrics-metadata' for c in changes)}项有证据的元数据修正；来源和旧值见回执')

    def queue(self,now):
        tasks=[dict(t) for t in self.tasks if t['state'] in ('open','deferred','needs-auth')]
        known={(t.get('publication_id'),t.get('kind')) for t in tasks}
        start=self.time(self.cfg.get('tracking_started_at'))
        for p in self.pubs:
            if p['status']=='submitted' or (p['status']=='scheduled' and self.time(p['scheduled_at'])<=now):
                if (p['id'],'verify-publication') not in known:tasks.append({'id':'verify-'+p['id'],'publication_id':p['id'],'platform_account_id':p['platform_account_id'],'kind':'verify-publication','state':'open','reason':'已提交或已过排期，公开状态待核','next_action':'查原稿，不重传、不改排期','next_check_at':p['scheduled_at'] or p['submitted_at'] or now.isoformat()})
            if p['status']!='published' or not self.primary(p) or p.get('visibility')=='private':continue
            for h in self.cfg.get('observation_hours',[24,72,168]):
                target=self.time(p['published_at'])+timedelta(hours=h)
                if start and target<start:continue
                done=any(m['subject_type']=='publication' and m['subject_id']==p['id'] and m.get('observation_target_hours') and float(m['observation_target_hours'])==h for m in self.mets)
                if not done:
                    late=(now-target).total_seconds()/3600
                    state='upcoming' if late<0 else ('due' if late<=self.cfg.get('observation_tolerance_hours',4) else 'missed')
                    tasks.append({'id':f'collect-{p["id"]}-{h}h','publication_id':p['id'],'platform_account_id':p['platform_account_id'],'kind':'collect-metrics','state':state,'reason':f'实际公开后{h}小时观察','next_action':'用官方导出，记录真实稿龄' if state!='missed' else '窗口已错过；补当前累计并注明，不能伪造旧窗口','next_check_at':target.isoformat()})
        return sorted(tasks,key=lambda t:t.get('next_check_at') or '9999')

    def render(self,now):
        by={p['id']:p for p in self.pubs};own=[m for m in self.mets if m['subject_type']=='publication']
        groups=defaultdict(dict)
        for m in own:groups[(m['subject_id'],m['captured_at'],m['source'],m.get('window_kind',''),m.get('period_start',''),m.get('period_end',''))][m['metric']]=m
        latest=defaultdict(dict)
        for m in own:
            if m.get('quality') in ('pending-platform-update','conflicting','unavailable'):continue
            p=by[m['subject_id']]
            preferred=self.accounts[p['platform_account_id']].get('headline_window','cumulative')
            actual=m.get('window_kind') or ('cumulative' if self.cumulative(m) else 'unknown')
            if actual!=preferred:continue
            official=m.get('source_kind')=='official-export' or (not m.get('source_kind') and Path(m['source']).suffix.lower() in ('.xlsx','.xls','.csv'))
            if self.cfg.get('require_official_exports',True) and not official:continue
            previous=latest[m['subject_id']].get(m['metric'])
            if not previous or self.time(previous['captured_at'])<self.time(m['captured_at']):latest[m['subject_id']][m['metric']]=m
        checks={}
        for c in self.checks:
            acc=c['platform_account_id']
            if acc not in checks or self.time(c['captured_at'])>self.time(checks[acc]['captured_at']):checks[acc]=c
        project=[p for p in self.pubs if self.primary(p)];other=[p for p in self.pubs if not self.primary(p)]
        published=[p for p in project if p['status']=='published' and p.get('visibility')=='public']
        future=sorted([p for p in self.pubs if p['status']=='scheduled' and self.time(p['scheduled_at'])>now],key=lambda p:self.time(p['scheduled_at']))
        lines=[f'## 当前总览\n\n汇总时间：**{self.fmt(now.isoformat(),True)}，{self.cfg["timezone"]}**。以下核对时间和原始导出代表各平台实际采集范围，统计本身可能延迟。\n',table(['已登记发布记录（含取消）','项目范围','账号历史','项目已发表／可见','未来定时','已取消','有指标记录'],[[len(self.pubs),len(project),len(other),len(published),len(future),sum(p['status']=='cancelled' for p in self.pubs),len([k for k,v in latest.items() if v])]] )]
        lines.append(f'已登记{len(self.items)}份制作包；自有发布指标{len(own)}项／{len(groups)}组时点快照。对标样本{sum(m["subject_type"]=="sample" for m in self.mets)}项单独保留。只有真实零写0，“—”表示没有这个数据。\n')
        lines.append('## 平台与账号核对\n')
        data=[]
        for acc,a in self.accounts.items():
            c=checks.get(acc);ps=[p for p in self.pubs if p['platform_account_id']==acc and p['status'] not in ('planned','cancelled','failed','draft-uploaded','removed')]
            data.append([clean(a['name']),self.fmt(c['captured_at']) if c else '尚未实时核对',c['observed_total'] if c else '—',len(ps),str(len(ps)-int(c['observed_total'])) if c and c['observed_total'] else '—',self.link('原件',c['evidence_path']) if c else '待采',clean(c['notes']) if c else '尚缺完整分页和身份依据'])
        lines.append(table(['账号','最近后台核对','后台稿件数','台账已提交稿','数量差异','核对证据','口径／范围'],data))
        lines.append('“已发表”指后台／导出确认的首次发表事实；公开、私密另列。后台核对不等同匿名公开播放验收。表现数据优先采用各平台官方导出原表；后台卡片负责身份、状态与排期，历史卡片快照保留但不冒充新导出。\n')
        lines.append('## 已提交的未来排期\n')
        lines.append(table(['计划公开（配置时区）','平台','作品／发布ID','标题','最后已知状态',*(f'{h}h' for h in self.cfg.get('observation_hours',[24,72,168]))],[[self.fmt(p['scheduled_at'],True),self.name(p),self.itemlink(p)+' / '+p['id'],self.titlelink(p),clean(p['platform_review_status']),*(self.fmt((self.time(p['scheduled_at'])+timedelta(hours=h)).isoformat()) for h in self.cfg.get('observation_hours',[24,72,168]))] for p in future]))
        plans=[p for p in self.pubs if p['status']=='planned' and p['planned_at']]
        if plans:lines.append(table(['未提交计划','账号','标题','状态'],[[self.fmt(p['planned_at'],True),self.name(p),self.titlelink(p),'尚未提交'] for p in plans]))
        lines.append('## 待核对与数据回收\n\n采集目标按实际首次发表时间计算，未来定时稿先核实公开时间。错过的历史窗口不能靠今天累计值补造。\n')
        tasks=self.queue(now)
        lines.append(table(['下一次时间','平台／发布','事项','状态','原因','恢复／采集动作'],[[self.fmt(t.get('next_check_at'),True),clean(self.accounts.get(t.get('platform_account_id'),{}).get('name',''))+' / '+clean(t.get('publication_id')),clean(t['kind']),clean(t['state']),clean(t.get('reason')),clean(t.get('next_action'))] for t in tasks]))
        pending=[p for p in self.pubs if p['status'] in ('planned','draft-uploaded','submitted') or (p['status']=='scheduled' and self.time(p['scheduled_at'])<=now) or (p['status'] in ('published','removed') and not p['item_id'] and p.get('scope')!='legacy-account')]
        lines.append(table(['发布ID','账号','标题','待核状态','证据'],[[p['id'],self.name(p),self.titlelink(p),self.label(p),self.link('原件',p['evidence_path'])] for p in pending]))
        if not pending:lines.append('当前已登记稿件没有待核的提交／公开状态；数据延迟、历史不可导出等缺口仍看上方待办。\n')
        lines.append('## 已有成绩（各平台独立看）\n\n以下只汇总项目范围的官方导出，按各平台选定口径展示，B站等时间范围数据不冒充生命周期累计。每项取最后一次可得值；如果该值早于本行“最新采集”，在数值旁显示它自己的时间。不能把不同时点伪装成同一快照，也不把单日／近7日替换累计值。\n')
        headline=['impression_count','view_count','like_count','favorite_count','comment_count','share_count','follower_gain','cover_ctr']
        def value(m,latest_at=None):
            if not m:return '—'
            n=float(m['value']);s=(f'{n*100:.2f}'.rstrip('0').rstrip('.')+'%') if m['unit']=='ratio' else (f'{n:,.0f}' if n.is_integer() else f'{n:.4f}'.rstrip('0').rstrip('.'))
            if latest_at and self.time(m['captured_at'])<self.time(latest_at):s+=f'（{self.fmt(m["captured_at"])}）'
            return s
        for acc,a in self.accounts.items():
            ps=sorted([p for p in published if p['platform_account_id']==acc ],key=lambda p:self.time(p['published_at']),reverse=True)
            lines.append('### '+clean(a['name'])+'\n')
            data=[];extras=[]
            for p in ps:
                v=latest.get(p['id'],{});newest=max((m['captured_at'] for m in v.values()),key=self.time) if v else ''
                window=next((m['window'] for m in v.values() if m['captured_at']==newest),'官方导出尚无有效数值')
                data.append([p['id']+' / '+(p['item_id'] or '无包'),self.titlelink(p),self.fmt(p['published_at']),self.fmt(newest),clean(window),*(value(v.get(k),newest) for k in headline)])
                pairs=[LABELS.get(k,k)+' '+value(m,newest) for k,m in v.items() if k not in headline and not (k=='avg_watch_duration_raw' and 'avg_watch_seconds' in v)]
                sources=sorted(set(m['source'] for m in v.values()))
                extras.append([p['id'],'；'.join(pairs) or '—',' / '.join(self.link('原件'+str(i+1),s) for i,s in enumerate(sources))])
            lines.append(table(['发布ID／作品','标题','首次发表','最新采集','官方导出口径',*(LABELS[k] for k in headline)],data))
            lines.append(table(['发布ID','补充指标（旧值带时点）','对应来源'],extras))
        lines.append('## 账号历史内容（与项目表现分开）\n\n无本地制作包的旧账号内容保留原生身份、发表时间及可见范围；不虚构作品，不混入项目效果。早于平台可导出范围的历史数值保持缺失。\n')
        lines.append(table(['发布ID','账号','标题','首次发表','当前可见性','观看／播放','赞／评／藏','来源'],[[p['id'],self.name(p),self.titlelink(p),self.fmt(p['published_at'],True),VIS.get(p.get('visibility',''),'未知'),value(latest.get(p['id'],{}).get('view_count')),' / '.join(value(latest.get(p['id'],{}).get(k)) for k in ('like_count','comment_count','favorite_count')),self.link('身份／状态',p['evidence_path'])] for p in other]))
        lines.append('## 全量发布账（去重与追溯）\n\n制作包是当前版本；已发版本与历史变更以原始回执、平台导出、素材哈希和变更记录为准。\n')
        lines.append(table(['发布ID','账号','范围／作品','平台标题','当前状态／可见性','计划时间','已确认定时','首次发表','状态核对','证据'],[[p['id'],self.name(p),clean(p.get('scope') or self.scope)+' / '+self.itemlink(p),self.titlelink(p),self.label(p),self.fmt(p['planned_at']),self.fmt(p['scheduled_at']),self.fmt(p['published_at']),self.fmt(p['last_verified_at']),self.link('原件',p['evidence_path'])] for p in self.pubs]))
        lines.append('## 作品库存与未发内容\n')
        rows=[]
        for iid,c in self.items.items():
            ps=[p for p in self.pubs if p['item_id']==iid and p['status']!='cancelled']
            note=self.cfg.get('inventory_notes',{}).get(iid) or ('已归档，不作为新增重发' if c['status']=='archived' else ('先看平台原稿并去重' if ps else '未排期'))
            rows.append([self.link(iid,c.get('artifact_path')),clean(c['title']),c.get('format',''),c['status'],'；'.join(self.name(p)+':'+self.label(p) for p in ps) or '无已登记发布',clean(note)])
        lines.append(table(['作品','制作包标题','类型','制作状态','分平台记录','处理'],rows))
        lines.append('## 指标快照索引\n\n官方导出原表全部保留；逐日行与合计行在指标账中分开，不重复相加。下表按来源和窗口类型汇总，日期细节可在原表及指标账追溯。\n')
        index=defaultdict(list)
        for m in own:index[(m['subject_id'],m['captured_at'],m['source'],m.get('window_kind') or '历史累计')].append(m)
        lines.append(table(['发布ID','账号','采集时间','类型','指标项数','覆盖范围／口径','原件'],[
            [key[0],self.name(by[key[0]]),self.fmt(key[1]),key[3],len(values),
             ((min(m['period_start'] for m in values if m.get('period_start'))+'—'+max(m['period_end'] for m in values if m.get('period_end'))) if any(m.get('period_start') for m in values) else clean(values[0]['window'])),self.link('原始文件',key[2])]
            for key,values in sorted(index.items(),key=lambda x:(self.time(x[0][1]),x[0][0]))]))
        lines.append('## 本轮仍不可取得的记录\n')
        lines.append(table(['事项','平台／发布','原因','后续条件','证据'],[[t['id'],clean(t['platform_account_id'])+' / '+clean(t['publication_id']),clean(t['reason']),clean(t['next_action']),self.link('依据',t['evidence_path'])] for t in self.tasks if t['state']=='unavailable']))
        return '\n'.join(lines).strip()+'\n'

    def init(self):
        if not self.paths['content_index'].exists():
            commit_files({self.paths['content_index']:csv_bytes('id topic_id format artifact_path status updated_at'.split(),[])})
        master=self.paths['master']
        files={self.paths[k]:csv_bytes(*self.tables[k]) for k in self.tables if not self.paths[k].exists()}
        if not master.exists():
            template=(Path(__file__).resolve().parents[1]/'assets/CONTENT_MANAGEMENT.md').read_text()
            report_link=os.path.relpath(self.paths['review_report'],master.parent) if self.paths.get('review_report') else ''
            files[master]=template.replace('{{PROJECT_NAME}}',self.cfg['project_name']).replace('{{TIMEZONE}}',self.cfg['timezone']).replace('{{REVIEW_REPORT_LINK}}',report_link).encode()
        report=self.paths.get('review_report')
        if report and not report.exists():
            template=(Path(__file__).resolve().parents[1]/'assets/CONTENT_REVIEW.md').read_text()
            files[report]=template.replace('{{PROJECT_NAME}}',self.cfg['project_name']).replace('{{TIMEZONE}}',self.cfg['timezone']).replace('{{MASTER_LINK}}',os.path.relpath(master,report.parent)).encode()
        brief=self.paths.get('iteration_brief')
        if brief and not brief.exists():
            template=(Path(__file__).resolve().parents[1]/'assets/CONTENT_ITERATION_BRIEF.md').read_text()
            report_link=os.path.relpath(report,brief.parent) if report else '项目当前复盘报告'
            files[brief]=template.replace('{{PROJECT_NAME}}',self.cfg['project_name']).replace('{{REVIEW_REPORT_LINK}}',report_link).encode()
        commit_files(files)

    def refresh(self,now,check=False):
        self.validate();p=self.paths['master'];text=p.read_text()
        assert text.count(BEGIN)==text.count(END)==1,'生成区标记缺失或重复'
        new=text.split(BEGIN)[0]+BEGIN+'\n\n'+self.render(now)+'\n'+END+text.split(END)[1]
        if check:
            assert text==new,'总表与事实台账不同步，请先刷新'
            print(f'检查通过：{len(self.pubs)}条发布，{len(self.mets)}项指标，关联／来源／状态／快照／总表同步')
        else:commit_files({p:new.encode()});print('总表已刷新，手写决定保留：'+str(p))

def main(argv=None):
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--config',type=Path,required=True);a.add_argument('--import-snapshot',type=Path);a.add_argument('--check',action='store_true');a.add_argument('--queue',action='store_true');a.add_argument('--init',action='store_true');a.add_argument('--as-of');args=a.parse_args(argv)
    l=Ledger(args.root,args.config)
    if args.check and l.paths['import_receipts'].exists():
        verified={}
        for receipt in l.paths['import_receipts'].glob('*.json'):
            for source in json.loads(receipt.read_text()).get('source_manifest',[]):
                h=verified.setdefault(source['path'],digest(l.root/source['path']))
                assert h==source['sha256'],('历史原件已变化',source['path'])
    if args.init:l.init()
    text=l.paths['master'].read_text() if l.paths['master'].exists() else ''
    recorded=re.search(r'汇总时间：\*\*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})',text)
    now=(datetime.fromisoformat(args.as_of).replace(tzinfo=l.tz) if not datetime.fromisoformat(args.as_of).tzinfo else l.time(args.as_of)) if args.as_of else (datetime.fromisoformat(recorded[1]).replace(tzinfo=l.tz) if args.check and recorded else datetime.now(l.tz).replace(second=0,microsecond=0))
    if args.queue:
        l.validate();print(json.dumps(l.queue(now),ensure_ascii=False,indent=2));return
    lock=l.root/'.content-ledger.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise RuntimeError('另一次维护尚持有本地锁；先检查该次任务，不能并发覆盖台账')
    try:
        os.write(fd,str(os.getpid()).encode());os.close(fd)
        if args.import_snapshot:l.import_snapshot(args.import_snapshot)
        l.refresh(now,args.check)
    finally:lock.unlink(missing_ok=True)

if __name__=='__main__':main()
