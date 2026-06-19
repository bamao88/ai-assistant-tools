# 视频剪辑 skill：架构 + 维护指南

> **要更新 / 迭代视频 skill（口播切片成片这条线）就先读这份文档。** 它告诉你东西在哪、怎么改、怎么验证不回归。
> 这份是「现状真源 + 怎么动手」；要看**为什么这么设计 / 迁移决策 / 历史**，去 [`video-tools-migration-plan.md`](./video-tools-migration-plan.md)。

## 一句话定位

把张和口播 → 竖版切片成片这条业务，按「**原子能力 + 可选组合**」组织成**四个引擎**。
组织原则**不是引擎边界，而是能力组合**：能力是积木、配方是把积木串起来的预设，AI 按视频选配方或自由组合。
句级 / 词级两套剪辑策略**共存**（不是谁替代谁）。

成片有**两种风格**，都走同一条**六环主链**，只在第⑤环「铸造」时选不同风格：
- **PPT 框架页版**（配方 `zh_business`）：按内容重绘设计页 + 人脸抠成圆窗。渲染已定型、有 G4 基线不许回归。
- **裁剪版**（配方 `zh_clip_cut`）：把录屏本身收拾干净——裁切放大铺满 + 盖掉多余 UI + 烧药丸字幕。

## 六环主链：剪辑流程的骨架（先看这个）

每条切片都走这条**线性流水线**（像工厂传送带，每件产品都过这几道工位）：

```
① 转写 → ② 选片 → ③ 裁剪(时间轴) → ④ 字幕(文字) → ⑤ 铸造(风格化) → ⑥ 组装成片
 听成字   剪哪句    粗剪/去静音/变速    搬时间/改错词    PPT版/裁剪版/钩子片   多片合并+标题
                    ★最易错·承重墙      ★最易错·承重墙
```

横切层（不占主链，谁需要谁挂）：
- **源适配**（按「这块毛料是什么」加清洗附件，主要挂③）：干净口播=啥都不挂；录屏=裁切+盖按钮(`reframe_crop`+`name_mask --black`)；带噪=去背景音(`denoise_voice`，demucs，缺失优雅跳过)。
- **自检门**（每环做完跑个小脚本读数字，AI 自己判过/不过）：③④门最严——`align_check`(切点准/字幕贴口型) + `len_check`(身子时长对，防烧错身子)。

**承重墙＝剪辑账本（cut manifest）**：这是裁剪版根治「音画对不上」的核心。大白话——**字幕的时间不是事后再去对的，它就是③那把剪刀剪出来的结果**。③裁剪每做一个时间操作（选段+顺序、去静音保留区间、变速倍数）就记一笔进一本「账本」（`cut_manifest.json`）；④ 字幕照账本**重放**，把每个字的源时间依次套上同一串操作，自然落到它在成片里的位置。剪刀(③)管对齐、AI(④)只换字，字幕同步从构造上就不会乱。账本读写 + 重放算法在 `video-clip/atoms/_manifest.py`（`remap_time`）。

**看这条线长什么样**：`python engines/video-compose/run.py --plan zh_clip_cut`（按六环分组列出每个原子、挂载点、自检门）。

## 四层模型 + 目录布局

