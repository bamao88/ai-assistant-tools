#!/usr/bin/env python3
"""video_framework_slicer —— 口播切片 → 「手写框架图翻页 + 人像圆形PIP + 纠错字幕 + 自适应变速」竖版成片。

一条命令：  python slicer.py jobs/<job>.json [--out DIR] [--skip-accel]

输入 = 一个 job JSON（见 jobs/clip01.json）：
  { video, srt, pages:[{start,title,blocks:[...]}], params?:{target_cps,max_speed,transition} }
  pages 现阶段人工写；将来由 LLM 读逐字稿自动产出同 schema 的 JSON（渲染层不用改）。

输出（OUT/<name>/）：
  page_*.png  zh.ass  paginated.mp4(原速带翻页)  accel.mp4(自适应变速·最终交付)

阶段：locate(人脸) → assets(白环/遮罩) → pages(spec→PNG) → subs(srt+纠错→ASS)
      → compose(翻页+PIP+字幕) → accelerate(按语速变速)

依赖：ffmpeg；node+puppeteer(render_page.js)；python: pillow, opencv-python-headless（建 venv）。
几何/配色为锁定值（已多轮定稿），改版式见 GEOM / 模板常量。
"""
from __future__ import annotations
import argparse, json, re, subprocess, html as _html
from pathlib import Path

HERE = Path(__file__).parent
_ENGINE_ROOT = Path(__file__).resolve().parent.parent  # engines/video-framework-render
ACCEL = dict(target_cps=8.0, max_speed=2.0, gap_speed=2.0, min_speed=1.0)  # 语速变速(画幅无关)

# ---- 版式几何外置：layouts/<name>.json（竖版 vertical / 横版 landscape）----
# 竖版值锁定（成片定稿，G4 逐帧回归基线）。外置后竖版输出必须逐字节不变。
def load_layout(name: str = "vertical") -> dict:
    return json.loads((_ENGINE_ROOT / "layouts" / f"{name}.json").read_text(encoding="utf-8"))

