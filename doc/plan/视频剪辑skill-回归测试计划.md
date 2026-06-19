# 视频剪辑 skill：分阶段回归测试计划

> 写于 2026-06-19。读者是不读代码的 owner——先讲"怎么测、为什么这么测"，技术名词都配大白话。
> 目标：**每个能力都有回归测试**、**分阶段跑**（不是每次都全量）、**最大化复用已有数据**（不让每个测试都从 3 小时源头重头跑）。
> 配套真源：[`video-skill-architecture.md`](../video-skill-architecture.md)（能力清单）、[`视频剪辑skill-六环阶段化升级-plan.md`](./视频剪辑skill-六环阶段化升级-plan.md)（这次建的东西）。

---

## 一、核心思路：流水线本身就是一串"夹具"

六环主链是一条**传送带**，每个原子吃上一个原子的产出。所以做回归测试不用每次从源头跑——
**把跑通过的中间产物冻结成"金标准"（golden），测某个原子时就喂它上游的金标准产物、比对它自己的金标准产出**。

大白话：测"去静音"这道工序，不用重新录像+粗剪，直接把上次粗剪好的半成品（金标准 body）拿来喂给它，看它吐出来的还跟上次一样不一样。

```
产物流水线（每个 → 是一个原子；方括号=该原子的金标准产物，回归就盯它）
 spec+source ─[rough_cut]→ [body 107.766s + 账本①]
                              │
        [body]+[vocals] ─[trim_silence]→ [trimmed 94.495s + 账本②keeps]
                              │
   [trimmed]+[vocals_t] ─[speed_adapt]→ [final 78.683s + 账本③factor]
                              │
       [账本]+words ─[subtitle_align]→ [clip.srt 30条]   ← 纯文本，秒级
                              │
        [clip.srt] ─[subtitle_ai_fix(LLM)]→ aifix.srt ─[subtitle_protect]→ [final.srt]
                              │
        [final.srt] ─[subtitles_cli]→ [zh.ass]  ─烧[final]→ subbed ─[title_bar]→ titled ─[prepend_hook]→ [成片]
                              │
       [final]+[srt] ─[align_check/len_check]→ [门A 6/6·门D 无漂·len +0.000]
```

**关键洞察**：④字幕、⑤药丸这些"数据变换"步骤的金标准产物是**文本/字节**（srt、ass、账本 JSON），
比对它们**根本不用碰视频、秒级出结果**。真正"重"（要重编码视频）的只有少数几个原子和整链——其余全靠喂金标准复用。

---

## 二、金标准夹具：冻结一套、长期复用

把这次对 clip_01 跑通并验过的产物，**curate 冻结**成回归基准，放 `var/zh_main/regression/clip_01/`：

| 类别 | 内容 | 存哪 |
|---|---|---|
| **输入夹具**（fixtures） | `clip_01_spec.json`、`words.json`、`fixes.json`、`keeplist.json`、demucs `vocals.wav`、钩子片.mp4 | `regression/clip_01/in/`（大媒体 gitignored） |
| **金标准中间产物**（golden） | `body.mp4`(107.766)、`trimmed.mp4`(94.495)、`final.mp4`(78.683)、`cut_manifest.json`、`clip.srt`、`zh.ass`、`成片.mp4` | `regression/clip_01/golden/`（gitignored） |
| **金标准期望值**（小·可入库） | 一份 `expected.json`：各产物时长、关键 hash、字幕条数(30)、账本 keeps、门数字、G4 页 hash | `engines/video-compose/regression/expected.json`（**tracked**·版本控制） |

> 设计要点：**大媒体进 `var/`（gitignored，机器本地）；期望值是小 JSON 进 git**。
> 这样断言口径有版本控制、换机器/换人也能复现，又不用把几百 MB 视频塞进仓库。
> 来源：本次 `var/zh_main/{ws2_verify,ws6_chain2,ws6_denoise,ws6_g4,baseline}/` 里已有全部产物，curate 拷过去即可。