```
能力组织：① catalog 能力 → ② recipes 配方 → ③ select 选择 → ④ engines 布局（原子住哪）

tools/engines/
├── video-compose/            ★ 组合层 · 唯一对外入口（只指挥，不产原子）
│   ├── catalog.json          总能力表（真源·跨引擎汇总；每个原子带六环 stage 标签，由 build_catalog.py 重建）
│   ├── recipes.json          命名配方：zh_business(PPT版) / zh_clip_cut(裁剪版·真chain) / landscape_business / raw_quickcut / simple_concat / chaptered_growth
│   ├── selector.py           AI 读视频 → 选配方 / 自由组合（--list 按六环分组展示）
│   ├── run.py                按配方解析能力链 → 跨引擎调原子（--plan 审链 / --run 跑；真chain 委派 runner）
│   ├── clip_cut_run.py       zh_clip_cut 链式执行器（六环原子按序串起来端到端出片，剪辑账本流转）
│   └── build_catalog.py      从各引擎 capabilities.json 重建 catalog（透传 stage/layer/required/substep/source_types）
│
├── video-slicer/             积木厂 · 剪辑策略 + 内容决策（Python 包，纯 urllib LLM，无独立 venv）
│   ├── capabilities.json     声明：cut_sentence(句级·线上) / cut_word(词级·方案B) 共存 + transcribe + subtitle_align/subtitle_protect(④承重墙)
│   ├── video_slicer/         planner + twostage + pages_gen(分页) + srt_fix(字幕纠错)
│   │   ├── subtitle_align.py     ④读剪辑账本搬字幕时间（承重墙·复用字级机器·remap_time 链式重放）
│   │   ├── subtitle_protect.py   ④别动清单钉回(自造词如「爱马仕」防 LLM 改) + 1:1/无吞字结构自检
│   │   └── profiles/zh_main/keeplist.json  别动清单（受保护词数组）
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
│   ├── layouts/              vertical.json / landscape.json / clip_cut.json(裁剪版 1080×1920=vertical×1.5)（几何外置，--layout 选）
│   ├── video_framework_render/subtitles_cli.py  把药丸渲染(make_subtitles)暴露成独立入口给裁剪版⑤复用（不改渲染逻辑·G4 零触碰）
│   ├── capabilities.json     声明：framework_reframe / compose / accelerate / subtitles / reframe_locate / raw
│   ├── profiles/zh_main/     fixes.json（账号 ASR 术语表）
│   └── requirements.txt      pillow + opencv-python-headless（首跑建 .venv）
│
└── video-clip/               积木厂 · 通用叠加/裁剪/自检原子（独立 .venv）
    ├── atoms/*.py            通用叠加: concat / prepend_hook / progress_bar / endcard / subtitle_burn / subtitle_ai_fix / cover_frame / title_bar / face_locate
    │                          ③裁剪(承重墙): rough_cut(3a切段拼身子) / trim_silence(3c去长静音吐区间) / speed_adapt(3d固定档+换轨)
    │                          源适配(录屏/带噪): reframe_crop(裁外框) / name_mask(--black 多块挡UI) / denoise_voice(demucs可选)
    │                          自检门: align_check(门A切点+门D字幕对齐) / len_check(身子时长防烧错)
    │                          剪辑账本: _manifest.py(账本读写+remap_time 重放·非原子·承重墙数据模型)
    ├── assets/fonts/         自带字体（title_bar 用思源宋体超粗体 SourceHanSerifCN-Heavy.otf）
    └── capabilities.json     声明叠加+③裁剪+源适配+自检 原子（带六环 stage 标签）
```

**铁律**：
- **依赖单向** `video-compose → 各引擎`；三个积木厂**互不调用**，只各自声明能力。
- **多租户定制集中**：账号特定的 prompt / 术语 / 几何全在 `engines/<engine>/profiles/<account>/`，**不散回业务项目**。
- **产物落点**：工具直出默认 `var/<account>/`（gitignored）；`--out` / `--out-root` 可改落点；项目在产物之上的加工（发布版、定稿文案）归项目自管。
- **业务侧只剩薄胶水**：`assistant_zh/workflow/video_framework_slicer/` = `run_pipeline.py`(选 profile + 落点) + ③项目加工；渲染 / 选段 / 叠加全在 tools。

## 入口命令（都在 video-compose）

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools
python engines/video-compose/selector.py --list                 # 看全部能力原子(按六环分组) + 配方
python engines/video-compose/run.py --plan zh_clip_cut           # 审裁剪版六环链（每环原子→引擎+源适配挂载点+自检门）
python engines/video-compose/run.py --run zh_business \
       --selection sel.json --profile zh_main                    # PPT版：端到端跑一条切片
