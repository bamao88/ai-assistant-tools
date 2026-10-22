---
name: video-clip
description: |
  口播/长视频到成片的统一工作流：转录 → 选题与成片脚本 → 人工确认 → 剪辑、字幕、PPT/原画铸造与组装。支持竖版手写白板 PPT、横版 PPT、保留原画面的快剪，以及拼接、钩子、片尾、标题、字幕、变速、裁切、遮 UI、PIP 轻美颜等按需处理。
  用户说“剪视频/做成片/出片/做口播切片/生成 PPT 风格成片/框架页竖版/横屏成片/原视频风格快剪/录屏裁剪/拼几段视频/加字幕、标题、钩子、片尾、变速、遮名、美颜”时触发。
  一条长视频还没选题时也由本 Skill 负责前半段，但选题/成片脚本必须停下来给人确认后才能继续剪。
  不负责：只要逐字稿/字幕/关键帧而不出片（video-content）；发布分发（Agent-Publish）；平台抓取（platform-fetch）；把现成 .pptx 转视频；替用户决定标题文案（本 Skill 只烧录已给定/已确认标题）。
---

# video-clip — 口播 / 长视频 → 成片

通用能力：账号定位、事实、素材与输出位置遵循当前项目；项目已有专属入口时优先沿其规则衔接。

## 角色

本 Skill 是唯一用户入口。它负责判断这单怎么走、在哪里停、产物去哪、哪些质量门必须过。

执行统一从 `engines/video-compose/` 进入；`video-select`、`video-slicer`、`video-framework-render`、`video-clip` 是背后的四个能力引擎，不单独触发。

```text
输入 → Skill 分流 → video-compose → 四个能力引擎 → 产物 + QC
```

能力库存的真源是各引擎 `capabilities.json`；跨引擎总表 `catalog.json` 只能由 `build_catalog.py` 生成；默认组合只认 `recipes.json`。不要在本文件维护第二份能力清单。

## 开工前按顺序做

1. **判断输入**：长视频未选题、已有成片脚本、已有片段，或单个原子动作。
2. **决定输出落点**：读 `output_routing.json`；用户路径优先。项目任务不知道 content_id 时先解析或问，不得静默落 `var/`。
3. **判断时间基准**：切点来自字级 ASR 时，读 `references/quality-gates.md` 的时间基准门；非零源起点未声明基准时停止。
4. **判断源类型**：干净口播 / 录屏 / 带噪 / 口播 PIP，只按实际需要挂源适配。
5. **选择成片风格和配方**：见下表；先 `--plan` 审链，再 `--run`。
6. **标出人工门**：选题脚本、美颜联系表、PPT 视觉变更都不能自动越过。

详细步骤和 job 示例：读 `references/workflows.md`。

## 入口分流

### A. 长视频，还没有成片脚本

```text
① 转录 → ② 选题/成片脚本 → 🛑人工确认 → ③裁剪 → ④字幕 → ⑤铸造 → ⑥组装
```

- ① 固定入口：`engines/video-slicer/transcribe-01.sh <视频>`。
- ② 在 `engines/video-select/` 跑 `topics → generate → 可选 dedup → gates`，生成 `candidates/clip_NN.md`。
- 🛑 把人读候选给用户确认；确认前不自动往下剪。
- 确认后进入 B。

### B. 已有成片脚本 / 已选片段

| 目标 | 默认配方 | 关键默认 |
|---|---|---|
| 竖版手写白板 PPT + 圆窗人像 | `zh_business` | `layout=vertical`，整档 1.25x；视觉已锁 |
| 横版 PPT | `landscape_business` | 横版方框，视觉 DNA 同源 |
| 保留原画面的口播快剪 | `zh_clip_cut` | 默认不裁画幅，去废/长静音、药丸字幕、1.2x |
| 极简词级快剪 | `raw_quickcut` | 先审 plan；按原子计划执行 |
| 纯拼接 / 章节成长片 | `simple_concat` / `chaptered_growth` | 轻量任务可直接调原子 |

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools
python engines/video-compose/selector.py --list
python engines/video-compose/run.py --plan zh_clip_cut
python engines/video-compose/run.py --run zh_clip_cut --job /abs/job.json
python engines/video-compose/run.py --run zh_business --selection /abs/selection.json --profile zh_main
```

### C. 只做一个动作

拼接、标题、钩子、片尾、遮 UI、裁画幅、抽封面等可直调原子。命令集中在 `references/atomic-commands.md`，不要把整条管线拆成手搓命令。

## 必经质量门

- **原片只读**：所有输出写新路径，可重复运行。
- **时间基准门**：ASR/WAV 时间剪原 MOV 时，显式记录并应用 `source_time_offset`；`rough_cut` 对含糊的非零起点拒绝运行。
- **三轨同刀**：凡动时间轴，画、音、字幕使用同一映射；每个出口跑 `align_check`，失败即停。
- **选题人工门**：机器门禁通过不等于内容已批准。
- **PPT 风格锁**：未经用户明确要求，不改 `pages_system_prompt.txt`、竖版 `PAGE_CSS`、`vertical.json`，不改用旧 `vertical_ppt`。
- **美颜人工门**：WXP 可用已确认 preset；正式合成前必须看 compare/preview，其他账号不自动瘦脸。
- **证据归档**：账本、SRT 链、QC、人工确认和成片随内容 item 保存。

完整规则和故障处理：读 `references/quality-gates.md`。

## 按任务加载 reference

| 任务 | 必读 |
|---|---|
| 真实出片 | `references/workflows.md` + `references/quality-gates.md` |
| 单个叠加/源适配 | `references/atomic-commands.md` + 对应质量门 |
| 修改本 Skill、能力、配方、profile、路由或测试 | `references/maintenance.md` + `doc/video-skill-architecture.md` |
| 改转录链 | `doc/转录标准流程-01.md` |
| 改选片 prompt/eval | `engines/video-select/README.md` + `engines/video-select/eval/README.md` |

Skill references 只放现行操作规则。计划、提案、迁移历史统一放 `doc/plan/`。

## 完成定义

交付前确认：成片可播放；画音/字幕/切点门通过；必留句短样抽查通过；人工门有确认；产物和 QC 落点正确。命令退出码 0 不是完成的充分条件。

## 维护收口

只要修改了能力、配方、入口或行为，同一次改动必须同步 `doc/video-skill-architecture.md`，并至少运行：

```bash
python engines/video-compose/verify_contracts.py
python -m unittest discover -s engines/video-clip/tests -p 'test_*.py'
(cd engines/video-slicer && python3 -m pytest tests/test_text_pipeline.py -q)
python engines/video-compose/regression/run_regression.py t0
python scripts/check-tools.py
```

更高风险按 `references/maintenance.md` 追加 T1/T2/T3/G4。
