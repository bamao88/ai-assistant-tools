---
name: zh-video-cover
description: |
  张和口播视频封面生成器（evc 宋体渐变风格，张和唯一认可的口播切片封面样式，标杆 ZHC20260613_evc*）。
  给定底图库 + 已定标题 → 一条命令出 3:4 封面（1242×1660）：张和人像帧 + 底部黑色渐变 +
  思源宋体白字 + 2px 描边。全部风格参数固化在 kit（字体/渐变/上移/字号/轮换），不再逐次口头调。
  支持单张，也支持批量（一批切片：按发布顺序底图轮换、相邻不撞、各写 item 的 cover.png + 出对比总览图）。
  当用户说「做张和视频封面/口播封面/切片封面/宋体封面/evc 封面」「给这批切片生成封面」
  「批量出封面」「换个底图重出封面」时触发。
  不处理：9:16 黑块黄字样式封面（→ platform-publish 的 video-cover/zhanghe cover-kit.json）、
  公众号横版封面（→ platform-publish gongzhonghao kit）、小红书图文卡片（→ markdown-to-cards）、
  起标题文案本身（→ dbs-xhs-title，本 skill 只把给定标题烧进封面）、内容发布上传（→ platform-publish）。
scope: assistant_zh
compatibility: claude-code
allowed-tools:
  - Bash
  - Read
---

# zh-video-cover — 张和口播视频封面(evc 宋体渐变)

薄入口（router）。把「底图库 + 渐变素材 + 已定标题」按固化参数一键渲成 3:4 封面。
**为什么存在**：evc 样式过去只是临时脚本、参数靠对话现调、每次来回；现在全部参数收进
`assets/cover-kit-evc.json` 单一真源，脚本零硬编码，一条命令跑完。

- **代码 + 配置真源**：`assets/generate_evc_cover.py`（kit 驱动）+ `assets/cover-kit-evc.json`（风格参数）。
- **共享品牌资产**（与黑块黄字 kit 共用，留在 platform-publish 原地，kit 按路径引用；改底图池/换渐变去这里）：
  底图池 `/Volumes/ExtSSD2601/AI_Assistant/tools/skills/platform-publish/assets/video-cover/zhanghe/covers/`（frame-01..05，**排除 frame-06**）、
  同目录 `gradient-3x4-bottom-black.png`。日常用只需传 `--base frame-0X` 池内名，路径由 kit 内部解析，无需知道绝对路径。
- 参数全表、批量 manifest 格式、硬边界、与候选标题/dbs 的衔接见 `references/evc-style.md`。
- **好封面标准 + 生成后自检调整 + 底图轮换纪律 + 底图不够怎么抽帧补 见 `references/quality-and-base-management.md`（生成后必读必做）。**

## 硬边界（decision_gate，调用前核）

① 张和本人口播出镜？② 要 3:4 宋体渐变(evc)样式？**两条都 yes 才用本 kit**。
非张和 / 屏幕录制 / 9:16 黑块黄字 / 公众号横版 → 另选方案（见 kit `usage.do_not_use_for`）。

## 怎么跑

```bash
GEN=/Volumes/ExtSSD2601/AI_Assistant/tools/skills/zh-video-cover/assets/generate_evc_cover.py
PY=/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-clip/.venv/bin/python   # 需 PIL

# 单张：2 行标题用 | 分行；省略 --base 走 round-robin
"$PY" "$GEN" --title "别再喊AI元年了|2026是重启之年" --output /abs/path/cover.png
"$PY" "$GEN" --title "A|B" --base frame-03 --output ...            # 指定底图，不推进游标
"$PY" "$GEN" --title "A|B" --base frame-03 --lift 0.25 --output ... # 自检后脸偏低→加大上移重出

# 批量（一批切片）：manifest.json 见 references/evc-style.md
"$PY" "$GEN" --batch manifest.json --overview /abs/overview.png
```

## 🔴 生成后必做（不是跑完就完 —— 详见 references/quality-and-base-management.md）

1. **看图自检**：`Read` 输出（批量看 `overview.png`），逐张按「好封面标准」核 —— **人脸在视觉中心、头顶留白适中、字够大（短句更大）**。
2. **不达标就调**：脸偏低/贴底 → `--lift` 加大（如 0.25）单张重出；脸贴顶 → 减小（如 0.125）；字挤 → 换更短候选标题。调到脸在视觉中心为止。
3. **查底图重复**：批量输出的 `base_usage` / `warnings` —— 同一底图一批里 **>2 次即过度重复**。`warnings` 非空说明底图池不够。
4. **底图不够**：先翻 `assets/video_cover_base/`，没有就去媒体库 `/Volumes/ExtSSD2601/media/` 找最近张和口播视频抽帧（find-images 方式三 / `screenshot/video_frame.py`），筛正脸不闭眼的竖帧丢进 `covers/`；**判断不了就停下反馈用户**，别硬凑重复底图发出。

## 标题从哪来

从**已生成的候选标题**里挑字数合适/好裁的，可轻裁不擅改（`feedback_cover_text_from_titles`）；
每条 2 行。可选先用 `dbs-xhs-title` 公式生成候选。本 skill 只负责把给定标题烧进封面，不起标题。

## 验证 / 回退

- 金标准：用 `assistant_zh/tmp/d2c_cover_fix/` 那批 13 条重跑 `--batch`，输出与 `final/d2cNN.png`
  逐张哈希一致（已验，见 `references/evc-style.md`）。
- 回退 tag：`pre-evc-cover-skill`（tools 仓）。
