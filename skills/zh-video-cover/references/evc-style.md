# evc 宋体渐变封面 — 参数 / 批量 / 衔接

evc = 张和唯一认可的口播切片封面样式，标杆已发布 `ZHC20260613_evc*`。全部参数在
`assets/cover-kit-evc.json`，改样式改 kit、不改脚本。

> 生成后的**质量自检、人脸 lift 调整、底图轮换纪律、底图不够怎么抽帧补** → 见 `quality-and-base-management.md`（必做）。

## 已固化参数（kit 字段 → 值）

| kit 字段 | 值 | 说明 |
|---|---|---|
| `canvas` | 1242×1660（3:4） | 直接以成品画幅为工作画布 |
| `text.font_file` | `fonts/SourceHanSerifCN-Heavy.otf` | 思源宋体 Heavy（衬线），bundled 自包含 |
| `gradient.file` | `gradient-3x4-bottom-black.png` | 白顶黑底，叠加 alpha=255−L；在共享目录 |
| `text.color/stroke` | 白 #ffffff + 2px 黑描边 | |
| `text.center_y_frac` | 0.75 | 文字垂直中心在 0.75·H |
| `text.max_line_width_px` | 1060 | 字号驱动：最长行 ≤1060px 的最大字号 |
| `text.max_font_px/min_font_px` | 132 / 78 | 短句自动放大到 132 封顶、长句缩到 78 |
| `base_crop.lift_default` | 0.1875（3/16） | 人物上移比例；1/8 太低、5/16 太高，3/16 最舒服 |
| `base_crop.lift_overrides` | {} | 可 per-frame 覆盖（如某底图人物偏高用更小值） |
| `rotation.exclude` | `["frame-06.png"]` | 贴脸自拍帧一提就切发，本风格排除 |
| `rotation.state_file` | `.rotation_state_evc.json` | 单张游标，与黑块黄字 `.rotation_state.json` 互不干扰 |

底图库 = 共享 `.../video-cover/zhanghe/covers/` 的 frame-01..05（新底图丢进去自动纳入，除非进 exclude）。

## 底图选择逻辑（三态）

- `--base-image PATH`：外部底图，覆盖轮换，不推进游标。
- `--base frameXX`：池内按文件名指定，不推进游标。
- 都不给：
  - **单张**：读写 `.rotation_state_evc.json` 游标，round-robin 取下一张。
  - **批量**：按列表顺序 `pool[seq % len]` 取模，**不碰游标**——纯确定性、可重跑一致，且列表相邻必然不同帧（相邻不撞底图）。

## 单张

```bash
PY=/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-clip/.venv/bin/python
GEN=/Volumes/ExtSSD2601/AI_Assistant/tools/skills/zh-video-cover/assets/generate_evc_cover.py
"$PY" "$GEN" --title "第一行|第二行" [--base frame-03|--base-image /abs.png] [--output /abs/cover.png]
```

## 批量（一批切片）

manifest.json：

```json
{
  "items": [
    {"content_id": "d2c01", "title": "别再喊AI元年了|2026是重启之年",
     "output": "/abs/.../content/zh_main/items/ZHC20260701_d2c01_001/cover.png"},
    {"content_id": "d2c12", "title": "转型AI产品经理|就干这3件事", "output": "/abs/.../ZHC20260701_d2c12_001/cover.png"}
  ],
  "publish_order": ["d2c01", "d2c12", "..."]
}
```

- `items[].title`：2 行，用 `|` 或 `\n` 分行。
- `items[].output`：写到各 item 目录的 `cover.png`（真源）。
- `publish_order`（可选）：显式发布顺序；底图按此顺序取模轮换，保证**相邻发布不撞底图**。省略则按 items 顺序。

```bash
"$PY" "$GEN" --batch manifest.json --overview /abs/overview.png
```

输出：各 `cover.png` + 一张对比总览图（按顺序每列一条，标 `content_id` + 底图帧）+ JSON（含 `content_id→base` 映射、`adjacent_collisions` 自检、overview 路径）。`adjacent_collisions` 非空即相邻撞图，需检查。

## 标题来源约定

从**已生成的候选标题**里挑字数合适/好裁的，允许轻裁不擅改（`feedback_cover_text_from_titles`）；封面文字不必等于视频标题。可选先跑 `dbs-xhs-title` 出候选。本 skill 不起标题，只烧字。

## 下游

写进 item `cover.png` 后，发布走 `platform-publish`（视频号封面走 `tencent-video-publish` 的 `cli.py`，见 platform-publish `references/shipinhao.md`）。

## 金标准验证（回归用）

用 `assistant_zh/tmp/d2c_cover_fix/` 的 13 条构 manifest（title 取定稿、`publish_order` = `d2c01,d2c12,d2c11,d2c13,d2c02,d2c05,d2c07,d2c04,d2c03,d2c08,d2c06,d2c09,d2c10`），跑 `--batch` 到临时目录，逐张与 `tmp/d2c_cover_fix/final/d2cNN.png` 做 `md5` diff——应全部一致（证明 kit 驱动 ≡ 认可原型）。2026-07-01 首次落地已验：13/13 identical、零相邻撞图、frame-06 从不出现。

## 边界

非张和 / 屏幕录制 / 9:16 黑块黄字 / 公众号横版 / 小红书图文卡 → 不用本 kit，见 SKILL.md 硬边界与 kit `usage.do_not_use_for`。
