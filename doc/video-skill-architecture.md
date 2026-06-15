# 视频剪辑 skill：架构 + 维护指南

> **要更新 / 迭代视频 skill（口播切片成片这条线）就先读这份文档。** 它告诉你东西在哪、怎么改、怎么验证不回归。
> 这份是「现状真源 + 怎么动手」；要看**为什么这么设计 / 迁移决策 / 历史**，去 [`video-tools-migration-plan.md`](./video-tools-migration-plan.md)。

## 一句话定位

把张和口播 → 框架页竖版切片成片这条业务，按「**原子能力 + 可选组合**」组织成**四个引擎**。
组织原则**不是引擎边界，而是能力组合**：能力是积木、配方是把积木串起来的预设，AI 按视频选配方或自由组合。
句级 / 词级两套剪辑策略**共存**（不是谁替代谁）。

## 四层模型 + 目录布局

```
能力组织：① catalog 能力 → ② recipes 配方 → ③ select 选择 → ④ engines 布局（原子住哪）

tools/engines/
├── video-compose/            ★ 组合层 · 唯一对外入口（只指挥，不产原子）
│   ├── catalog.json          总能力表（真源·跨引擎汇总，由 build_catalog.py 重建）
│   ├── recipes.json          命名配方：zh_business(线上主路径) / raw_quickcut / simple_concat / chaptered_growth
│   ├── selector.py           AI 读视频 → 选配方 / 自由组合
│   ├── run.py                按配方解析能力链 → 跨引擎调原子（--plan 审链 / --run 跑）
│   └── build_catalog.py      从各引擎 capabilities.json 重建 catalog
│
├── video-slicer/             积木厂 · 剪辑策略 + 内容决策（Python 包，纯 urllib LLM，无独立 venv）
│   ├── capabilities.json     声明：cut_sentence(句级·线上) / cut_word(词级·方案B) 共存
│   ├── video_slicer/         planner + twostage + pages_gen(分页) + srt_fix(字幕纠错)
│   ├── personas/zh_main.md   张和选题 persona
│   ├── profiles/zh_main/     {pages,srt_fix}_system_prompt.txt（账号 prompt 定制）
│   ├── baselines/            方案A 选段基准（对照用）
│   └── .env                  → 符号链 var/credentials/llm.env（LLM provider 密钥，tools 侧真源）
│
├── video-framework-render/   积木厂 · 框架页竖版渲染（独立 .venv: pillow + opencv-python-headless）
│   ├── video_framework_render/render.py        6 阶段原子：locate/assets/pages/subs/compose/accelerate
│   ├── video_framework_render/render_page.js   puppeteer 渲 HTML→PNG（PUPPETEER_PATH 可指定，否则自动找）
│   ├── capabilities.json     声明：framework_reframe / compose / accelerate / subtitles / reframe_locate / raw
│   ├── profiles/zh_main/     fixes.json（账号 ASR 术语表）；GEOM/版式 = render.py 内置默认
│   └── requirements.txt      pillow + opencv-python-headless（首跑建 .venv）
│
└── video-clip/               积木厂 · 通用叠加原子（独立 .venv）
    ├── atoms/*.py            concat / progress_bar / endcard / name_mask / subtitle_burn / subtitle_ai_fix / speed_adapt / face_locate / cover_frame
    └── capabilities.json     声明 9 个叠加原子
```

**铁律**：
- **依赖单向** `video-compose → 各引擎`；三个积木厂**互不调用**，只各自声明能力。
- **多租户定制集中**：账号特定的 prompt / 术语 / 几何全在 `engines/<engine>/profiles/<account>/`，**不散回业务项目**。
- **产物落点**：工具直出默认 `var/<account>/`（gitignored）；`--out` / `--out-root` 可改落点；项目在产物之上的加工（发布版、定稿文案）归项目自管。
- **业务侧只剩薄胶水**：`assistant_zh/workflow/video_framework_slicer/` = `run_pipeline.py`(选 profile + 落点) + ③项目加工；渲染 / 选段 / 叠加全在 tools。

## 入口命令（都在 video-compose）

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools
python engines/video-compose/selector.py --list                 # 看全部能力原子 + 配方
python engines/video-compose/run.py --plan zh_business           # 审一条配方的能力链（每步原子→引擎→entry）
python engines/video-compose/run.py --run zh_business \
       --selection sel.json --profile zh_main                    # 端到端跑一条切片
```

## 维护场景：要做某件事 → 改哪里

| 想做的事 | 怎么做 |
|---|---|
| **加一个新能力**（结尾卡、字幕加粗变色、画面多排布…） | ① 在所属积木厂 `engines/<engine>/` 写原子代码 → ② 在该引擎 `capabilities.json` 声明 → ③ 跑 `python engines/video-compose/build_catalog.py` 重建总表 → ④ 在 `recipes.json` 引用（或让 AI 自由组合）。**管线骨架不动。** |
| **加一条新配方**（新的能力组合预设） | 在 `engines/video-compose/recipes.json` 加一条，`chain` 列出有序原子；`run.py --plan <name>` 审链路。 |
| **改账号定制**（选题口径 / 术语表 / 版式几何，不碰代码） | 改对应 `engines/<engine>/profiles/<account>/`：选题/分页/纠错 prompt 在 `video-slicer/profiles/`、persona 在 `video-slicer/personas/`、ASR 术语在 `video-framework-render/profiles/<acct>/fixes.json`。 |
| **接一个新账号 / 第二个号** | 新建 `engines/<engine>/profiles/<新account>/`（拷 zh_main 改），调用时 `--profile <新account>`。引擎代码不动。 |
| **改视觉版式**（GEOM / 字幕样式 / PAGE_CSS） | 改 `video-framework-render/video_framework_render/render.py` 顶部 `GEOM` / `SUB` / `PAGE_CSS`（当前 = 张和内置默认）。**改完必跑 G4 回归。** |
| **跑一条切片验证** | 见上「入口命令」`run.py --run zh_business --selection <sel>.json --profile zh_main`；产物 `var/<account>/.../accel.mp4`。 |
| **改完验证不回归（G4）** | `var/zh_main/baseline/` 存了冻结基线（`primaries/` 含可重放 `job.json`）。用引擎 venv 重放该 job.json，与基线逐帧/逐字节比对。方法 + 上次结果见 `var/zh_main/baseline/{STAGE0-baseline.md,G4-result.md}`。 |
| **登记 / 结构变更后收口** | 改了引擎结构就更新 `registry.yaml`，跑 `python scripts/check-tools.py`（期望 0 error）。 |

## 环境依赖（首跑准备）

- `video-framework-render`：`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`（pillow + opencv）；node puppeteer（`PUPPETEER_PATH` 或本机已装）；系统 ffmpeg(含 libass)；字体 Hannotate SC + PingFang SC。
- `video-clip`：自带 `.venv`（pillow + opencv），首跑 `requirements.txt`。
- `video-slicer`：纯标准库 + urllib LLM，用系统 python 即可；LLM 密钥走 `.env`（→ `var/credentials/llm.env`）。
- `run_pipeline`（业务薄胶水）：用系统 python 跑（含 urllib LLM）；渲染子进程自动走 `video-framework-render/.venv`。

## 相关真源

- 决策 / 迁移历史 / 验收清单全文：[`video-tools-migration-plan.md`](./video-tools-migration-plan.md)
- 机器可读引擎清单：`registry.yaml`
- G4 基线与回归证据：`var/zh_main/baseline/`
