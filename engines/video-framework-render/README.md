# video-framework-render

口播切片 → **手写框架图翻页 + 人像圆形 PIP + 纠错字幕 + 整档定速变速** 竖版成片（720×1280）。

「改造/渲染」积木厂（迁移计划 §3.1）：只提供原子，不指挥。指挥权在 `video-compose`。
原住 `assistant_zh/workflow/video_framework_slicer/`（线上成片主流程），迁移阶段3 迁入并独立成引擎。

## 安装

```bash
cd engines/video-framework-render
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # pillow + opencv-python-headless
# node puppeteer：优先设环境变量，或在本引擎 npm i puppeteer
export PUPPETEER_PATH=/path/to/node_modules/puppeteer   # 或：cd video_framework_render && npm i puppeteer
# 系统需 ffmpeg(含 libass)；字体 Hannotate SC（手写）、PingFang SC（字幕）
```

## 用法

```bash
.venv/bin/python -m video_framework_render.render <job.json> [--out DIR] [--skip-accel] [--profile zh_main]
# 产物 OUT/<name>/：page_*.png  zh.ass  paginated.mp4(原速带翻页)  accel.mp4(自适应变速·最终交付)
```

job.json schema（= pages_gen 输出 + 切片信息）：
```jsonc
{ "name":"...", "video":"/abs/clip.mp4", "srt":"/abs/clip.fixed.srt",
  "subtitle_strip_px":0, "params":{"target_cps":8.0,"max_speed":2.0,"transition":0.5},
  "pages":[{"start":0,"title":"...","blocks":[{"type":"hero","text":"...","uw":330}, ...]}] }
```

## 原子（capabilities.json）

`render.py` 已按 6 阶段原子组织：`locate → assets → render_pages → subtitles → compose → accelerate`。
组合层 `video-compose`（阶段5b）按 catalog 引用这些原子；`framework_reframe` = 当前 zh_business 主路径。

## 定制（多租户，§3.2）

- 锁定几何 `GEOM`/`SUB`/`ACCEL` + `PAGE_CSS`：当前为 `render.py` 内置默认（= 张和 zh_main 默认，§3.1）；阶段5 进一步外置为 `profiles/zh_main/` 文件。
- 账号 ASR 纠错映射：`profiles/<profile>/fixes.json`（`--profile zh_main` 读）。

## ⚠️ 验证状态（迁移阶段3）

结构迁移已验证（py_compile / 导入 / fixes.json 字节一致 / 路径解析）。
**G4 逐帧成片回归 = BLOCKED_NEEDS_LOCAL_VALIDATION**：需装好 venv + puppeteer + 字体后，
用 `tools/var/zh_main/baseline/primaries/` 的冻结 job.json 实跑 `render`，逐帧/逐字节比对 accel.mp4。
