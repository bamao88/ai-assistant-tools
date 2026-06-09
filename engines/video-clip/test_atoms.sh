#!/bin/bash
# video-clip 全功能回归测试。每个原子的每条路径都打到。产物全在本目录(var/,gitignore)。
set -u
ENG=/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-clip
W=/Volumes/ExtSSD2601/AI_Assistant/tools/var/video-clip/_test
cd "$W"
PASS=0; FAIL=0; FAILED=()
ff(){ ffmpeg -y -loglevel error "$@"; }
dur(){ ffprobe -v error -show_entries format=duration -of csv=p=0 "$1" 2>/dev/null; }
ok(){ # ok <label> <file>  —— 文件存在且(视频有时长 / 图片可探测)
  local lbl="$1" f="$2"
  if [ ! -f "$f" ]; then echo "  ✗ $lbl (无产物 $f)"; FAIL=$((FAIL+1)); FAILED+=("$lbl"); return; fi
  if [[ "$f" == *.png || "$f" == *.jpg ]]; then
    ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$f" >/dev/null 2>&1 \
      && { echo "  ✓ $lbl"; PASS=$((PASS+1)); } || { echo "  ✗ $lbl (图损坏)"; FAIL=$((FAIL+1)); FAILED+=("$lbl"); }
  else
    local d; d=$(dur "$f")
    if [ -n "$d" ] && (( $(echo "$d > 0" | bc -l) )); then echo "  ✓ $lbl (${d}s)"; PASS=$((PASS+1));
    else echo "  ✗ $lbl (时长异常 d=$d)"; FAIL=$((FAIL+1)); FAILED+=("$lbl"); fi
  fi
}
PY="$ENG/.venv/bin/python"; [ -x "$PY" ] || PY=python3   # 引擎 venv(含 pillow+cv2)
run(){ "$PY" "$ENG/atoms/$@"; }

echo "### 准备 fixtures"
ff -f lavfi -i testsrc=size=720x1280:rate=25:duration=4 -f lavfi -i sine=frequency=300:duration=4 -c:v libx264 -pix_fmt yuv420p -c:a aac a.mp4
ff -f lavfi -i testsrc2=size=720x1280:rate=25:duration=4 -f lavfi -i sine=frequency=400:duration=4 -c:v libx264 -pix_fmt yuv420p -c:a aac b.mp4
ff -f lavfi -i testsrc=size=640x360:rate=30:duration=3 -f lavfi -i sine=frequency=200:duration=3 -c:v libx264 -pix_fmt yuv420p -c:a aac small.mp4
ff -f lavfi -i testsrc=size=1080x1920:rate=25:duration=4 -f lavfi -i sine=frequency=350:duration=4 -c:v libx264 -pix_fmt yuv420p -c:a aac big.mp4
cat > t.srt <<'EOF'
1
00:00:00,000 --> 00:00:02,000
这是第一句用 cloud code 测试

2
00:00:02,300 --> 00:00:03,800
第二句讲 honeystone 工程很关键
EOF
python3 -c "from PIL import Image,ImageDraw; im=Image.new('RGBA',(720,1280),(0,0,0,180)); d=ImageDraw.Draw(im); d.rectangle([60,560,660,720],fill=(255,107,92,255)); im.save('card.png'); im.convert('RGB').save('card.jpg')"
python3 -c "from PIL import Image,ImageDraw; m=Image.new('L',(250,250),0); ImageDraw.Draw(m).ellipse([0,0,249,249],fill=255); m.save('circle.png')"
REAL=/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/workflow/video_framework_slicer/out_v1/v1_c18_把项目当求职项目理解不同代际/accel.mp4
HTMLCARD=/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/workflow/video_vertical/endcard.html

echo "### 1 concat"
run concat.py c_copy.mp4 --inputs a.mp4 b.mp4              >/dev/null; ok "concat 同规格(copy路径)" c_copy.mp4
run concat.py c_re.mp4 --inputs a.mp4 small.mp4            >/dev/null; ok "concat 异规格(reencode路径)" c_re.mp4
run concat.py c_tg.mp4 --inputs a.mp4 small.mp4 --target 480x854 --fps 30 >/dev/null; ok "concat --target 覆盖" c_tg.mp4

echo "### 2 progress-bar"
run progress_bar.py a.mp4 pb_lbl.mp4 --chapters 4 --index 2 --label "第二幕·被批评" >/dev/null; ok "progress-bar 章节+CJK标签" pb_lbl.mp4
run progress_bar.py a.mp4 pb_nolbl.mp4 --chapters 3 --index 1 >/dev/null; ok "progress-bar 无标签/3幕第1" pb_nolbl.mp4
run progress_bar.py a.mp4 pb_color.mp4 --chapters 4 --index 4 --color 33A1FF --h 18 >/dev/null; ok "progress-bar 颜色/高度/末幕" pb_color.mp4

echo "### 3 endcard"
run endcard.py a.mp4 ec_png.mp4 --card card.png --seconds 1.5 --fade 0.4 >/dev/null; ok "endcard png" ec_png.mp4
run endcard.py a.mp4 ec_jpg.mp4 --card card.jpg --seconds 1.2 >/dev/null; ok "endcard jpg" ec_jpg.mp4
run endcard.py a.mp4 ec_html.mp4 --card "$HTMLCARD" --seconds 1.5 >/dev/null; ok "endcard html(渲染路径)" ec_html.mp4