python engines/video-compose/run.py --run zh_clip_cut \
       --job job.json                                            # 裁剪版：一键出片（job 规格见 clip_cut_run.py --help）
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
| **给成片加顶部标题**（贴纸式白底黑字 / 旧黑底白字整条） | `engines/video-clip/atoms/title_bar.py IN OUT --text 标题`。两种样式：`--style bar`（默认·顶部黑底白字整条）；`--style label`（顶部黑色信箱块里**白底黑字圆角贴纸**·单行·块高自动探测顶部黑边）。字色/底色 `--bar-color`/`--text-color` 可覆盖。 |
| **成片前置开篇钩子 + 翻页转场** | `engines/video-clip/atoms/prepend_hook.py 钩子 正文 OUT [--flip 0.30] [--trans slideleft]`。钩子→翻页(翻页期间正文定格暂停)→正文，自动统一画幅/帧率+音频过渡。与 `concat`（硬切拼接，无转场）互补。 |
| **出一条裁剪版成片**（录屏裁剪版竖版切片） | `run.py --run zh_clip_cut --job job.json` 一键端到端。job 规格（源/选段spec、words.json、术语表、别动清单、标题、钩子、是否 denoise/ai_fix、基准时长、落点）见 `clip_cut_run.py --help`。剪辑账本(`cut_manifest.json`)在原子间流转，自动跑③④⑤⑥+自检门。 |
| **改去长静音/变速口径**（裁剪版③） | 去静音：`trim_silence.py` 的 `--min-sil`(多长算长停顿,默认1.5s)/`--keep-pad`(保留缓冲)/`--noise`(静音阈)；变速：`speed_adapt.py --fixed 1.2`(整体倍速)。静音检测**用干净人声当参考最准**——job 给 `vocals` 现成人声、或 `denoise:true` 跑 demucs(需装 audio venv)。 |
| **改裁剪版药丸字幕位置/大小** | 改 `video-framework-render/layouts/clip_cut.json` 的 `sub`(FS字号/CY纵向中心/H药丸高/R圆角)。它=竖版 vertical.json ×1.5；**复用同一份 make_subtitles 几何**，不在别处再写第二份。 |
| **改录屏裁切框 / 挡 UI 块**（源适配） | 裁切框：`reframe_crop.py --source X (--crop W:H:X:Y | --detect)` 吐 crop_vf（录屏 UI 版式固定，通常存进 job spec 的 `crop_vf` 当常量）；挡块：`name_mask.py IN OUT --region WxH+X+Y --region ... --black`（多块黑挡）或直接写进 job spec 的 `mask_boxes`(rough_cut 切段同趟盖)。 |
| **保护字幕里的自造词**（别动清单） | 往 `engines/video-slicer/profiles/zh_main/keeplist.json` 加词（如「爱马仕」「直觉机器」）。`subtitle_protect` 会在 LLM 订正后把被改掉的受保护词强制钉回，并做 1:1 条数 + 无空格吞字自检。 |
| **整条切片"加标题+拼钩子"一键收尾**（标题取自选题文案） | 业务粘合脚本 `var/zh_main/0618test/finalize_clip.py <clip号>`：自动从对应 item `publish_copy.md`「标题候选」✅ 取标题 → `title_bar --style label` 烧标题 → `prepend_hook` 前置钩子。clip↔item 映射见该脚本与 `var/zh_main/0618test/doc/钩子+标题-成片收尾流程.md`。 |
| **换/加转写后端**（字级线地基） | `video-slicer/video_slicer/transcribe/`：火山 seedasr v3 主 + 阿里 paraformer 兜底；上传公网默认、阿里 OSS 备选(`--uploader oss`)。火山 key 入 `var/credentials/aliyun.env`。输出对齐 `twostage/resolve.py` 词表 schema。 |
| **改去口水/承接句判断**（字级线） | 改 `video-slicer/references/字级去口水与承接句保护.md`（删前保后 + 四类高危承接句红线，cut_word 去口水的判断基底）。 |
| **字幕/文案带标点 ITN**（字级线） | 去口水输入用**句级带标点 ITN 文本**（`run_cut.py` 建富 token → `script_clean.clean_to_keep(rich_tokens=…)`），删后经 `transcribe/align.py` 对回字级拿时间 → 字幕/文案/PPT输入(读 srt)带标点和"90%"。无原生句或对不齐 → 自动降级回字级裸拼（不断流）。原生效果待火山实跑验证。 |
| **跑一条切片验证** | 竖版 `run.py --run zh_business --selection <sel>.json --profile zh_main`；横版 `run.py --run landscape_business --selection <sel>.json`；产物 `var/<account>/.../accel.mp4`。 |
| **改完验证不回归（G4）** | `var/zh_main/baseline/` 存了冻结基线（`primaries/` 含可重放 `job.json`）。用引擎 venv 重放该 job.json，与基线逐帧/逐字节比对。方法 + 上次结果见 `var/zh_main/baseline/{STAGE0-baseline.md,G4-result.md}`。 |
| **建/迭代金标准（评测基准）** | 选段质量的"标准答案"这条线在 `engines/video-slicer/baselines/`：`global_evidence.py`（**四级流水线**：①开场钩子短拼接 ②正文论证结构全局取证 ③组装脚本 ④精修去口水/去重复/开篇独立/结尾干脆，只产候选）+ `score.py`（vs 金标准 → 句号召回/F1 + 时间 IoU）。全新生成用 `--selection`，对已有结果换版式用 `--migrate`。产出②只回真实句号（可经 `resolve.py` 换算成秒）。流程/命令见 `baselines/README.md`；设计见 `doc/plan/video-golden-baseline-plan.md`。**不进生产管线**，是 prompt 迭代的对照尺子。 |
| **登记 / 结构变更后收口** | 改了引擎结构就更新 `registry.yaml`，跑 `python scripts/check-tools.py`（期望 0 error）。 |