非确定性步骤的金标准怎么定（不能逐字节比）：
- **LLM**（subtitle_ai_fix）：文本会变 → 只断言**结构**（1:1 条数、无空格吞字、关键术语仍正确），不比原文。
- **x264 重编码**（final/成片/render）：字节会变 → 断言**时长 + SSIM≥阈**，不比字节（G4 教训）。
- **demucs**：够确定（实测两次 107.712 差 3µs）→ 断言时长 + 波形相关度。
- **puppeteer 页 PNG**：确定（G4 实测逐像素一致）→ hash 比对。

---

## 三、四层测试金字塔（分阶段的"阶段"）

| 层 | 测什么 | 复用什么 | 成本 | 何时跑 |
|---|---|---|---|---|
| **T0 纯单元/数据** | 不碰视频的逻辑：账本重放、分句、别动清单、药丸 ASS、审链快照、catalog | 金标准 账本/srt/words | **秒级** | 每次提交必跑 |
| **T1 单原子·复用金标准视频** | 每个会动视频的原子：喂上游 golden → 比对本原子产出 | 金标准 body/trimmed/final | 分钟级（短 ffmpeg） | 改了某原子 |
| **T2 阶段集成** | 一整环：③裁剪链 / ④字幕链 / ⑤⑥铸造组装 | 阶段入口 golden | 分钟级 | 改了某阶段/配方 |
| **T3 端到端 + 跨线零回归** | 整条 `--run zh_clip_cut` 出片 + **G4 zh_business 零回归** | source + G4 baseline | 重（~3–5 分） | 发版/收口前 |

---

## 四、逐能力回归清单（每个能力测什么、复用哪个金标准、属哪层）

### T0 纯数据（秒级·每次必跑）
| 能力 | 输入（复用） | 断言 | 
|---|---|---|
| `_manifest.remap_time` | 合成 ops | 选段/去静音/变速映射、被剪点返 None、句末夹回（单元用例） |
| `subtitle_align` | golden 账本 + words | 输出 srt == golden `clip.srt`（**文本比对**）、30 条 |
| `subtitle_protect` | 冻结 pre/post 对 + keeplist | 输出 == golden `final_protected.srt`、爱马仕钉回、1:1、无吞字 |
| `subtitles_cli`(make_subtitles) | golden `final.srt` | 输出 `zh.ass` == golden（**字节比对**） |
| `reframe_crop` | source 路径 | `--crop` 出 `crop=894:1588:104:290,scale=1080:1920`；`--detect` 出建议 |
| `selector --list` / `run --plan zh_clip_cut` | — | 文本快照：六环分组、0 待建、源适配/自检门齐 |
| `build_catalog` | 三 capabilities.json | catalog 30 原子、全带 stage、`also_provides` 入索引 |
| `check-tools` | — | 0 error |

### T1 单原子·复用金标准视频（改哪个原子跑哪个）
| 能力 | 输入（复用 golden） | 断言 |
|---|---|---|
| `rough_cut` | spec + source | body 时长 107.766±0.05 + 账本 rough_cut keeps == 期望 |
| `trim_silence` | golden `body` + `vocals` | trimmed 94.495±0.1 + 账本 keeps==期望 + 去静音 13.29s |
| `speed_adapt --fixed` | golden `trimmed` + `vocals_t` | final 78.683±0.05 + 账本 speed factor=1.2 |
| `name_mask --black` | golden `body` + 多 region | 输出尺寸不变、指定块变黑（抽帧像素均值≈0） |
| `subtitle_burn` / `title_bar` / `prepend_hook` / `concat` / `endcard` / `progress_bar` | golden `final`/`钩子` | 输出存在、时长符合（如 prepend = 钩子+0.3+正文）、抽帧有目标元素 |
| `denoise_voice` | golden `body`(原音) | vocals 107.712±0.05 + 与 golden vocals 波形相关>0.99 |
| `align_check` / `len_check` | golden `final` + `srt` | 门A 6/6 落静音、门D 无漂、len +0.000±0.15 |

