# xhs-interior-design skill 字体路径硬编码为 Linux，Mac 本地无法运行

## 工具
`xhs-interior-design`（Skill 路径：`assistant_hj/.claude/skills/xhs-interior-design/`）

## 问题描述

`design_system.py` 里的字体路径常量全部硬编码为 Linux/Claude 云沙箱路径：

```python
# design_system.py:37-54
LATIN_FONT_DIR = "/mnt/skills/examples/canvas-design/canvas-fonts"
CJK_FONT_DIR   = "/usr/share/fonts/opentype/noto"
EMOJI_FONT     = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

CJK_SERIF_REG    = f"{CJK_FONT_DIR}/NotoSerifCJK-Regular.ttc"
CJK_SERIF_SEMI   = f"{CJK_FONT_DIR}/NotoSerifCJK-SemiBold.ttc"
CJK_SERIF_BOLD   = f"{CJK_FONT_DIR}/NotoSerifCJK-Bold.ttc"
# ...
LATIN_ITALIANA  = f"{LATIN_FONT_DIR}/Italiana-Regular.ttf"
LATIN_MONO      = f"{LATIN_FONT_DIR}/GeistMono-Bold.ttf"
```

在 macOS 本地运行时，这些路径全部不存在。

## 复现

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/assistant_hj
python3 -c "
import sys
sys.path.insert(0, '.claude/skills/xhs-interior-design')
import layouts
layouts.make_cover(
    photo_path='.claude/skills/xhs-interior-design/assets/clean-interior.jpg',
    output_path='/tmp/test.jpg',
    title='测试'
)
"
```

## 实际行为

```
File ".../xhs-interior-design/shared.py", line 23, in load_font
    _font_cache[key] = ImageFont.truetype(path, size)
OSError: cannot open resource
```

## 期望行为

跨平台字体回退：runtime 检测 OS，在 macOS 用 `/System/Library/Fonts/` 或 Homebrew cask 路径（`/opt/homebrew/Caskroom/font-noto-*/`）。

建议的回退链：

```python
import platform
IS_MAC = platform.system() == "Darwin"

if IS_MAC:
    LATIN_FONT_DIR = "~/Library/Fonts"  # 用户需要自行安装 Italiana + GeistMono
    CJK_FONT_DIR   = "/opt/homebrew/Caskroom/font-noto-serif-cjk-sc/latest"
    # fallback 到系统 Songti/Hiragino
else:
    LATIN_FONT_DIR = "/mnt/skills/examples/canvas-design/canvas-fonts"
    CJK_FONT_DIR   = "/usr/share/fonts/opentype/noto"
```

同时 README 需要列出 Mac 用户的字体安装指引：
- `brew install --cask font-noto-serif-cjk-sc font-noto-sans-cjk-sc`
- 从 Google Fonts 下载 Italiana / GeistMono 到 `~/Library/Fonts/`

## 当前临时绕过

调用端做 monkey-patch（不改 skill 源文件），在 import `layouts` 前覆盖 `design_system` 模块常量为 Mac 系统字体。脚本样例：`assistant_hj/tmp/gen_covers_工地干净.py`

这个 workaround 的副作用：
- Mac 宋体/STHeiti 替代思源宋体/黑体，中文字重偏轻
- Georgia 替代 Italiana，英文 kicker 不如原 Italiana 细优雅
- Menlo 替代 GeistMono，字形差异较明显

视觉 70% 还原，能做草稿评审但不适合最终发布素材。

## 影响

- HJ Agent 本地无法正常用该 skill 生成封面/配图
- 只要 agent 要生成小红书配图（cover / caption / plain / tutorial 四种都受影响），都卡住
- 当前每次出封面都要 agent 手动 monkey-patch，流程不闭环

## 优先级建议

中-高。HJ 账号起号期配图频繁，这是持续卡点。

## 相关产物

本次 workaround 产出的 3 张封面（用 Mac 系统字体替代版）：
- `assistant_hj/content/draft/covers_2026-04-20_工地干净/cover_A_frame11.jpg`
- `assistant_hj/content/draft/covers_2026-04-20_工地干净/cover_B_rank05.jpg`
- `assistant_hj/content/draft/covers_2026-04-20_工地干净/cover_C_rank11.jpg`
