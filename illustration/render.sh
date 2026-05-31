#!/usr/bin/env bash
# render.sh — 把 HTML 配图渲染成高清 PNG（用本机已装的 Chrome 无头模式，零额外依赖）
#
# 用法:
#   ./render.sh <input.html> [output.png] [WxH]
#
#   - input.html   必填，要渲染的 HTML 文件
#   - output.png   可选，默认与输入同名（.html -> .png）
#   - WxH          可选画布尺寸，如 1600x900。不填则读取 HTML 里的
#                  <meta name="render-size" content="1600x900">，再没有则默认 1600x900
#
# 输出为 @2x 高清图（force-device-scale-factor=2），即 1600x900 -> 实际 3200x1800。
set -euo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || { echo "找不到 Chrome: $CHROME" >&2; exit 1; }

IN="${1:?用法: render.sh <input.html> [output.png] [WxH]}"
[ -f "$IN" ] || { echo "输入文件不存在: $IN" >&2; exit 1; }

OUT="${2:-${IN%.html}.png}"

# 决定画布尺寸：参数 > HTML meta > 默认
SIZE="${3:-}"
if [ -z "$SIZE" ]; then
  SIZE="$(grep -oE 'name="render-size"[^>]*content="[0-9]+x[0-9]+"' "$IN" \
            | grep -oE '[0-9]+x[0-9]+' | head -1 || true)"
fi
SIZE="${SIZE:-1600x900}"
W="${SIZE%x*}"; H="${SIZE#*x}"

# 转成 file:// 绝对路径
ABS="$(cd "$(dirname "$IN")" && pwd)/$(basename "$IN")"

"$CHROME" --headless=new --disable-gpu --hide-scrollbars --no-sandbox \
  --force-device-scale-factor=2 \
  --window-size="${W},${H}" \
  --default-background-color=00000000 \
  --screenshot="$OUT" "file://${ABS}" >/dev/null 2>&1

[ -f "$OUT" ] && [ -s "$OUT" ] || { echo "渲染失败，未生成: $OUT" >&2; exit 1; }
echo "✓ 渲染完成: $OUT  (画布 ${W}x${H} @2x)"
