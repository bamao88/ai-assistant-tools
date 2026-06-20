# 视频剪辑 skill 回归测试套件

分层回归：喂**冻结的金标准夹具**、逐能力比对，不每次从 3 小时源头重头跑。
完整设计与逐能力清单见 [`var/zh_main/0619test/doc/视频剪辑skill-回归测试计划.md`](../../../var/zh_main/0619test/doc/视频剪辑skill-回归测试计划.md)。

## 跑

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools
python engines/video-compose/regression/run_regression.py t0          # 纯数据/单元·秒级·每次提交跑
python engines/video-compose/regression/run_regression.py t1          # 单原子·复用 golden 视频·分钟级
python engines/video-compose/regression/run_regression.py t2          # 阶段集成
python engines/video-compose/regression/run_regression.py t3          # 端到端 + G4 零回归 + ①火山转录·发版前
python engines/video-compose/regression/run_regression.py all         # 一条龙
python engines/video-compose/regression/run_regression.py t3 --skip-slow   # 跳过 demucs/G4/转录/e2e 重步骤
python engines/video-compose/regression/run_regression.py t3 --keep-llm    # T3 真跑 LLM ai_fix（默认关·非确定）
```

退出码 0=全绿，1=有红。每条打印 ✅/❌ + 实测值。

## 文件

| 文件 | 作用 | 跟踪 |
|---|---|---|
| `run_regression.py` | 四层 runner（读 expected.json，喂 golden，断言） | git |
| `expected.json` | 金标准期望值（时长/hash/条数/账本 keeps/G4 页 hash） | **git** |
| `gen_expected.py` | 金标准变了重算 expected.json | git |
| `catalog.json`(上级目录) | 总能力表 | git |
| `var/zh_main/0619test/golden/` | 金标准大媒体（body/trimmed/final/srt/zh.ass/vocals…） | gitignored·本地 |

## 改了金标准怎么办

1. 重新冻结 `var/zh_main/0619test/golden/` 里对应产物。
2. `python engines/video-compose/regression/gen_expected.py` 重算期望值。
3. `git diff expected.json` 确认变化符合预期（别把回归当基线悄悄改绿）。

> ⚠️ **WS-6 伴随轨重构（2026-06-20）后必须重冻 golden 再跑 t2/t3**：字幕改走伴随轨、烧字移到最后，
> 像素时间线和 `clip.srt` 语义都变了（`clip.srt` 现在是 assembled 轴 40 条·不再是成片轴 30 条；新增
> `final.srt`/`final_shifted.srt`/`成片_nosub.mp4`，不再有 `body_subbed.mp4`）。重冻前 t2 的「subtitle_align
> 复现 golden srt」会红——这是**正确信号**（提醒重冻），不是代码回归。重冻办法：用新管线端到端跑一遍进
> golden 夹具目录，再走上面 1→2→3。新序端到端证据：`var/zh_main/ws6_ride/clip_01/`。详见
> `doc/bug/ws6_chain-clip01-音画字幕-诊断.md` 与 `doc/video-skill-architecture.md`。

## 慢步骤口径

- **LLM**（ai_fix）非确定 → 默认关，`--keep-llm` 才真跑；断言只看结构（1:1/无吞字）。
- **demucs / G4 / 火山转录 / 端到端** → 只在 T3 真跑；`--skip-slow` 可跳过。
- T0/T1/T2 全用冻结产物，不碰这些慢且要钱/算力的。

## 换机器复现

需要：系统 ffmpeg(含 libass) + `engines/video-framework-render/.venv`(pillow+opencv+puppeteer) +
demucs venv(`var/zh_main/0618test/.audio_venv` 或 `engines/video-clip/.venv-audio`) + 火山/LLM 凭证(`var/credentials/`)。
金标准媒体不入库——按计划 doc 的"金标准夹具"小节从 `var/zh_main/{ws6_chain2,ws2_verify}/` curate 重建。
