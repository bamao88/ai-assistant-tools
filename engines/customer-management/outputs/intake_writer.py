#!/usr/bin/env python3
"""新学员入营 · 飞书+本地写入器（可复用）。吃一份 worksheet JSON，按 wxid 写客户管理表 + all_student.json。

worksheet schema (wxid -> {}):
  name           展示名（日志用）
  ziwo           自我介绍文本（空则不写；已有内容则 \n---\n append 顶部最新）
  qudao          渠道选项名 list（多选 append，只填飞书已有选项）
  mark5          默认 True：几期学员 append「5期」(保留已有期数)
  del_huodong_sizhuo  True：从「活动标签」移除所有含「私戳」的选项（成交后清潜客标签）
  phone          手机号（空则不填；只填飞书该字段为空时）
  pay            {amt, method(转账/小鹅通/微信支付), img(相对路径)} 付款；img 用 --as bot 传

用法: python3 -m outputs.intake_writer <worksheet.json> [--apply]
只填空+多选append，不覆盖已有文本；幂等。
"""
import json, subprocess, sys, time, os
from pathlib import Path

APP="YTcFbyGS4arILPseQJscA6J7nqb"; TBL="tblfCYoeornDw0XF"
F_WX="wxid"; F_ZIWO="自我介绍"; F_QUDAO="渠道"; F_JIQI="几期学员"
F_HUODONG="活动标签"; F_PHONE="手机号"; F_SHIFU="实付"; F_FANGSHI="付款方式"; F_PINGZHENG="提成截图凭证"
REPO=Path(__file__).resolve().parents[2]
SM=REPO/"student_manage"

def lark(args,timeout=120):
    r=subprocess.run(["lark-cli","--as","bot","--profile","zhanghe"]+args,capture_output=True,text=True,timeout=timeout)
    if r.returncode!=0: raise RuntimeError(r.stderr[:300])
    o=r.stdout;i=o.find("{");return json.loads(o[i:])
def sx(v):
    return "".join((x.get('text') or x.get('name') or '') if isinstance(x,dict) else str(x) for x in v) if isinstance(v,list) else (v or "")
def names(v):
    out=[]
    if isinstance(v,list):
        for x in v: out.append(x.get('name') if isinstance(x,dict) else x)
    elif isinstance(v,str) and v: out=[v]
    return out
def fetch():
    out=[];tok=""
    while True:
        p={"page_size":500}
        if tok:p["page_token"]=tok
        d=lark(["api","GET",f"/open-apis/bitable/v1/apps/{APP}/tables/{TBL}/records","--params",json.dumps(p,ensure_ascii=False)]).get("data",{})
        out+=d.get("items") or []
        if not d.get("has_more"):break
        tok=d.get("page_token") or ""
        if not tok:break
    return out

def main():
    args=sys.argv[1:]
    apply="--apply" in args
    wsf=[a for a in args if not a.startswith("--")][0]
    ws=json.load(open(wsf))
    recs=fetch()
    w2r={}
    for r in recs:
        w=sx((r.get("fields") or {}).get(F_WX)).strip()
        if w and w not in w2r: w2r[w]=r
    updates=[]; attaches=[]; miss=[]
    for w,spec in ws.items():
        r=w2r.get(w)
        if not r: miss.append((w,spec.get("name"))); continue
        f=r.get("fields") or {}; patch={}; diag=[]
        # 自我介绍（只填空，已有则 append 顶部）
        zi=(spec.get("ziwo") or "").strip()
        if zi:
            cur=sx(f.get(F_ZIWO)).strip()
            if not cur: patch[F_ZIWO]=zi; diag.append("自我介绍")
            elif zi not in cur: patch[F_ZIWO]=zi+"\n---\n"+cur; diag.append("自我介绍+")
        # 渠道（多选 append）
        qd=spec.get("qudao") or []
        if qd:
            cur=names(f.get(F_QUDAO)); add=[x for x in qd if x not in cur]
            if add: patch[F_QUDAO]=cur+add; diag.append("渠道+"+",".join(add))
        # 几期学员 append 5期
        if spec.get("mark5",True):
            cur=names(f.get(F_JIQI))
            if "5期" not in cur: patch[F_JIQI]=cur+["5期"]; diag.append("几期+5期")
        # 删私戳
        if spec.get("del_huodong_sizhuo"):
            cur=names(f.get(F_HUODONG)); keep=[x for x in cur if "私戳" not in x]
            if len(keep)!=len(cur): patch[F_HUODONG]=keep; diag.append("删私戳"+str([x for x in cur if '私戳' in x]))
        # 手机号（只填空）
        ph=(spec.get("phone") or "").strip()
        if ph and not sx(f.get(F_PHONE)).strip(): patch[F_PHONE]=ph; diag.append("手机")
        # 付款
        pay=spec.get("pay")
        if pay:
            if not sx(f.get(F_SHIFU)).strip(): patch[F_SHIFU]=str(pay["amt"]); patch[F_FANGSHI]=pay["method"]; diag.append(f"实付{pay['amt']}")
            if pay.get("img") and not f.get(F_PINGZHENG): attaches.append((r["record_id"],pay["img"],spec.get("name")))
        if patch:
            updates.append({"record_id":r["record_id"],"fields":patch,"_n":spec.get("name"),"_d":diag})
    print(f"待更新 {len(updates)} 行, 传凭证 {len(attaches)}, 缺行 {len(miss)}")
    for u in updates: print(f"  {u['_n']:16} {u['_d']}")
    if miss: print("  ⚠️缺行:",miss)
    if not apply:
        print("[dry-run] 未写。加 --apply。"); return
    ok=0;fail=0
    for i in range(0,len(updates),100):
        b=[{"record_id":u["record_id"],"fields":u["fields"]} for u in updates[i:i+100]]
        res=lark(["api","POST",f"/open-apis/bitable/v1/apps/{APP}/tables/{TBL}/records/batch_update","--data",json.dumps({"records":b},ensure_ascii=False)])
        if res.get("code")==0: ok+=len(b)
        else: fail+=len(b); print("FAIL",res.get("code"),res.get("msg"))
    print(f"[update] ok={ok} fail={fail}")
    aok=0;af=[]
    for rid,img,nm in attaches:
        rr=subprocess.run(["lark-cli","base","+record-upload-attachment","--as","bot","--profile","zhanghe",
            "--base-token",APP,"--table-id",TBL,"--record-id",rid,"--field-id",F_PINGZHENG,"--file",img],
            capture_output=True,text=True,timeout=120)
        if '"ok": true' in (rr.stdout+rr.stderr): aok+=1
        else: af.append(nm)
        time.sleep(1)
    print(f"[attach] ok={aok} fail={af}")

if __name__=="__main__":
    main()