## 环境依赖（首跑准备）

- `video-framework-render`：`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`（pillow + opencv）；node puppeteer（`PUPPETEER_PATH` 或本机已装）；系统 ffmpeg(含 libass)；字体 Hannotate SC + PingFang SC。
- `video-clip`：自带 `.venv`（pillow + opencv），首跑 `requirements.txt`。③裁剪/源适配/自检原子多数纯 ffmpeg+系统 python 即可。**带噪去噪**：`denoise_voice` 的 demucs **已装在 `var/zh_main/0618test/.audio_venv`（demucs 4.0.1 + torch 2.12.1，6-18 既有）**，`denoise_voice` 自动探测此处（也认 `VIDEO_AUDIO_VENV` 环境变量、`engines/video-clip/.venv-audio`）；都没有则优雅跳过抽原音轨（不断流）。如需固化可把该 venv 迁到 `engines/video-clip/.venv-audio`。
- `video-slicer`：纯标准库 + urllib LLM，用系统 python 即可；LLM 密钥走 `.env`（→ `var/credentials/llm.env`）。
- `run_pipeline`（业务薄胶水）：用系统 python 跑（含 urllib LLM）；渲染子进程自动走 `video-framework-render/.venv`。

## 相关真源

- 决策 / 迁移历史 / 验收清单全文：[`video-tools-migration-plan.md`](./video-tools-migration-plan.md)
- 六环阶段化 + 裁剪版 + 剪辑账本设计：[`doc/plan/视频剪辑skill-六环阶段化升级-plan.md`](./plan/视频剪辑skill-六环阶段化升级-plan.md)
- 机器可读引擎清单：`registry.yaml`
- G4 基线与回归证据：`var/zh_main/baseline/`（裁剪版承重墙在 clip_01 上验证：身子 78.683s 精确 + 3 帧字幕对口型 + 门A 6/6）
- 裁剪版手搓来源（已产品化·保留参考）：`var/zh_main/0618test/`（`assemble→rough_cut`、`trim_silence→trim_silence`、`build_subs→subtitle_align+subtitles`、`finalize→speed_adapt`）