### T2 阶段集成
| 阶段 | 入口（复用 golden） | 断言 |
|---|---|---|
| ③ 裁剪链（含 denoise） | spec + source | final 78.683 + 账本三 op 齐 + 门A/len PASS |
| ③ 裁剪链（省 demucs） | spec + source + 给现成 vocals | 同上（跳过 demucs 省时） |
| ④ 字幕链 | golden 账本 + words(+LLM) | srt 30 条 → ai_fix 1:1 → protect 钉回/无吞字 |
| ⑤⑥ 铸造组装 | golden `final` + `final.srt` + 钩子 | 药丸烧对、标题烧对、钩子翻页、成片时长结构对、3 帧抽检 |

### T3 端到端 + 零回归
| 测 | 复用 | 断言 |
|---|---|---|
| 整链 `--run zh_clip_cut --job` | source + 全夹具 | 成片产出 + 78.683 + 3 帧对口型 + 门全绿 |
| **G4 zh_business 零回归** | `baseline/_g4_replay` golden | 5/5 页逐像素一致、zh.ass byte-identical、accel 101.729、SSIM≥0.98 |
| 旧配方不破 | — | `--plan` zh_business/landscape/raw_quickcut/simple_concat/chaptered_growth 都审得出 |

---

## 五、分阶段执行节奏（什么时候跑哪层）

1. **改完任意代码 → 跑 T0**（秒级）：纯数据回归 + check-tools + 审链快照。挡住 90% 的低级回归。
2. **改了某个原子 → 跑该原子 T1 + 它所在阶段的 T2**。只动一个原子，不必全量。
3. **改了某阶段/配方/版式 → 跑该阶段 T2**（+ 若动视觉则 T3 的 G4）。
4. **发版 / 收口 → 跑 T3 全量**（端到端 + G4 + demucs + LLM 各一遍）。

口径：**T0 秒级随便跑；T3 重，只在发版前**。日常迭代靠 T0+T1 的"喂金标准"快速回归。

---

## 六、落地：要建的东西（待你确认后我做）

1. **冻结金标准**：建 `var/zh_main/regression/clip_01/{in,golden}/`，从本次 `ws2_verify/ws6_*` curate 拷入；写 tracked `engines/video-compose/regression/expected.json`（期望值小 JSON）。
2. **测试 runner**（按层分文件，复用现有 `engines/video-clip/test_atoms.sh` 风格）：
   - `regression/t0_data.sh`（纯数据·秒级）
   - `regression/t1_atoms.sh`（单原子·喂金标准）
   - `regression/t2_stages.sh`（阶段集成）
   - `regression/t3_e2e_g4.sh`（端到端 + G4）
   - 一个 `run_regression.sh [t0|t1|t2|t3|all]` 总入口，读 `expected.json` 做断言，输出 PASS/FAIL 表。
3. **非确定性断言工具**：时长比对、SSIM、波形相关、hash、srt 文本/条数——封一个小 `assert.py` 给各层共用。
4. **文档**：把"怎么跑回归"加进 `video-skill-architecture.md` 的维护场景表。

## 七、验收（测试套件本身怎么算建好）
- `run_regression.sh t0` 秒级全绿；`all` 一条龙跑出 PASS/FAIL 表。
- 故意改坏一个原子（如 trim 阈值），对应层能**红**（测试有效，不是摆设）。
- 金标准 + expected.json 齐全，换机器按 README 能复现。
- G4 仍在 T3 里把守 zh_business 零回归。

---

## 待你拍板的点
- **夹具就用 clip_01 一条够不够？** 还是再纳入 1–2 条不同形态的源（如另一条更长/带噪更重的）做多样性？clip_01 是录屏裁剪版，覆盖了 crop+mask+demucs+药丸+钩子全链，单条已能覆盖绝大部分原子。
- **LLM/demucs 这种"慢且要钱/要算力"的，放 T3 全量就好，还是也想要一个可跳过的开关？**（默认：T0/T1 不碰它们，用冻结产物；只有 T3 真跑。）
