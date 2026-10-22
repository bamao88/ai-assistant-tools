# 封面质量标准 + 底图管理（生成后必读必做）

生成器只按参数出图，**图好不好要 agent 自己看**。批量/单张跑完后，本文件的三件事是必做项，不是可选。

## 一、什么是一张好封面（质量标准 rubric）

对每张生成的封面，`Read` 图片逐条核：

1. **人脸在视觉中心**：脸大致落在画面上半的视觉重心，水平居中；**头顶留一点白但别太多**（大片空/贴顶都不行），脸不被切、不歪贴一侧。这是最常出问题的一项。
2. **脸和文字不打架**：底部渐变+文字压在下方约 1/4，不盖到脸/下巴；脸和字之间有呼吸感。
3. **字够大、手机不放大能读**：一图一事、两行字。`feedback_cover_diagram_mobile_first` 的手机优先原则。
4. **文字少→字号更大**：字号是宽度驱动的（短句本应自动放大到 132 封顶），但**要目视确认**短句真的顶大了、没有一行小字飘在中间留一堆空。若某条特别短还显小，检查是不是另一行太长把字号压下去了。
5. **底图和这一批别撞**：见第三节。

不达标就调（见第二节），别将就发。

## 二、生成后自检 + 调整流程（闭环，别一次跑完就完）

```
跑生成器 → Read 图判质量 → 按 rubric 逐张判 → 不合格的单张重出 → 再看 → 直到都达标
```

> **看哪张图**：`overview.png` 分辨率低（一排缩略图），**只够扫"底图有没有重复/整体一眼"**；判人脸位置/留白**必须 Read 全分辨率单张**（每个不同底图看一张代表即可，同底图同 lift 脸位一样）。

**最常见的调整：人脸高低（--lift）。** `lift` = **人像整体上移比例，值越大人越往上**。默认 3/16（0.1875），但不同底图取景不同，按规则移完效果不一定好——**结合你实际看到的图调**：

- 脸偏低/贴底、下巴离字太近 → **加大 lift**（如 `--lift 0.25`、`0.28`），把人往上提到视觉中心。
- 脸贴顶/头发被切 → **减小 lift**（如 `--lift 0.125`）。
- 原则：调到**人脸在画面视觉中心、头顶留白适中**为止。
- **⚠️ 例外：脸「太小」不是 lift 能救的。** 若人物取景太远导致脸偏小（哪怕居中），调 lift 只会把人推离中心、更糟——**这种要 `--base` 换一张取景更近的底图**，不是调 lift。

```bash
# 单张按图微调 lift 重出（覆盖 kit 默认）
"$PY" "$GEN" --title "第一行|第二行" --base frame-03 --lift 0.25 --output /abs/cover.png
```

其他调整：字太小/太挤 → 检查标题是否某行过长（换更短的候选标题）；底图取景太远/不合适 → `--base` 换一张。
批量里想让某条固定用某 lift，在 manifest 该 item 加 `"lift": 0.25`。

> 经验值参考（本项目 kit 底图）：室外帧 3/16 合适；室内/人物取景偏高的帧可用 1/8。5/16 通常太高。

## 三、底图轮换纪律 = 账本驱动的生命周期（批量必读）

底图 = 张和固定品牌人像，靠轮换、与内容无关。**多样性门槛 = 表情有别 + 相邻不撞**，不苛求背景/服装不同（背景服装相近没关系，只要表情有差异、相邻不相似）。

挑图不再是无状态取模，而是**账本 `pool_ledger_evc.json` 驱动的 LRU**（kit `lifecycle`）：

- **复用封顶 K=3**（`reuse_cap`）：每张底图最多用 3 次，满 3 次自动**退休**、不再被挑。
- **时间岔开**：在未退休帧里，优先挑**上次排期日期最旧 / 从没用过**的（never-used 最优先）→ 自然跟上次使用岔开。
- **相邻不撞**：批量内相邻永不同帧（`adjacent_collisions` 应 `[]`）。
- **记账 = --record**：一次使用 = 封面写进真实要发布的 item，按其 `publish_date` 记账。**真实发布批量必须带 `--record`**（把 frame→item→publish_date 写回账本）；测试/tmp 不要带（不污染账本）。manifest 每条要带 `publish_date`。
- **账本缺失自动降级**回无状态取模轮换（不会卡死，但失去封顶/岔开）。

批量返回看 `exhausted` / `base_usage` / `warnings`。现状：池 13 张，其中 **frame-01/02/03 已随首批 d2c 用满 3 次退休**、frame-04/05 各 2 次、koubo 的 frame-07..14 全新。

## 四、底图用尽怎么办（登记表 → 抽帧 → 反馈）

**批量报 `exhausted:true`**（未退休帧填不满这批）时，按 lifecycle 顺序：

1. **先看还有没有现成已筛帧可 promote**：`assistant_zh/assets/video_cover_base/`（`INDEX.yaml`）。当前 koubo 批 33 张里**还剩 25 张已筛未用**，直接 promote 进池即可，**不用抽帧**：
   ```
   PY=.../video-clip/.venv/bin/python
   "$PY" .../assets/extract_frames.py promote --source-id 1781174349_koubo \
     --candidate-dir assistant_zh/assets/video_cover_base/1781174349_koubo \
     --files cover_07_绿树_平和.jpg,cover_09_秋树_暖调2.jpg   # 你挑的
   ```
   （promote 会 cp 进 covers/frame-NN + 写账本 source/t。）

2. **要真正的新底图 → 从登记表 `base_videos.yaml` 里 `usable:true && exhausted:false` 的源抽帧**：
   ```
   "$PY" .../assets/extract_frames.py sample --video <path> --start S --end E --every 2.5
   # → 出候选帧 + contact_sheet；你按质量标准6条筛(见 kit extraction.quality_gate)
   # → 逐张自渲染封面 Read 复核 → promote --files 过关的(数量不封顶)
   ```
   抽完把这段时间窗并进该源的 `mined_ranges`（Edit base_videos.yaml），全轴覆盖/挑不出好帧就 `exhausted:true`。

3. **⚠️ 现状（2026-07-03 实测）：登记表里没有可抽的干净口播原片**——koubo 已榨干，`20260613` 是框架成片(叠PPT/人像小窗/烧字)`usable:false`。所以**除了 promote 剩余 koubo，眼下没有新源可抽**。

4. **没现成帧、也没可抽源 → 停下反馈用户**：「所有底图用满 3 次、koubo 剩余帧也用完、登记表里没有可抽的干净口播原片了，请提供新的张和口播原片（像 koubo 那种自拍全屏竖版口播）。」别硬凑重复底图发出。

> `video_cover_base/`=已筛候选人像库（promote 来源）；`covers/`=实际轮换池；`base_videos.yaml`=可抽的原片登记（用户维护，贴本地路径）；`pool_ledger_evc.json`=池使用账本（AI 维护，gitignored）。质量标准6条见 §一 + kit `extraction.quality_gate`。
