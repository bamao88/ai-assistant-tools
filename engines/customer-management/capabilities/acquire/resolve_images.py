#!/usr/bin/env python3
"""resolve_images.py — 按需读图能力（acquire 的 L2 重解析层）。§2① + 无损分层阶段3。

给定 wxid → 在本机微信 v4 容器按 md5(wxid) 找该人全部聊天图片 .dat → 解密成可读图 →
返回落盘路径。供 analyze / agent 在「文字不足、需看图取证」时**按需**调用——这是无损分层
里 L2 的实际取图入口（L0 文字默认看，info_map 告诉它有图，卡住时来这里解）。

与 payment 的关系：payment 配方按"期"批量解 + 拼 montage 是上层编排；本模块是其复用的
**单点取图能力**（按 wxid，可被任何流程/agent 调用），共享 decrypt_dat.dat2img。

约束（是边界不是 bug）：
  · 仅本机：依赖 config.WECHAT_ATTACH_DIR（写死当前采集账号容器，换号设环境变量覆盖）。
  · 按人解：解出某人**全部**图片，不按单条消息精确取（按时间/眼看对应聊天里的 [图片]）。
  · wxgf：微信新专有格式不在本脚本解码（需 Wxam2pic），计入 counts 但不出图。
  · imgkey：一次性钥匙串授权生成 imgkey.txt（capabilities.acquire.get_img_key）。

CLI:  python3 -m capabilities.acquire.resolve_images --wxid <wxid> [--out <dir>]
库用: from capabilities.acquire.resolve_images import resolve_person_images
"""
from __future__ import annotations

import glob
import hashlib
import os
import sys
from pathlib import Path

# engine 根（capabilities/acquire/ → up 2）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402
from capabilities.acquire.decrypt_dat import dat2img  # noqa: E402


def load_img_keys() -> tuple[bytes, int]:
    """读 imgkey.txt(16字节ASCII原样) + imgxor.txt(十进制单字节)。口径与 payment 配方一致。"""
    keyf = config.PAYMENT_IMGKEY_FILE
    if not keyf.exists():
        raise FileNotFoundError(f"缺 imgkey.txt（先跑 capabilities.acquire.get_img_key）: {keyf}")
    raw = keyf.read_text().strip()
    is_hex32 = len(raw) == 32 and all(c in "0123456789abcdefABCDEF" for c in raw)
    key = bytes.fromhex(raw) if is_hex32 else raw.encode("latin-1")
    xk = 0x7F
    xf = config.PAYMENT_IMGXOR_FILE
    if xf.exists():
        v = xf.read_text().strip()
        if v.isdigit():
            xk = int(v) & 0xFF
    return key, xk


def resolve_person_images(
    wxid: str,
    *,
    out_dir: str | Path | None = None,
    key: bytes | None = None,
    xorkey: int | None = None,
) -> dict:
    """解出某人全部聊天图片。返回 {wxid, attach_dir, exists, counts, images:[路径]}。

    counts 形如 {jpg, png, wxgf, err}；images 是可读图（jpg/png/gif/bmp）落盘路径列表。
    attach 目录不存在（该账号容器里没这个人/不在本机）→ exists=False, images=[]。
    """
    if key is None:
        key, xorkey = load_img_keys()
    xk = 0x7F if xorkey is None else xorkey
    md5 = hashlib.md5(wxid.encode()).hexdigest()
    attach = Path(config.WECHAT_ATTACH_DIR) / md5
    out = Path(out_dir) if out_dir else (config.PAYMENT_OUT_DIR / wxid)
    result: dict = {"wxid": wxid, "attach_dir": str(attach), "exists": attach.is_dir(),
                    "counts": {}, "images": []}
    if not attach.is_dir():
        return result
    out.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for f in sorted(glob.glob(str(attach / "**" / "*.dat"), recursive=True)):
        try:
            data, ext, _ = dat2img(open(f, "rb").read(), key, xk)
        except Exception:
            counts["err"] = counts.get("err", 0) + 1
            continue
        if ext in ("jpg", "png", "gif", "bmp"):
            p = out / (os.path.basename(f).replace(".dat", "") + "." + ext)
            p.write_bytes(data)
            result["images"].append(str(p))
            counts[ext] = counts.get(ext, 0) + 1
        elif ext == "wxgf":
            counts["wxgf"] = counts.get("wxgf", 0) + 1
    result["counts"] = counts
    return result


def main() -> None:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="按 wxid 解密某人全部聊天图片（按需读图）")
    ap.add_argument("--wxid", required=True)
    ap.add_argument("--out", help="解出图落盘目录（默认 payment_proof/out/<wxid>）")
    args = ap.parse_args()
    res = resolve_person_images(args.wxid, out_dir=args.out)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if not res["exists"]:
        print(f"\n⚠️ 该 wxid 在本机微信容器无附件目录（不在本账号/不在本机）：{res['attach_dir']}", file=sys.stderr)


if __name__ == "__main__":
    main()
