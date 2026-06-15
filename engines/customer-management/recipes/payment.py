#!/usr/bin/env python3
"""payment.py — 付款金额配方：acquire(解图) + analyze(视觉读卡) → 写回（§5/§6）。

组成（配方 = 能力 + 卡 + 出口）：
  1. acquire : 调 capabilities.acquire.decrypt_dat 把目标学员的微信 .dat 图解密，
               拼成九宫格 montage/<昵称>.png（前置：先跑 capabilities.acquire.get_img_key
               生成 imgkey.txt）。
  2. analyze : **视觉读卡 cards/payment.md**——由 agent（Claude）用自身视觉逐张读 montage
               定位付款交易页、取金额+渠道。**注意本 engine 的 analyze/core.call_llm 是纯文本
               通道，不支持读图**；付款视觉读历来由 agent 直接看图完成（见 cards/payment.md 顶部说明），
               故本配方止于「把图解好 + 指向视觉卡」，不调任何 LLM API（不 hack 多模态）。
  3. 写回    : agent 读图得出的 {amt, method, img} 填进 outputs/intake_writer 的 worksheet 的
               `pay` 字段，由 intake_writer 幂等写「实付/付款方式」+ 上传「提成截图凭证」。

流程：读 all_student.json 选目标学员(默认 学期=参数) → 每人图片目录=md5(wxid) → 解全部 .dat 变体
(_t→jpg缩略 / _h→png高清 / 普通→wxgf跳过) → 每人拼一张 montage.png → 打印视觉读卡指引。

用法（迁移后从 engine 根跑）:
  python3 -m recipes.payment --term 5期             # 解某一期全部学员
  python3 -m recipes.payment --wxid wxid_a wxid_b   # 只解指定 wxid
前置: 先跑 capabilities.acquire.get_img_key 生成 imgkey.txt。
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
    keyf = str(config.PAYMENT_IMGKEY_FILE)
    if not os.path.exists(keyf):
        sys.exit("缺 imgkey.txt，先跑 get_img_key.py")
    raw = open(keyf).read().strip()
    key = bytes.fromhex(raw) if len(raw) == 32 and all(c in "0123456789abcdefABCDEF" for c in raw) else raw.encode("latin-1")
    xk = 0x7F
    xf = str(config.PAYMENT_IMGXOR_FILE)
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
    card = Path(__file__).resolve().parents[1] / "cards" / "payment.md"
    print(f"\n[acquire 完成] 解出图在 {OUT}/<昵称>/  拼图在 {MON}/<昵称>.png")
    print(f"[analyze 视觉读] 按视觉读卡 {card} 逐张读 montage 定位付款页 → 取 金额+渠道")
    print(f"  ⚠️ 本 engine analyze 机器核纯文本不读图；付款视觉读由 agent 直接看 montage 完成。")
    print(f"[写回] 把 {{amt,method,img}} 填进 worksheet 的 pay 字段 → recipes.intake / outputs.intake_writer")


if __name__ == "__main__":
    main()
