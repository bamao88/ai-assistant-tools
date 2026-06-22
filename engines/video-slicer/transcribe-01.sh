#!/bin/zsh
# transcribe-01.sh —— 六环主链第①环「转录」的固定标准入口。
#
# 后续所有「把视频/音频转成逐字稿」的 01 步骤都走这个脚本，别再手敲长命令。
# 它封装了已验证（44s ~ 2.2h 都跑通）的整条流程：
#   ① 自动开本地网络分流（route-bypass，整条链路走本地出口，VPN 照开不用关）
#   ② ffmpeg 抽音频  ③ 上传公网（uguu→0x0，走本地）  ④ 火山转录(主)·阿里(兜底)
#   ⑤ 落 words.json（字级词表）+ 顺手导一份 transcript.txt 全文方便人看
#
# 用法：
#   ./transcribe-01.sh <视频/音频路径> [输出目录]
# 默认输出目录 = 视频同目录下的 transcript/（跟素材放一起）。
#
# 故障速查：
#   - 弹 Mac 管理员密码框：第①步开本地分流要改路由表，输一次即可，VPN 不用关。
#   - 报「上传失败」：八成是没走本地分流；脚本已自动 apply，重跑一次即可。
#   - 别用 --uploader oss：阿里 OSS 凭证 2026-06 已过期、已停用，默认 public 即可。

set -euo pipefail

SCRIPT_DIR="${0:A:h}"   # = engines/video-slicer

SRC="${1:-}"
if [[ -z "$SRC" ]]; then
  print -u2 "用法: $0 <视频/音频路径> [输出目录]"
  exit 2
fi
SRC="${SRC:A}"          # 转绝对路径
if [[ ! -f "$SRC" ]]; then
  print -u2 "✗ 文件不存在: $SRC"
  exit 1
fi

OUT_DIR="${2:-${SRC:h}/transcript}"
mkdir -p "$OUT_DIR"

print "① 转录（六环第①环·标准流程）"
print "  源 : $SRC"
print "  出 : $OUT_DIR/words.json"
print ""

cd "$SCRIPT_DIR"
python3 -m video_slicer.transcribe --audio "$SRC" --out-dir "$OUT_DIR"

# 顺手把全文导成 .txt，方便人直接读（不影响 words.json）。
python3 - "$OUT_DIR" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
d = json.loads((out / "words.json").read_text(encoding="utf-8"))
(out / "transcript.txt").write_text(d.get("full_text", ""), encoding="utf-8")
print(f"  全文: {out/'transcript.txt'}（{len(d['words'])} 字）")
PY

print "✓ 第①环转录完成 → $OUT_DIR/"