echo "### 4 speed-adapt"
run speed_adapt.py a.mp4 sp.mp4 --srt t.srt --target_cps 8 >/dev/null; ok "speed-adapt 基本" sp.mp4
run speed_adapt.py a.mp4 sp_dump.mp4 --srt t.srt --dump-filter >/dev/null; ok "speed-adapt --dump-filter" sp_dump.mp4
[ -f sp_dump.accel_filter.txt ] && { echo "  ✓ dump-filter 落盘"; PASS=$((PASS+1)); } || { echo "  ✗ dump-filter 未落盘"; FAIL=$((FAIL+1)); FAILED+=("dump-filter落盘"); }

echo "### 5 subtitle-burn"
run subtitle_burn.py a.mp4 sub720.mp4 --srt t.srt >/dev/null; ok "subtitle-burn 720x1280" sub720.mp4
run subtitle_burn.py big.mp4 sub1080.mp4 --srt t.srt --fs 48 >/dev/null; ok "subtitle-burn 1080x1920自适应+fs" sub1080.mp4

echo "### 6 subtitle-ai-fix (走LLM)"
run subtitle_ai_fix.py t.srt t.fixed.srt --hint "AI产品分享" >/dev/null 2>&1
if python3 -c "
import sys
def n(p): return open(p,encoding='utf-8').read().count('-->')
import os
assert os.path.exists('t.fixed.srt'), 'no output'
a,b=n('t.srt'),n('t.fixed.srt')
assert a==b, 'count mismatch in=%d out=%d'%(a,b)
print('  cues=%d'%a)
"; then echo "  ✓ subtitle-ai-fix 等长1:1"; PASS=$((PASS+1)); else echo "  ✗ subtitle-ai-fix"; FAIL=$((FAIL+1)); FAILED+=("ai-fix"); fi

echo "### 7 face-locate"
run face_locate.py a.mp4 > fl_noface.json 2>/dev/null
python3 -c "import json;d=json.load(open('fl_noface.json'));assert d['faces_found']==0;print('  ✓ face-locate 无脸回退')" && PASS=$((PASS+1)) || { echo "  ✗ face-locate 无脸"; FAIL=$((FAIL+1)); FAILED+=("face无脸"); }
CLIP="/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/workflow/video_framework_slicer/out_v1/v1_c18_把项目当求职项目理解不同代际/clip.mp4"
if [ -f "$CLIP" ]; then
  run face_locate.py "$CLIP" --target 720x744 > fl_real.json 2>/dev/null
  python3 -c "import json;d=json.load(open('fl_real.json'));assert d['faces_found']>0;assert 'ffmpeg_crop' in d;print('  ✓ face-locate 真脸 found=%d %s'%(d['faces_found'],d['ffmpeg_crop']))" && PASS=$((PASS+1)) || { echo "  ✗ face-locate 真脸"; FAIL=$((FAIL+1)); FAILED+=("face真脸"); }
fi

echo "### 8 name-mask"
run name_mask.py a.mp4 nm_copy.mp4 --region 250x250+235+900 >/dev/null; ok "name-mask 无黑帧(copy)" nm_copy.mp4
ff -i a.mp4 -f lavfi -i color=black:s=250x250:d=4 -filter_complex "[0:v][1:v]overlay=235:900:enable='between(t,1.5,2.5)'[v]" -map "[v]" -map 0:a -c:v libx264 -pix_fmt yuv420p -c:a aac blk.mp4
run name_mask.py blk.mp4 nm_ov.mp4 --region 250x250+235+900 >/dev/null; ok "name-mask 覆盖路径" nm_ov.mp4
run name_mask.py blk.mp4 nm_mask.mp4 --region 250x250+235+900 --mask circle.png >/dev/null; ok "name-mask 圆形alpha" nm_mask.mp4
run name_mask.py blk.mp4 nm_trim.mp4 --region 250x250+235+900 --trim 1.0 >/dev/null; ok "name-mask --trim裁片头" nm_trim.mp4

echo "### 9 cover-frame"
run cover_frame.py a.mp4 cov.png --at 2 >/dev/null; ok "cover-frame 基本" cov.png
run cover_frame.py a.mp4 cov_ov.png --at 1 --overlay card.png >/dev/null; ok "cover-frame --overlay" cov_ov.png

echo "### R1 recipe simple_concat (=concat) 已覆盖"
echo "### R2 recipe chaptered_growth 端到端(chen_growth 4幕→各加进度条→拼接)"
GD=/Volumes/ExtSSD2601/media/tencent/_camp4_chen_growth/clips_by_stage
NAMES=("第一幕·立项迷茫" "第二幕·被批评" "第三幕·小有成就" "第四幕·标杆")
FILES=("$GD/C同学_第一幕_立项迷茫.mp4" "$GD/C同学_第二幕_被批评.mp4" "$GD/C同学_第三幕_小有成就.mp4" "$GD/C同学_第四幕_标杆.mp4")
ACTS=()
for i in 0 1 2 3; do
  ff -t 2 -i "${FILES[$i]}" -c:v libx264 -pix_fmt yuv420p -c:a aac "act_raw_$i.mp4"   # 截2s 提速
  run progress_bar.py "act_raw_$i.mp4" "act_$i.mp4" --chapters 4 --index $((i+1)) --label "${NAMES[$i]}" >/dev/null
  ACTS+=("act_$i.mp4")
done
run concat.py growth.mp4 --inputs "${ACTS[@]}" >/dev/null
ok "chaptered_growth 成片(4幕)" growth.mp4

echo ""
echo "=================================================="
echo "PASS=$PASS  FAIL=$FAIL"
[ $FAIL -gt 0 ] && { printf '失败项: %s\n' "${FAILED[@]}"; exit 1; } || echo "ALL GREEN"
