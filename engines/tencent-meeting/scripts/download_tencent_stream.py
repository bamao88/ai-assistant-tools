#!/usr/bin/env python3
"""腾讯会议「分轨」下载 + 媒体库归档。切张和口播片的专用入口。

为什么要这个脚本（2026-06-02 踩坑固化）：
  腾讯云录制常有分轨——网页下载菜单可选「说话人(摄像头) / 共享屏幕 / 合成」。
  同目录的 fetch_tencent_video_via_chrome.py 只取 `download/record` 返回里的
  `payload.url`（=合成/主视频那一路），把分轨丢了。而切口播片必须用「说话人」轨：
    - 合成轨在共享屏幕时把人物缩成右上角小窗，画面忽人忽屏不统一；
    - 更要命的是合成/屏幕轨会把共享内容（飞书内部表、手机号、书签栏）录进去，
      直接发布 = 泄密。说话人轨纯摄像头满屏、零屏幕泄露，且与逐字稿时间轴一致，
      clip_plan 时间戳可直接套用、重渲即可。

  多流就在 `download/record`（need_multi_stream=1）的**同一个返回**里：
    payload.url                      -> 合成 / 主视频
    payload.data.multi_stream_recordings[] = [{url, stream_type}, ...]
      stream_type "1" -> 共享屏幕   stream_type "2" -> 发言人视角(说话人)
  （映射沿用同目录 download_tencent_meeting_videos_stable.py 的 VIDEO_TYPE_LABELS。）

三种用法
--------
1) download —— 直接走登录态 Chrome 同源 XHR 取分轨地址并下载（受腾讯下载频率/配额限制，
   短时间反复取址会返回 code=4049，此时改用 ingest）：
     python3 download_tencent_stream.py download <url或short_code> \
       --stream speaker --slug 20260429_4.5期开放答疑

2) ingest —— 把**已经用网页下载菜单下好**的分轨文件（落在 ~/Downloads，命名形如
   `...-说话人.mp4 / ...-共享屏幕.mp4 / ....mp4`）认领、改名、归档进媒体库并写 meta.json。
   这条不依赖 API、永远可用，是 4049 被限流时的稳妥路径：
     python3 download_tencent_stream.py ingest --slug 20260429_4.5期开放答疑 \
       --from ~/Downloads --match 开放答疑

3) list-streams —— 只列这条录制有哪几路流（type/size），不下载。配额新鲜时可用来确认
   stream_type 实际编号：
     python3 download_tencent_stream.py list-streams <url或short_code>

前提（同 fetch_tencent_video_via_chrome.py）：
  ① curl https://meeting.tencent.com/ == 200（200 就别动网络/Tailscale）。
  ② Chrome 开「显示→开发者→允许 Apple 事件中的 JavaScript」并冷重启。
  ③ download / list-streams 模式下，前台 active tab 是已登录、已加载完成的该录制页
     （或用 --open [--profile-directory ...] 让脚本自己打开）。ingest 模式无需 Chrome。

媒体库约定见 /Volumes/ExtSSD2601/media/README.md。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

# 复用 fetch_tencent_video_via_chrome.py 里验证过的助手，不重复造轮子。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_tencent_video_via_chrome as fx  # type: ignore[import-not-found]  # noqa: E402

DEFAULT_MEDIA_ROOT = Path("/Volumes/ExtSSD2601/media/tencent")

# stream_type 编号 -> (英文别名, 中文文件名后缀)。沿用 stable 脚本的 VIDEO_TYPE_LABELS。
STREAM_TYPE_MAP = {
    "1": ("screen", "共享屏幕"),
    "2": ("speaker", "说话人"),
}
# 用户传的 --stream 别名 -> 归一化
STREAM_ALIASES = {
    "main": "main", "composite": "main", "合成": "main", "主视频": "main",
    "speaker": "speaker", "说话人": "speaker", "发言人视角": "speaker", "camera": "speaker",
    "screen": "screen", "共享屏幕": "screen",
    "all": "all",
}
# ingest 时按文件名关键词判定流类型
NAME_HINTS = [("说话人", "speaker"), ("发言人", "speaker"),
              ("共享屏幕", "screen"), ("屏幕", "screen")]


# --------------------------------------------------------------------------- #
# download / list-streams：借登录态 Chrome 取多流地址
# --------------------------------------------------------------------------- #
def get_download_payload(rec_sharing_id: str, page_id: str) -> dict:
    """调 download/record（need_multi_stream=1），返回该录制的全部可下载流。

    返回 {code, msg, main_url, audio_url, streams:[{stream_type, alias, url}]}。
    多流结构沿用 download_tencent_meeting_videos_stable.py 的解析：
      payload.url / payload.audio_url / payload.data.multi_stream_recordings[].
    """
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
        'var d=JSON.parse(x.responseText),data=d.data||{};'
        'var streams=(data.multi_stream_recordings||[]).map(function(s){'
        'return {stream_type:String(s.stream_type),url:s.url||""};});'
        'var mainUrl=d.url||"";'
        'if(!mainUrl&&(data.urls||[]).length){mainUrl=(data.urls[0]||{}).url||"";}'
        'return JSON.stringify({code:d.code,msg:d.message||d.msg,'
        'main_url:mainUrl,audio_url:d.audio_url||"",streams:streams});'
        '}catch(e){return "ERR:"+e}})()'
    ) % (page_id, rec_sharing_id, fx.DOWNLOAD_REC)
    out = fx.chrome_js(js)
    if out.startswith("ERR:"):
        sys.exit(f"download/record 调用失败: {out}")
    d = json.loads(out)
    if d.get("code") != 0:
        sys.exit(
            f"download/record code={d.get('code')} msg={d.get('msg')}。"
            "code=4049 多半是取址被频率/配额限流——改用 `ingest` 走网页下载菜单的产物。"
        )
    for s in d.get("streams", []):
        s["alias"] = STREAM_TYPE_MAP.get(s["stream_type"], ("unknown", "stream" + s["stream_type"]))[0]
    return d


def resolve_targets(payload: dict, want: str) -> list[tuple[str, str, str]]:
    """根据 --stream 选出要下的 (alias, 中文名, url) 列表。"""
    by_alias = {"main": ("合成", payload.get("main_url") or "")}
    for s in payload.get("streams", []):
        alias, cn = STREAM_TYPE_MAP.get(s["stream_type"], ("stream" + s["stream_type"], "流" + s["stream_type"]))
        if s.get("url"):
            by_alias[alias] = (cn, s["url"])
    if want == "all":
        chosen = list(by_alias.keys())
    else:
        chosen = [want]
    targets = []
    for alias in chosen:
        if alias not in by_alias or not by_alias[alias][1]:
            avail = ", ".join(k for k, v in by_alias.items() if v[1]) or "(无)"
            sys.exit(f"这条录制没有『{alias}』流。可用: {avail}。"
                     f"（说话人对应 stream_type 2，若编号不同先用 list-streams 看实际编号）")
        cn, url = by_alias[alias]
        targets.append((alias, cn, url))
    return targets


# --------------------------------------------------------------------------- #
# 媒体库归档
# --------------------------------------------------------------------------- #
def video_meta(path: Path) -> dict:
    """ffprobe 出时长/分辨率/大小，写进 meta。"""
    info = fx.ffprobe_ok(path)  # "duration=... codec_type=video codec_name=h264 ..."
    dur = 0.0
    for tok in info.replace("\n", " ").split():
        if tok.startswith("duration="):
            try:
                dur = float(tok.split("=", 1)[1])
            except ValueError:
                pass
    return {
        "size_mb": round(path.stat().st_size / 1048576, 1),
        "duration_sec": round(dur, 1),
        "probe": info,
    }


def organize(slug_dir: Path, alias: str, cn: str, src: Path) -> Path:
    """把一路视频放进 <slug>/video/<slug>-<中文名>.mp4（合成不加后缀）。"""
    video_dir = slug_dir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if alias == "main" else f"-{cn}"
    dest = video_dir / f"{slug_dir.name}{suffix}.mp4"
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest


def update_meta(slug_dir: Path, short_code: str, source_url: str,
                added: list[tuple[str, str, Path]]) -> None:
    """合并写 meta.json 的 streams 段，标注每路 have / 大小 / 时长。"""
    meta_path = slug_dir / "meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta.setdefault("title", slug_dir.name)
    meta.setdefault("short_code", short_code)
    if source_url:
        meta.setdefault("source_url", source_url)
    streams = meta.setdefault("streams", {})
    assets = meta.setdefault("assets", {})
    KEYMAP = {"main": ("composite", "video_composite"),
              "speaker": ("speaker", "video_speaker"),
              "screen": ("screen", "video_screen")}
    DESC = {
        "main": "腾讯自动合成，共享屏幕时人物缩成右上角画中画，会暴露屏幕内容",
        "speaker": "纯摄像头/人物，干净16:9，无屏幕无画中画——切口播片用这路",
        "screen": "纯共享屏幕，可能含敏感信息，发布前先核",
    }
    for alias, cn, dest in added:
        skey, akey = KEYMAP.get(alias, (alias, "video_" + alias))
        vm = video_meta(dest)
        streams[skey] = {"have": True, "file": f"video/{dest.name}",
                         "size_mb": vm["size_mb"], "duration_sec": vm["duration_sec"],
                         "desc": DESC.get(alias, "")}
        assets[akey] = f"video/{dest.name}"
    streams.setdefault(
        "note", "腾讯网页下载菜单可选 说话人/共享屏幕/合成；切口播片用『说话人』轨。")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  meta.json 已更新: {meta_path}")


# --------------------------------------------------------------------------- #
# 子命令
# --------------------------------------------------------------------------- #
def cmd_list_streams(args) -> int:
    code = fx.short_code(args.source)
    fx.ensure_front_meeting_page(code, args.want_open, args.profile_directory, args.wait)
    info = fx.get_record_info(code)
    recs = info.get("recs") or []
    if not recs:
        sys.exit("没有录制。换有权限的 Chrome 账号。")
    print(f"会议 {code}: {len(recs)} 段录制, allow_download={info.get('allow_download')}")
    for i, r in enumerate(recs, 1):
        payload = get_download_payload(r["sharing_id"], info["page_id"])
        print(f"  录制[{i}] {r.get('name')}:")
        if payload.get("main_url"):
            print("    - main(合成)  ✓")
        for s in payload.get("streams", []):
            print(f"    - stream_type={s['stream_type']} ({s['alias']})  "
                  f"{'✓' if s.get('url') else '✗无地址'}")
    return 0


def cmd_download(args) -> int:
    code = fx.short_code(args.source)
    want = STREAM_ALIASES.get(args.stream)
    if not want:
        sys.exit(f"--stream 取值非法: {args.stream}（main/speaker/screen/all）")
    fx.ensure_front_meeting_page(code, args.want_open, args.profile_directory, args.wait)
    info = fx.get_record_info(code)
    recs = info.get("recs") or []
    if not recs:
        sys.exit("没有录制（recordings=[]）。换有权限的 Chrome 账号。")
    slug = args.slug or fx.safe_name(recs[0].get("name") or code, code)
    slug_dir = args.media_root / slug
    rec = recs[0]  # 默认第一段；多段录制用 list-streams 看后再扩展
    payload = get_download_payload(rec["sharing_id"], info["page_id"])
    targets = resolve_targets(payload, want)
    added = []
    for alias, cn, url in targets:
        tmp = slug_dir / "video" / f".{slug}-{cn}.dl.mp4"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        print(f"下载 {alias}({cn}) ...")
        fx.curl_download(url, tmp, 0)
        dest = organize(slug_dir, alias, cn, tmp)
        tmp.unlink(missing_ok=True)
        probe = fx.ffprobe_ok(dest)
        print(f"  ✓ {dest}  {dest.stat().st_size/1048576:.1f}MB  {probe}")
        added.append((alias, cn, dest))
    update_meta(slug_dir, code, info.get("source_url") or f"https://meeting.tencent.com/crm/{code}", added)
    print(f"完成：{len(added)} 路 → {slug_dir}")
    return 0


def cmd_ingest(args) -> int:
    """把网页下载菜单已下好的分轨文件归档进媒体库。"""
    src_dir = Path(args.from_dir).expanduser()
    if not src_dir.is_dir():
        sys.exit(f"--from 目录不存在: {src_dir}")
    slug_dir = args.media_root / args.slug
    cands = [p for p in src_dir.glob("*.mp4")
             if (not args.match or args.match in p.name)]
    if not cands:
        sys.exit(f"{src_dir} 里没找到匹配 .mp4（--match {args.match!r}）。"
                 "确认网页下载已完成（.crdownload 改名成真名）。")
    added = []
    for p in sorted(cands):
        alias, cn = "main", "合成"
        for hint, a in NAME_HINTS:
            if hint in p.name:
                alias = a
                cn = {"speaker": "说话人", "screen": "共享屏幕"}[a]
                break
        dest = organize(slug_dir, alias, cn, p)
        print(f"  归档 {alias}({cn}): {p.name}  {dest.stat().st_size/1048576:.1f}MB → {dest.name}")
        added.append((alias, cn, dest))
    update_meta(slug_dir, args.short_code or "", args.source_url or "", added)
    print(f"完成：归档 {len(added)} 路 → {slug_dir}")
    print("提示：切口播片用 video/<slug>-说话人.mp4 作 --video 传给 video-slicer。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--media-root", type=Path, default=DEFAULT_MEDIA_ROOT,
                    help=f"媒体库根（默认 {DEFAULT_MEDIA_ROOT}）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_chrome_opts(p):
        p.add_argument("--open", dest="want_open", action="store_true",
                       help="先用 Chrome 打开会议页")
        p.add_argument("--profile-directory", default="",
                       help='Chrome profile 目录名，如 "Default" / "Profile 2"')
        p.add_argument("--wait", type=int, default=30, help="等页面加载秒数")

    pd = sub.add_parser("download", help="借登录态 Chrome 下指定分轨")
    pd.add_argument("source", help="腾讯会议分享链接或 short_code")
    pd.add_argument("--stream", default="speaker",
                    help="main/speaker/screen/all（默认 speaker 说话人）")
    pd.add_argument("--slug", default="", help="媒体库子目录名，默认取录制标题")
    add_chrome_opts(pd)
    pd.set_defaults(func=cmd_download)

    pl = sub.add_parser("list-streams", help="只列可下载的流，不下载")
    pl.add_argument("source", help="腾讯会议分享链接或 short_code")
    add_chrome_opts(pl)
    pl.set_defaults(func=cmd_list_streams)

    pi = sub.add_parser("ingest", help="把网页已下好的分轨归档进媒体库")
    pi.add_argument("--slug", required=True, help="媒体库子目录名")
    pi.add_argument("--from", dest="from_dir", default="~/Downloads", help="源目录")
    pi.add_argument("--match", default="", help="文件名关键词过滤，如 开放答疑")
    pi.add_argument("--short-code", default="", help="写进 meta 的 short_code")
    pi.add_argument("--source-url", default="", help="写进 meta 的分享链接")
    pi.set_defaults(func=cmd_ingest)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