# ======================================================================
# 页面 HTML 模板（手写体/标题带/coral 长条/正文；无白环——白环是独立静态层）
PAGE_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
html,body { width:720px; height:1280px; background:#ffffff; }
.stage { position:relative; width:720px; height:1280px; background:#ffffff; overflow:hidden;
  font-family:"Hannotate SC","HanziPen SC","PingFang SC",cursive; color:#1a1a1a; }
.titlewrap { position:absolute; top:100px; left:0; width:720px; text-align:center; }
.titleband { display:inline-block; padding:10px 34px; background:#f0ece3; border-radius:14px;
  font-size:42px; font-weight:700; letter-spacing:1px; color:#1a1a1a; }
.titlestrip { position:absolute; top:204px; left:50%; transform:translateX(-50%);
  width:440px; height:13px; border-radius:7px; background:#FF6B5C; }
.ppt { position:absolute; top:266px; left:0; width:720px; text-align:center;
  display:flex; flex-direction:column; align-items:center; }
.l-hero { font-size:48px; font-weight:700; letter-spacing:1px; position:relative; }
.underline { display:block; margin:4px auto 0; height:10px; }
.arrow { margin:14px 0 6px; }
.l-mid { font-size:35px; font-weight:700; line-height:1.4; }
.l-key { font-size:39px; font-weight:700; margin-top:6px; }
.l-sub { font-size:28px; color:#555; margin-top:8px; line-height:1.4; }
.gap-l { height:38px; } .gap-m { height:22px; }
"""
ARROW = ('<svg class="arrow" width="46" height="50" viewBox="0 0 46 50">'
  '<path d="M23,3 C20,18 26,30 23,42" stroke="#1a1a1a" stroke-width="5" fill="none" stroke-linecap="round"/>'
  '<path d="M11,32 C16,40 20,44 23,46 C26,44 30,40 35,32" stroke="#1a1a1a" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')

def _hero(text, uw=300):
    u=(f'<svg class="underline" width="{uw}" viewBox="0 0 {uw} 10" preserveAspectRatio="none">'
       f'<path d="M4,6 C{uw*0.27:.0f},2 {uw*0.72:.0f},9 {uw-4},4" stroke="#1a1a1a" stroke-width="6" fill="none" stroke-linecap="round"/></svg>')
    return f'<div class="l-hero">{_html.escape(text)}{u}</div>'

def _block(b):
    t=b["type"]
    if t=="hero": return _hero(b["text"], b.get("uw",300))
    if t=="arrow": return ARROW
    if t=="mid": return f'<div class="l-mid">{b["text"]}</div>'      # 允许 <br>
    if t=="key": return f'<div class="l-key">{b["text"]}</div>'
    if t=="sub": return f'<div class="l-sub">{b["text"]}</div>'
    if t=="gap": return f'<div class="gap-{b.get("size","l")}"></div>'
    return ""

def page_html_vertical(spec):
    body="".join(_block(b) for b in spec["blocks"])
    return (f'<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><style>{PAGE_CSS}</style></head>'
            f'<body><div class="stage">'
            f'<div class="titlewrap"><span class="titleband">{_html.escape(spec["title"])}</span></div>'
            f'<div class="titlestrip"></div><div class="ppt">{body}</div></div></body></html>')

# ---- 横版 1280×720 模板：吸收 videocut-zh 适合横屏的「方框」骨架，配色/手写字/coral 沿用我们的。----
# 复用同一套 block（hero/arrow/mid/key/sub/gap）——内容/视觉解耦：同一份 pages 既出竖版又出横版。
# 右侧 + 右下留空给人像圆形 PIP（内容别压到那）。
PAGE_CSS_LANDSCAPE = """
* { margin:0; padding:0; box-sizing:border-box; }
html,body { width:1280px; height:720px; background:#ffffff; }
.stage { position:relative; width:1280px; height:720px; background:#fbfbf7;
  font-family:"Hannotate SC","HanziPen SC","PingFang SC",cursive; color:#1a1a1a; }
.titlewrap { position:absolute; top:42px; left:0; width:1280px; text-align:center; }
.titleband { display:inline-block; padding:8px 40px; background:#f0ece3; border-radius:14px;
  font-size:40px; font-weight:700; letter-spacing:1px; color:#1a1a1a; }
.titlestrip { position:absolute; top:128px; left:50%; transform:translateX(-50%);
  width:520px; height:12px; border-radius:6px; background:#FF6B5C; }
.ppt { position:absolute; top:172px; left:80px; width:840px;
  display:flex; flex-direction:column; align-items:flex-start;
  padding:30px 40px; border:3px solid #1a1a1a; border-radius:24px; background:#ffffff; }
.l-hero { font-size:52px; font-weight:700; letter-spacing:1px; position:relative; }
.underline { display:block; margin:4px 0 0; height:10px; }
.arrow { margin:10px 0 4px; }
.l-mid { font-size:34px; font-weight:700; line-height:1.4; }
.l-key { font-size:40px; font-weight:700; margin-top:8px; }
.l-sub { font-size:28px; color:#555; margin-top:6px; line-height:1.4; }
.gap-l { height:30px; } .gap-m { height:18px; }
"""

def page_html_landscape(spec):
    body="".join(_block(b) for b in spec["blocks"])
    return (f'<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><style>{PAGE_CSS_LANDSCAPE}</style></head>'
            f'<body><div class="stage">'
            f'<div class="titlewrap"><span class="titleband">{_html.escape(spec["title"])}</span></div>'
            f'<div class="titlestrip"></div><div class="ppt">{body}</div></div></body></html>')

# 模板注册表：按 layout["template"] 选页面 HTML 构造器。
TEMPLATES = {"vertical": page_html_vertical, "landscape": page_html_landscape}

# ======================================================================
def locate_face_cx(video) -> tuple[float, float, float]:
    """Haar 人脸检测取脸中心 (x,y) + 脸高 fh(均占比例)。失败→(0.5,0.42,0.16)。
    x 水平居中；竖屏源用 y+fh 做头肩方裁（避开上方 PPT）；横屏源仍方裁满高(y/fh 不影响)。"""
    try:
        import cv2, numpy as np, statistics
    except ImportError:
        print("  [locate] 无 cv2，用 cx=0.5 cy=0.42 fh=0.16（建议 venv 装 opencv-python-headless）")
        return 0.5, 0.42, 0.16
    cap=cv2.VideoCapture(str(video)); total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    W=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    H=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
    base=cv2.data.haarcascades
    cas=[cv2.CascadeClassifier(base+"haarcascade_frontalface_default.xml"),
         cv2.CascadeClassifier(base+"haarcascade_frontalface_alt2.xml")]
    xs=[]; ys=[]; hs=[]
    for i in np.linspace(0,max(total-1,0),40).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES,int(i)); ok,fr=cap.read()
        if not ok: continue
        g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY); fc=[]
        for c in cas: fc+=[tuple(int(v) for v in f) for f in c.detectMultiScale(g,1.1,6,minSize=(80,80))]
        if fc:
            x,y,w,h=max(fc,key=lambda f:f[2]*f[3]); xs.append((x+w/2)/W); ys.append((y+h/2)/H); hs.append(h/H)
    cap.release()
    portrait = H > W
    cx=statistics.median(xs) if xs else 0.5
    # 检测失败兜底：竖屏源人物在下半部→默认 0.75(避免圆窗落到上方 PPT)；横屏源保持 0.42
    cy=statistics.median(ys) if ys else (0.75 if portrait else 0.42)
    fh=statistics.median(hs) if hs else 0.16
    if len(xs) < 3:
        print(f"  [locate] ⚠️仅检到 {len(xs)} 帧人脸，用兜底 y={cy*100:.0f}%（竖屏下部）—建议人工抽查此条 PIP")
    print(f"  [locate] 检到 {len(xs)} 帧，脸中心 x={cx*100:.1f}% y={cy*100:.1f}% 脸高={fh*100:.1f}%")
    return cx, cy, fh

# ======================================================================
def make_assets(out: Path, L: dict):
    """白环+阴影静态层 + 圆形遮罩（PIL）。"""
    from PIL import Image, ImageDraw, ImageFilter
    CW,CH=L["canvas"]["w"],L["canvas"]["h"]; G=L["geom"]
    d=G["ring_d"]; r=d//2; cx,cy=G["ring_cx"],G["ring_cy"]
    sh=Image.new("RGBA",(CW,CH),(0,0,0,0))
    ImageDraw.Draw(sh).ellipse([cx-r-4,cy-r-4+14,cx+r+4,cy+r+4+14],fill=(20,20,20,90))
    sh=sh.filter(ImageFilter.GaussianBlur(18))
    ring=Image.new("RGBA",(CW,CH),(0,0,0,0))
    ImageDraw.Draw(ring).ellipse([cx-r,cy-r,cx+r,cy+r],fill=(255,255,255,255))
    Image.alpha_composite(sh,ring).save(out/"ring.png")
    cd=G["circle_d"]; m=Image.new("L",(cd,cd),0); ImageDraw.Draw(m).ellipse([0,0,cd-1,cd-1],fill=255)
    m.save(out/"mask.png")

# ======================================================================
def render_pages(pages, out: Path, L: dict):
    """page spec → HTML → PNG（node+puppeteer）。画幅由 layout 决定。"""
    builder=TEMPLATES[L["template"]]; CW,CH=L["canvas"]["w"],L["canvas"]["h"]
    for i,sp in enumerate(pages):
        (out/f"page_{i}.html").write_text(builder(sp), encoding="utf-8")
        subprocess.run(["node", str(HERE/"render_page.js"), str(out/f"page_{i}.html"),
                        str(out/f"page_{i}.png"), str(CW), str(CH)], check=True)

# ======================================================================
# 字幕：标定的 libass 真实字宽（PingFang SC 回退渲染，FS=36）
def _cwid(c, FS):
    if '一'<=c<='鿿' or c in "，。！？、；：—…“”（）《》": return 0.708*FS
    if c.isascii() and c.isalpha(): return 0.472*FS
    if c.isdigit(): return 0.431*FS
    if c==' ': return 0.25*FS
    return 0.389*FS
def _textw(s,FS): return sum(_cwid(c,FS) for c in s)
def _pill(W,H,r):
    k=round(r*0.5523)
    return (f"m {r} 0 l {W-r} 0 b {W-r+k} 0 {W} {r-k} {W} {r} l {W} {H-r} "
            f"b {W} {H-r+k} {W-r+k} {H} {W-r} {H} l {r} {H} b {r-k} {H} 0 {H-r+k} 0 {H-r} "
            f"l 0 {r} b 0 {r-k} {r-k} 0 {r} 0")
def _secs(ts):
    h,m,rest=ts.split(":"); s,ms=rest.split(","); return int(h)*3600+int(m)*60+int(s)+int(ms)/1000
def _asst(t):
    h=int(t//3600); m=int(t%3600//60); s=t%60; return f"{h}:{m:02d}:{s:05.2f}"

def load_fixes(profile="zh_main"):
    # 迁移阶段3：张和 ASR 纠错映射 = 账号数据，抽到定制层 profiles/<profile>/fixes.json
    p=_ENGINE_ROOT/"profiles"/profile/"fixes.json"
    if not p.exists(): return []
    raw=json.loads(p.read_text(encoding="utf-8"))
    out=[]
    for pat,rep in raw:
        out.append((re.compile(r'(?<![A-Za-z])'+pat+r'(?![A-Za-z])', re.I), rep))
    return out
def fix_text(t, fixes):
    for pat,rep in fixes: t=pat.sub(rep,t)
    return re.sub(r'\s{2,}',' ',t).strip()

def _chunk(text, MAX=13.0):
    toks=re.findall(r"[A-Za-z0-9]+|[一-鿿]|[，。！？、；：]|\s+|.",text)
    def w(t):
        if re.match(r"[A-Za-z0-9]+",t): return max(len(t)*0.6,0.6)
        if t.isspace(): return 0.3
        return 1.0
    out=[];cur="";cw=0.0
    for t in toks:
        if cw+w(t)>MAX and cur.strip(): out.append(cur.strip());cur="";cw=0.0
        cur+=t;cw+=w(t)
        if t in "，。！？；" and cw>=MAX*0.6: out.append(cur.strip());cur="";cw=0.0
    if cur.strip(): out.append(cur.strip())
    merged=[]
    for p in out:
        if merged and len(re.sub(r"[^A-Za-z0-9一-鿿]","",p))<2: merged[-1]+=p
        else: merged.append(p)
    return merged or [text]

def make_subtitles(srt: Path, out: Path, profile="zh_main", L: dict|None=None):
    L=L or load_layout()
    S=L["sub"]; FS,CY,PAD,H,R=S["FS"],S["CY"],S["PAD"],S["H"],S["R"]
    CW,CH=L["canvas"]["w"],L["canvas"]["h"]; CX=CW//2
    fixes=load_fixes(profile); ev=[]
    for b in srt.read_text(encoding="utf-8").strip().split("\n\n"):
        cuelines=b.split("\n")
        if len(cuelines)<3: continue
        t0,t1=[_secs(x.strip()) for x in cuelines[1].split("-->")]
        zh=[x for x in cuelines[2:] if re.search(r"[一-鿿]",x)]
        keep=fix_text((zh[0] if zh else cuelines[2]).strip(), fixes)
        pcs=_chunk(keep); tot=sum(len(p) for p in pcs) or 1; cur=t0
        for p in pcs:
            seg=(t1-t0)*len(p)/tot; s,e=_asst(cur),_asst(cur+seg); cur+=seg
            W=round(_textw(p,FS))+2*PAD; PX=round((CW-W)/2); PYt=CY-H//2
            ev.append(f"Dialogue: 0,{s},{e},Pill,,0,0,0,,{{\\pos({PX},{PYt})\\an7\\p1}}{_pill(W,H,R)}{{\\p0}}")
            ev.append(f"Dialogue: 1,{s},{e},Cap,,0,0,0,,{{\\pos({CX},{CY})\\an5}}{p}")
    hdr=(f"[Script Info]\nScriptType: v4.00+\nPlayResX: {CW}\nPlayResY: {CH}\nScaledBorderAndShadow: yes\n\n"
         "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
         f"Style: Cap,PingFang SC,{FS},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1\n"
         f"Style: Pill,PingFang SC,{FS},&H00141414,&H000000FF,&H00141414,&H00141414,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n\n"
         "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    (out/"zh.ass").write_text(hdr+"\n".join(ev)+"\n", encoding="utf-8")

# ======================================================================
def ffprobe_dur(path) -> float:
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","csv=p=0",str(path)],capture_output=True,text=True).stdout.strip())

def compose(job, out: Path, face_cx: float, face_cy: float, face_fh: float, clip_h: int, strip_px: int, L: dict):
    """ffmpeg：PPT层翻页(slide) + 静态白环 + 人像圆形 + 字幕。输出 paginated.mp4。"""
    G=L["geom"]; CW,CH=L["canvas"]["w"],L["canvas"]["h"]
    pages=job["pages"]; n=len(pages); D=job.get("params",{}).get("transition",G["transition"])
    dur=ffprobe_dur(job["video"])
    src_w=job.get("src_w",1920); src_h=clip_h
    if src_w >= src_h:                          # 横屏源：原逻辑——满高方裁、从顶部(人物占满高度)
        side=clip_h-strip_px
        x0=int(min(max(face_cx*src_w-side/2,0),max(0,src_w-side)))
        y0=0
    else:                                       # 竖屏源：头肩方裁 → 避开上方 PPT
        # 构图锁定（geom 配了 pip_face_ratio 即启用）：脸高占圆固定比例 + 眼睛纵向固定位置，
        # 使每条切片头肩大小/位置一致；未配则退回旧逻辑(2.2×脸高·脸居中)保逐字节不变。
        face_ratio=G.get("pip_face_ratio")
        if face_ratio:
            vpos=G.get("pip_face_vpos", 0.42)
            side=int(min(max(face_fh*src_h/face_ratio, src_w*0.30), src_w))
            y0=int(min(max(face_cy*src_h-vpos*side, 0), max(0,src_h-side)))
            print(f"  [pip] 构图锁定 脸占圆{face_ratio:.0%} 眼高{vpos:.0%} side={side} y0={y0}")
        else:
            side=int(min(max(face_fh*src_h*2.2, src_w*0.45), src_w))
            y0=int(min(max(face_cy*src_h-side/2,0),max(0,src_h-side)))
            print(f"  [pip] 竖屏源头肩方裁 side={side} y0={y0}（旧逻辑·脸居中）")
        x0=int(min(max(face_cx*src_w-side/2,0),max(0,src_w-side)))
    cd=G["circle_d"]; cx,cy=G["circle_x"],G["circle_y"]
    starts=[p["start"] for p in pages]
    F=[]
    F.append(f"[0:v]scale={CW}:{CH},setsar=1[b0];")
    for i in range(1,n): F.append(f"[{i}:v]scale={CW}:{CH},setsar=1[p{i}];")
    prev="b0"
    for i in range(1,n):
        T=starts[i]
        sl=(f"x='if(lt(t,{T}),{CW},if(lt(t,{T}+{D}),{CW}*(1-(t-{T})/{D}),0))':y=0:enable='gte(t,{T})'")
        tag=f"s{i}" if i<n-1 else "ppt"
        F.append(f"[{prev}][p{i}]overlay={sl}[{tag}];"); prev=tag
    clip_in=n; ring_in=n+1; mask_in=n+2   # ffmpeg 输入序: pages(0..n-1) → clip(n) → ring(n+1) → mask(n+2)
    F.append(f"[{prev}][{ring_in}:v]overlay=0:0[wr];")
    F.append(f"[{clip_in}:v]crop={side}:{side}:{x0}:{y0},scale={cd}:{cd},setsar=1,format=rgba[spk];")
    F.append(f"[spk][{mask_in}:v]alphamerge[pip];")
    F.append(f"[wr][pip]overlay={cx}:{cy}[o];")
    F.append(f"[o]subtitles={out/'zh.ass'}[v]")
    (out/"compose_filter.txt").write_text("\n".join(F))
    cmd=["ffmpeg","-y","-loglevel","error"]
    for i in range(n): cmd+=["-loop","1","-i",str(out/f"page_{i}.png")]
    cmd+=["-ss","0","-t",str(int(dur)+1),"-i",str(job["video"]),
          "-i",str(out/"ring.png"),"-loop","1","-i",str(out/"mask.png")]
    cmd+=["-filter_complex_script",str(out/"compose_filter.txt"),
          "-map","[v]","-map",f"{clip_in}:a","-r","25","-c:v","libx264","-preset","veryfast",
          "-crf","21","-pix_fmt","yuv420p","-c:a","aac","-shortest","-movflags","+faststart",
          str(out/"paginated.mp4")]
    subprocess.run(cmd,check=True)

def accelerate(job, out: Path):
    """按逐字稿语速对成片整体自适应变速。输出 accel.mp4。"""
    pr=job.get("params",{}); TGT=pr.get("target_cps",ACCEL["target_cps"]); MX=pr.get("max_speed",ACCEL["max_speed"])
    GAP=ACCEL["gap_speed"]; MN=ACCEL["min_speed"]
    src=out/"paginated.mp4"; DUR=ffprobe_dur(src)
    cues=[]
    for b in Path(job["srt"]).read_text(encoding="utf-8").strip().split("\n\n"):
        L=b.split("\n")
        if len(L)<3: continue
        t0,t1=[_secs(x.strip()) for x in L[1].split("-->")]
        txt=" ".join(L[2:]); nn=len(re.sub(r"[^一-鿿A-Za-z0-9]","",txt))
        cues.append([t0,min(t1,DUR),nn])
    cues.sort()
    segs=[]; cur=0.0
    for t0,t1,nn in cues:
        if t0>cur+0.05: segs.append((cur,t0,GAP))
        d=t1-t0; cps=nn/d if d>0 else TGT
        segs.append((t0,t1,min(max(TGT/cps if cps>0 else MN,MN),MX))); cur=t1
    if cur<DUR-0.05: segs.append((cur,DUR,GAP))
    F=[]; vc=[]; ac=[]
    for i,(s,e,sp) in enumerate(segs):
        F.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=(PTS-STARTPTS)/{sp:.4f}[v{i}];")
        F.append(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS,atempo={sp:.4f}[a{i}];")
        vc.append(f"[v{i}]"); ac.append(f"[a{i}]")
    od=sum((e-s)/sp for s,e,sp in segs)
    fo=float(pr.get("fade_out_sec", 2.0))       # 结尾音效淡出(默认2s，防结尾突兀)
    if fo>0:
        F.append("".join(f"{vc[i]}{ac[i]}" for i in range(len(segs)))+f"concat=n={len(segs)}:v=1:a=1[v][araw];")
        F.append(f"[araw]afade=t=out:st={max(0.0,od-fo):.3f}:d={fo:.3f}[a]")
    else:
        F.append("".join(f"{vc[i]}{ac[i]}" for i in range(len(segs)))+f"concat=n={len(segs)}:v=1:a=1[v][a]")
    (out/"accel_filter.txt").write_text("\n".join(F))
    print(f"  [accel] {len(segs)}段 目标{TGT}cps 均速{DUR/od:.2f} {DUR:.0f}s→{od:.0f}s 末{fo}s淡出")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(src),
        "-filter_complex_script",str(out/"accel_filter.txt"),"-map","[v]","-map","[a]",
        "-r","25","-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p",
        "-c:a","aac","-movflags","+faststart",str(out/"accel.mp4")],check=True)

# ======================================================================
def run(job_path: str, out_root: str|None, skip_accel: bool, profile="zh_main", layout="vertical"):
    job=json.loads(Path(job_path).read_text(encoding="utf-8"))
    name=job.get("name", Path(job_path).stem)
    L=load_layout(job.get("layout") or layout)     # job 可钉死画幅(横版 job 写 "layout":"landscape")
    out=Path(out_root or HERE/"out")/name; out.mkdir(parents=True, exist_ok=True)
    print(f"[{name}] → {out}  (layout={L['name']})")
    # 探测源画幅
    info=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
        "stream=width,height","-of","csv=p=0",str(job["video"])],capture_output=True,text=True).stdout.strip()
    sw,sh=[int(x) for x in info.split(",")[:2]]; job["src_w"]=sw
    strip_px=int(job.get("subtitle_strip_px",0))   # 源底部烧死字幕条高度(腾讯合成轨常见;纯说话人轨=0)
    calib=job.get("pip_calib")                     # 批量标定值：整段录屏定一次，所有切片共用→大小/位置零飘动
    if calib:
        fcx,fcy,ffh=float(calib["cx"]),float(calib["cy"]),float(calib["fh"])
        print(f"  [1/6] 人脸定位(用批量标定值) x={fcx*100:.1f}% y={fcy*100:.1f}% 脸高={ffh*100:.1f}%")
    else:
        print("  [1/6] 人脸定位"); fcx,fcy,ffh=locate_face_cx(job["video"])
    print("  [2/6] 静态资源(白环/遮罩)"); make_assets(out, L)
    print("  [3/6] 渲染框架图页"); render_pages(job["pages"], out, L)
    print("  [4/6] 字幕(纠错+药丸)"); make_subtitles(Path(job["srt"]), out, profile, L)
    print("  [5/6] 合成(翻页+PIP+字幕)"); compose(job, out, fcx, fcy, ffh, sh, strip_px, L)
    if skip_accel:
        print("  [6/6] 跳过变速"); print(f"完成 → {out/'paginated.mp4'}"); return
    print("  [6/6] 自适应变速"); accelerate(job, out)
    print(f"完成 → {out/'accel.mp4'}")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("job"); ap.add_argument("--out", default=None)
    ap.add_argument("--skip-accel", action="store_true")
    ap.add_argument("--profile", default="zh_main")
    ap.add_argument("--layout", default="vertical", help="版式 layouts/<name>.json（vertical|landscape）")
    a=ap.parse_args(); run(a.job, a.out, a.skip_accel, a.profile, a.layout)
