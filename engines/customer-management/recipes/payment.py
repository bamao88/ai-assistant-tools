#!/usr/bin/env python3
"""批量解密某批学员的微信图片并拼成九宫格，供人工/视觉定位付款截图。

流程：读 all_student.json 选目标学员(默认 学期=参数) → 每人图片目录=md5(wxid) → 解全部 .dat 变体
(_t→jpg缩略 / _h→png高清 / 普通→wxgf跳过) → 每人拼一张 montage.png。
然后用视觉读 montage/<昵称>.png 定位付款交易页(交易详情/支付成功,大额数字,收款方=张和All in AI),
再读该图的高清/缩略原生分辨率取 金额+渠道。排除：助理收款码QR、SZplayer、课程页、群聊、入群卡片。

用法:
  python3 extract_payments.py --term 5期            # 解某一期全部学员
  python3 extract_payments.py --wxid wxid_a wxid_b   # 只解指定 wxid
前置: 先跑 get_img_key.py 生成 imgkey.txt。
"""
import sys, os, glob, json, hashlib, math, argparse
from pathlib import Path

# engine 根（recipes/ → up 1）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from capabilities.acquire.decrypt_dat import dat2img  # noqa

LIVE = os.path.expanduser(
    "~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_vre3jz2a7vwb22_c26a")
ATT = f"{LIVE}/msg/attach"
OUT = str(config.PAYMENT_OUT_DIR)
MON = str(config.PAYMENT_MONTAGE_DIR)


def load_students(term, wxids):
    recs = json.load(open(config.STUDENT_FILE))
    if wxids:
        return [r for r in recs if r.get("wxid") in set(wxids)]
    return [r for r in recs if r.get("学期") == term and r.get("wxid")]


def decrypt_student(wxid, name, key, xk):
    md5 = hashlib.md5(wxid.encode()).hexdigest()
    dirp = f"{ATT}/{md5}"
    od = os.path.join(OUT, name.replace("/", "_"))
    if not os.path.isdir(dirp):
        return {"name": name, "no_dir": True}
    os.makedirs(od, exist_ok=True)
    cnt = {"jpg": 0, "png": 0, "wxgf": 0}
    for f in sorted(glob.glob(dirp + "/**/*.dat", recursive=True)):
        try:
            res, ext, _ = dat2img(open(f, "rb").read(), key, xk)
        except Exception:
            continue
        if ext in ("jpg", "png", "gif", "bmp"):
            open(f"{od}/{os.path.basename(f).replace('.dat', '')}.{ext}", "wb").write(res)
            cnt[ext if ext in cnt else "jpg"] = cnt.get(ext, 0) + 1
        elif ext == "wxgf":
            cnt["wxgf"] += 1
    return {"name": name, "md5": md5, **cnt}


def build_montage(name):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    folder = os.path.join(OUT, name.replace("/", "_"))
    groups = {}
    for f in glob.glob(folder + "/*.*"):
        if not f.lower().endswith((".jpg", ".png")):
            continue
        base = os.path.basename(f).replace("_t.jpg", "").replace("_h.png", "").rsplit(".", 1)[0]
        groups.setdefault(base, []).append(f)
    imgs = sorted(next((x for x in fs if x.endswith(".png")), fs[0]) for fs in groups.values())
    if not imgs:
        return
    CELL, COLS, PAD = 420, 4, 26
    rows = math.ceil(len(imgs) / COLS)
    canvas = Image.new("RGB", (COLS * (CELL + PAD) + PAD, rows * (CELL + PAD) + PAD), (245, 245, 245))
    dr = ImageDraw.Draw(canvas)
    for i, fp in enumerate(imgs):
        try:
            im = Image.open(fp).convert("RGB"); im.thumbnail((CELL, CELL))
        except Exception:
            continue
        x = PAD + (i % COLS) * (CELL + PAD); y = PAD + (i // COLS) * (CELL + PAD)
        canvas.paste(im, (x, y + 18)); dr.text((x, y), f"#{i+1} {os.path.basename(fp)[:14]}", fill=(180, 0, 0))
    os.makedirs(MON, exist_ok=True)
    canvas.save(f"{MON}/{name.replace('/', '_')}.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--term", default="5期")
    ap.add_argument("--wxid", nargs="*")
    args = ap.parse_args()
    keyf = os.path.join(HERE, "imgkey.txt")
    if not os.path.exists(keyf):
        sys.exit("缺 imgkey.txt，先跑 get_img_key.py")
    raw = open(keyf).read().strip()
    key = bytes.fromhex(raw) if len(raw) == 32 and all(c in "0123456789abcdefABCDEF" for c in raw) else raw.encode("latin-1")
    xk = 0x7F
    xf = os.path.join(HERE, "imgxor.txt")
    if os.path.exists(xf):
        v = open(xf).read().strip()
        if v.isdigit():
            xk = int(v) & 0xFF
    students = load_students(args.term, args.wxid)
    print(f"目标学员 {len(students)} 人；XOR=0x{xk:02x}")
    for r in students:
        info = decrypt_student(r["wxid"], r.get("微信昵称") or r["wxid"], key, xk)
        if not info.get("no_dir"):
            build_montage(info["name"])
        print(info)
    print(f"\n解出图在 {OUT}/<昵称>/  拼图在 {MON}/<昵称>.png  → 用视觉逐张读 montage 定位付款页")


if __name__ == "__main__":
    main()
