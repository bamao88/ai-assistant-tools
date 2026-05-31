#!/usr/bin/env python3
"""借「已登录 Chrome 前台标签」的同源 XHR 取腾讯会议录制真实地址并下载。

为什么要这个脚本（2026-05-31 踩坑固化）：
  同目录的 download_tencent_meeting_videos_stable.py 只用无 cookie 的 requests 调
  公共 API，登录态才可见的录制它永远拿不到（code=0 但 recordings=[]，报
  "No recordings found"）。逐字稿能成功是因为走 Chrome DOM（带登录态）。视频也
  必须借**已登录 Chrome 页面的同源 XHR**（带 cookie）取地址，再 curl 拉字节。
  这个脚本把那三步（common-record-info → download/record → curl+校验）固化下来，
  避免每次手搓 osascript JS。

前提（不满足会直接报错，不会瞎下）：
  1. 网络已通：curl https://meeting.tencent.com/ == 200（被东京出口掐时先做三件事分流，
     见 SKILL 前置条件 1）。
  2. Chrome 已开「显示→开发者→允许 Apple 事件中的 JavaScript」并冷重启（AppleEvents JS 桥）。
  3. 前台 active tab 是**已登录、已加载完成**的该会议录制页（/crm 或 /cw）。
     可用 --open 让脚本自己 open 指定 profile 的会议页并等待。

用法:
  # 前台已经是登录态会议页时，一条命令下主视频：
  python3 fetch_tencent_video_via_chrome.py <url或short_code> --output-dir /abs/dir

  # 让脚本用指定 Chrome profile 打开会议页再下（profile 目录名见 chrome://version，
  # 如 "Default" / "Profile 2"）：
  python3 fetch_tencent_video_via_chrome.py <url> --output-dir /abs/dir --open --profile-directory "Profile 2"

  # 只列录制（看 size / minutes_exportable / 几段），不下载：
  python3 fetch_tencent_video_via_chrome.py <url> --list-only
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SHARE_RE = re.compile(r"https?://meeting\.tencent\.com/(?:crm|cw)/([A-Za-z0-9]+)")
COMMON_INFO = "https://meeting.tencent.com/wemeet-tapi/v2/meetlog/public/detail/common-record-info"
DOWNLOAD_REC = "https://meeting.tencent.com/wemeet-cloudrecording-webapi/v1/download/record"
REFERER = "https://meeting.tencent.com/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")


def short_code(s: str) -> str:
    m = SHARE_RE.search(s.strip())
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9]+", s.strip()):
        return s.strip()
    sys.exit(f"不是腾讯会议分享链接也不是 short_code: {s}")


def chrome_js(js: str, timeout: int = 40) -> str:
    """在 Chrome 前台 active tab 执行 JS，返回其字符串结果。"""
    esc = js.replace("\\", "\\\\").replace('"', '\\"')
    applescript = (
        'tell application "Google Chrome" to execute front window\'s '
        f'active tab javascript "{esc}"'
    )
    r = subprocess.run(["osascript", "-e", applescript],
                       capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if not out and err:
        raise RuntimeError(f"osascript 失败: {err}")
    return out


def ensure_front_meeting_page(code: str, want_open: bool, profile: str,
                              wait: int) -> None:
    """确认前台 active tab 是已加载完成的会议页；--open 时先打开。"""
    url = f"https://meeting.tencent.com/crm/{code}"
    if want_open:
        args = ["open", "-b", "com.google.Chrome", "--args"]
        if profile:
            args += [f"--profile-directory={profile}"]
        args += [url]
        subprocess.run(args, check=False)
        time.sleep(8)
        subprocess.run(["osascript", "-e",
                        'tell application "Google Chrome" to activate'], check=False)
        time.sleep(2)

    deadline = time.time() + wait
    last = ""
    while time.time() < deadline:
        try:
            state = chrome_js('document.readyState+"|"+location.href')
        except Exception as e:  # noqa: BLE001
            last = str(e)
            time.sleep(1.5)
            continue
        last = state
        if state.startswith("complete") and "meeting.tencent.com" in state:
            return
        time.sleep(1.5)
    sys.exit(f"前台 Chrome 标签不是已加载完成的会议页（最后状态: {last[:200]}）。\n"
             f"请先在已登录的 Chrome 里打开 {url}，或加 --open [--profile-directory ...]。")


def get_record_info(code: str) -> dict:
    js = (
        '(function(){try{'
        'var p=new URLSearchParams({forward_cgi_path:"shares",enter_from:"share",'
        'lang:"zh-CN",is_origin_content:"true",is_cve:"true",short_url_code:"%s"});'
        'var x=new XMLHttpRequest();'
        'x.open("GET","%s?"+p.toString(),false);x.send();'
        'var d=JSON.parse(x.responseText),data=d.data||{};'
        'var long=(data.short_url_info||{}).long_url||"";'
        'var qs=long.indexOf("?")>=0?long.split("?")[1]:long;'
        'var page_id=(new URLSearchParams(qs)).get("id")||"";'
        'var recs=(data.recordings||[]).map(function(r){return {'
        'sharing_id:r.sharing_id,size:r.size,name:r.name,'
        'minutes_exportable:r.minutes_exportable};});'
        'return JSON.stringify({code:d.code,msg:d.msg||d.message,'
        'page_id:page_id,allow_download:data.allow_download,recs:recs});'
        '}catch(e){return "ERR:"+e}})()'
    ) % (code, COMMON_INFO)
    out = chrome_js(js)
    if out.startswith("ERR:"):
        sys.exit(f"common-record-info 失败: {out}")
    return json.loads(out)


def get_download_url(rec_sharing_id: str, page_id: str) -> str:
    js = (
        '(function(){try{'
        'var p=new URLSearchParams({id:"%s",sharing_id:"%s",source:"shares",'
        'from_share:"1",need_multi_stream:"1",c_app_id:"1400143280",c_os:"web",'
        'c_os_model:"web",c_os_version:"1",c_app_version:"1",c_instance_id:"5",'
        'c_district:"0",c_timestamp:String(Date.now()),'
        'c_nonce:"h"+Math.floor(Math.random()*999999),'
        'rnds:"h"+Math.floor(Math.random()*999999)});'
        'var x=new XMLHttpRequest();'
        'x.open("GET","%s?"+p.toString(),false);x.send();'
        'var d=JSON.parse(x.responseText);'
        'return JSON.stringify({code:d.code,msg:d.message||d.msg,url:d.url||""});'
        '}catch(e){return "ERR:"+e}})()'
    ) % (rec_sharing_id, page_id, DOWNLOAD_REC)
    out = chrome_js(js)
    if out.startswith("ERR:"):
        sys.exit(f"download/record 失败: {out}")
    d = json.loads(out)
    if d.get("code") != 0 or not d.get("url"):
        sys.exit(f"download/record 没返回地址: code={d.get('code')} msg={d.get('msg')}")
    return d["url"]


def safe_name(text: str, fallback: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\r\n]+", "_", (text or "").strip())
    cleaned = cleaned.strip(" ._")
    return cleaned[:120] or fallback


def curl_download(url: str, dest: Path, expect_size: int) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["curl", "-L", "--fail", "-C", "-", "-e", REFERER, "-A", UA,
           "-o", str(dest), url]
    print(f"  下载中 → {dest.name}（预期 {expect_size/1048576:.1f} MB）...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"curl 下载失败 returncode={r.returncode}（403 多半是缺 Referer/UA，"
                 f"或地址 token 过期，重取一次）")
    return dest.stat().st_size if dest.exists() else 0


def ffprobe_ok(path: Path) -> str:
    ff = shutil.which("ffprobe") or "/opt/homebrew/opt/ffmpeg/bin/ffprobe"
    if not Path(ff).exists():
        return "ffprobe 不可用，跳过编码校验"
    r = subprocess.run(
        [ff, "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,codec_name",
         "-of", "default=noprint_wrappers=1", str(path)],
        capture_output=True, text=True)
    return (r.stdout or r.stderr).strip().replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="腾讯会议分享链接或 short_code")
    ap.add_argument("--output-dir", type=Path, default=Path.cwd() / "tencent_videos")
    ap.add_argument("--list-only", action="store_true", help="只列录制，不下载")
    ap.add_argument("--open", dest="want_open", action="store_true",
                    help="先用 Chrome 打开会议页（配合 --profile-directory）")
    ap.add_argument("--profile-directory", default="",
                    help='Chrome profile 目录名，如 "Default" / "Profile 2"')
    ap.add_argument("--wait", type=int, default=30, help="等页面加载完成的秒数")
    args = ap.parse_args()

    code = short_code(args.source)
    ensure_front_meeting_page(code, args.want_open, args.profile_directory, args.wait)

    info = get_record_info(code)
    if info.get("code") != 0:
        sys.exit(f"common-record-info code={info.get('code')} msg={info.get('msg')}"
                 f"（多半是当前 Chrome 账号对这条分享没权限，换个 profile 试）")
    recs = info.get("recs") or []
    if not recs:
        sys.exit("没有录制（recordings=[]）。换有权限的 Chrome 账号，或这条分享无录制。")

    print(f"会议 {code}: {len(recs)} 段录制, allow_download={info.get('allow_download')}, "
          f"page_id={info.get('page_id')}")
    for i, r in enumerate(recs, 1):
        sz = int(r.get("size") or 0)
        print(f"  [{i}] {r.get('name')}  {sz/1048576:.1f}MB  "
              f"minutes_exportable={r.get('minutes_exportable')}")
    if args.list_only:
        print(json.dumps(info, ensure_ascii=False))
        return 0

    multi = len(recs) > 1
    results = []
    for i, r in enumerate(recs, 1):
        url = get_download_url(r["sharing_id"], info["page_id"])
        expect = int(r.get("size") or 0)
        stem = safe_name(r.get("name") or f"recording{i}", f"{code}_rec{i}")
        suffix = f"_{stem}" if multi else ""
        dest = args.output_dir / "files" / f"{code}{suffix}.mp4"
        got = curl_download(url, dest, expect)
        ok = (expect == 0) or (got == expect)
        probe = ffprobe_ok(dest)
        status = "OK" if ok else f"SIZE_MISMATCH(got={got} expect={expect})"
        print(f"  ✓ {dest}  {got/1048576:.1f}MB  [{status}]  {probe}")
        results.append({"file": str(dest), "bytes": got, "expect": expect,
                        "ok": ok, "ffprobe": probe})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "video_manifest.json").write_text(
        json.dumps({"code": code, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    all_ok = all(x["ok"] for x in results)
    print(f"完成：{len(results)} 段，{'全部校验通过' if all_ok else '有段大小不符，请检查'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
