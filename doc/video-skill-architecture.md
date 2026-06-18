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
│   ├── capabilities.json     声明：cut_sentence(句级·线上) / cut_word(词级·方案B) 共存 + transcribe
│   ├── video_slicer/         planner + twostage + pages_gen(分页) + srt_fix(字幕纠错)
│   │   └── transcribe/       字级转写：火山 seedasr v3 主 / 阿里 paraformer 兜底；公网/OSS 上传
│   │                          + align.py(句级带标点 ITN ↔ 字级时间 对齐) + segment.py(分句·优先原生语义句)
│   ├── personas/zh_main.md   张和选题 persona（含问答可剪）
│   ├── references/           字级去口水与承接句保护.md（删前保后+承接句红线，cut_word 判断基底）
│   ├── profiles/zh_main/     {pages,srt_fix}_system_prompt.txt（账号 prompt 定制）
│   ├── baselines/            方案A 选段基准 + 金标准/评测基准（global_evidence 生成器 + score 打分器·对照用）
│   └── .env                  → 符号链 var/credentials/llm.env（LLM provider 密钥，tools 侧真源）
│
├── video-framework-render/   积木厂 · 框架页渲染（竖版 720×1280 / 横版 1280×720 同源·独立 .venv: pillow+opencv）
│   ├── video_framework_render/render.py        6 阶段原子 + TEMPLATES(vertical 框架页 / landscape 方框) + PIP 构图锁定/批量标定(--calibrate)
│   ├── video_framework_render/render_page.js   puppeteer 渲 HTML→PNG（画幅参数化，默认 720×1280）
│   ├── layouts/              vertical.json / landscape.json（CANVAS/GEOM/SUB 几何外置，--layout 选）
│   ├── capabilities.json     声明：framework_reframe / compose / accelerate / subtitles / reframe_locate / raw
│   ├── profiles/zh_main/     fixes.json（账号 ASR 术语表）
│   └── requirements.txt      pillow + opencv-python-headless（首跑建 .venv）
│
└── video-clip/               积木厂 · 通用叠加原子（独立 .venv）
    ├── atoms/*.py            concat / progress_bar / endcard / name_mask / subtitle_burn / subtitle_ai_fix / speed_adapt / face_locate / cover_frame / title_bar
    ├── assets/fonts/         自带字体（title_bar 用思源宋体超粗体 SourceHanSerifCN-Heavy.otf）
    └── capabilities.json     声明 10 个叠加原子
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
| **改视觉几何**（画幅 / 圆形人像窗 / 药丸字幕位置） | 改 `video-framework-render/layouts/<vertical|landscape>.json`（CANVAS/GEOM/SUB 已外置，代码不再硬编码）。**改完必跑 G4 回归。** |
| **改圆窗 PIP 构图**（人物在圆里多大 / 眼睛多高） | 改 `vertical.json` 的 `geom.pip_face_ratio`（脸高占圆比例，越大人越大）/ `pip_face_vpos`（脸心在圆内纵向位置，越小人越靠上）。当前 0.42/0.42(脸占42%·眼略上移)。竖版用此构图锁定；横版(landscape)及未配该键的版式仍走旧逻辑(2.2×脸高·脸居中)逐字节不变。**改完必按新构图重冻 G4 基线。** |
| **保证每条切片圆窗大小/位置一致**（免逐条手调） | 圆窗飘动的根因是「每条片各自做角落小脸检测」噪声大。`run_pipeline.py` 已对整段录屏 `video_speaker` **标定一次**(调 `render.py <video> --calibrate` 取 cx/cy/fh)，把 `pip_calib` 注入每条 job → 所有切片共用同一裁框、零飘动。竖版自动启用；标定失败自动退回每条各自定位(不断流)。 |
| **改版式排布**（框架页 / 方框 CSS 结构） | 改 `render.py` 的 `PAGE_CSS`（竖版框架页）/ `PAGE_CSS_LANDSCAPE`（横版方框），或 `TEMPLATES` 注册新模板。 |
| **出横屏成片** | `run.py --run landscape_business --selection <sel>.json`（或渲染 `--layout landscape`）。横版=1280×720 方框版式，视觉 DNA 同竖版（配色/手写字/药丸/圆窗）。同一份 pages 既出竖版又出横版。 |
| **换/加转写后端**（字级线地基） | `video-slicer/video_slicer/transcribe/`：火山 seedasr v3 主 + 阿里 paraformer 兜底；上传公网默认、阿里 OSS 备选(`--uploader oss`)。火山 key 入 `var/credentials/aliyun.env`。输出对齐 `twostage/resolve.py` 词表 schema。 |
| **改去口水/承接句判断**（字级线） | 改 `video-slicer/references/字级去口水与承接句保护.md`（删前保后 + 四类高危承接句红线，cut_word 去口水的判断基底）。 |
| **字幕/文案带标点 ITN**（字级线） | 去口水输入用**句级带标点 ITN 文本**（`run_cut.py` 建富 token → `script_clean.clean_to_keep(rich_tokens=…)`），删后经 `transcribe/align.py` 对回字级拿时间 → 字幕/文案/PPT输入(读 srt)带标点和"90%"。无原生句或对不齐 → 自动降级回字级裸拼（不断流）。原生效果待火山实跑验证。 |
| **跑一条切片验证** | 竖版 `run.py --run zh_business --selection <sel>.json --profile zh_main`；横版 `run.py --run landscape_business --selection <sel>.json`；产物 `var/<account>/.../accel.mp4`。 |
| **改完验证不回归（G4）** | `var/zh_main/baseline/` 存了冻结基线（`primaries/` 含可重放 `job.json`）。用引擎 venv 重放该 job.json，与基线逐帧/逐字节比对。方法 + 上次结果见 `var/zh_main/baseline/{STAGE0-baseline.md,G4-result.md}`。 |
| **建/迭代金标准（评测基准）** | 选段质量的"标准答案"这条线在 `engines/video-slicer/baselines/`：`global_evidence.py`（**四级流水线**：①开场钩子短拼接 ②正文论证结构全局取证 ③组装脚本 ④精修去口水/去重复/开篇独立/结尾干脆，只产候选）+ `score.py`（vs 金标准 → 句号召回/F1 + 时间 IoU）。全新生成用 `--selection`，对已有结果换版式用 `--migrate`。产出②只回真实句号（可经 `resolve.py` 换算成秒）。流程/命令见 `baselines/README.md`；设计见 `doc/plan/video-golden-baseline-plan.md`。**不进生产管线**，是 prompt 迭代的对照尺子。 |
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
