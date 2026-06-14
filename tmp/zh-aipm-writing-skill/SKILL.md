---
name: zh-aipm-writing-skill
description: |
  AI PM 超级小助理（副号）所有写作任务的统一入口——知识学习笔记、概念拆解、一手源整合解读、同学答疑、求职/转型判断、热点翻译都走这里。
  副号 ≠ 主号：不用张和第一人称，用课代表/助教视角；不做 takeaway / 应用上升；目标是"读者读完能复述这件事是什么"，不是"读者读完知道下次该做什么"。
  skill 内置 6 个写作参考维度（想清楚 / skeleton / draft / 配图 / 独立审稿 / humanizer 检测）+ 一组风格硬约束 + 风格参考样本。维度是参考视角不是强制流程——每篇文章的实际路径会不一样，最终标准是文章质量，不是流程是否走完。
  用户提到"写""起稿""改稿""推文""解读""复盘""教材""文章""博客""公众号"等动作 + 账号是副号时，触发本 skill；主号不走 skill，由 AI 直接撰写（zh-writing-skill 已弃用）。
compatibility: claude-code
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
  - WebSearch
  - WebFetch
  - mcp__fetch__fetch_markdown
  - AskUserQuestion
---

# zh-aipm-writing-skill

副号「AI PM 超级小助理 / 毛毛还在打工」所有内容文章的写作入口。

**核心定位**：课代表/助教视角的知识学习笔记。读者读完能复述"这件事是什么"，不需要知道"下次怎么做"。

主号（和哥AI产品丨智能问问，张和第一人称）的写作由 AI 直接撰写（`zh-writing-skill` 已弃用，移到 `tools/tmp`），本 skill 不处理。

---

## 这个 skill 怎么用

skill 里写的所有内容都是过去写作踩坑总结出来的经验，**是参考素材库，不是 SOP**。当前这套维度不一定能保证写出好文章，最终标准是文章本身。

实际写作时：

- 6 个维度按需选用，不强求按顺序走完，也不强求每个都用到
- 反复返修 / AI 味重 / 读者反馈不清楚等情况下，回来翻对应维度
- "风格硬约束"那段相对稳定（破折号、takeaway、套路化开头这些必砍）
- "维度"和"风格参考"会持续迭代——每次写完新文章，发现的新写作病或工作流问题继续追加

不要因为"6 个维度都走了"就认为文章已经够好。也不要因为某些维度跳过了就认为流程不完整。**唯一的检验是定稿后文章读起来质量如何。**

---

## 账号定位

| 维度 | 副号 |
|---|---|
| 发布平台 | 公众号首发，小红书同步 |
| 写作视角 | 课代表/助教，不是张和本人 |
| 内容主流类型 | 知识学习笔记、概念拆解、一手源整合、同学答疑 |
| 长度 | 1500-3000 字（公众号），不强求短 |
| 读者画像 | 对 AI 产品有兴趣、看过一些 AI 概念文章、用过 ChatGPT/Cursor，想搞懂某个反复看到的术语或概念 |
| 不做的事 | takeaway / 应用上升 / 教读者怎么做 / 张和第一人称 / 张和本人专属经历 |

**典型内容形态**（按写作难度排）：

- **知识学习笔记**：把一个概念讲清楚（"Harness 是什么"、"function calling 与 Harness 的边界"）
- **概念拆解**：把一组相关概念区分清楚（"Agent / Harness / Scaffold / Tool Use 的关系"）
- **一手源整合解读**：把几个员工推特/官方博客/播客整合成一篇（"Cursor 团队怎么讲他们的 Harness 设计"）
- **同学答疑**：群里反复出现的问题整理（"为什么 Claude Code 看起来比 Cursor 慢"）
- **热点翻译**：行业新闻翻译成"对 AI PM 意味着什么"（但不上升到 takeaway）
- **求职/转型判断**：基于公开信号给方向判断（"2026 年想转 AI PM 该补什么"）

---

## 写作过程中可以参考的 6 个维度

**这 6 个维度不是强制流程模板。** 每篇文章的实际写作路径会不一样——有些维度可以跳过、合并、反复迭代或者完全不用。最终标准是**文章质量本身**，不是这 6 个维度是否都走完。

它们是过去写作踩坑总结出的视角。遇到对应的问题（"方向反复返修" / "图越生成越浪费时间" / "写完读起来像综述" / "AI 味太重"）时，可以来翻翻对应维度下的具体规则。

按写作时间顺序大致排列，但不强求线性。

### 维度 1: 想清楚（方向不稳时回到这里）

**适用时机**：写之前方向不清楚 / 写到一半发现跑偏 / 反复返修浪费时间

回答 4 个问题：

1. **这一篇要交付什么** —— 不是"图怎么排"或"用什么素材"，是"读者读完能复述什么"
2. **宽 vs 窄** —— 一篇讲透一个概念（窄）还是讲清楚一组概念关系（宽）？默认窄
3. **深浅** —— 入门级（读者完全没听过这个词）还是进阶级（读者听过但说不清）？多数副号文章是后者
4. **讲法** —— 概念层层展开？时间脉络？case 驱动？

不一定要正式写一段 100 字"写作意图描述"。但如果发现写不下去或者跑偏，停下来问这 4 个问题通常能找回方向。

### 维度 2: skeleton（结构稳定前可以反复改）

**适用时机**：写正文前 / 写到一半结构混乱时

skeleton.md 应该包含：

- 主标题候选（2-3 个）
- 章节顺序（按"概念层层展开"的逻辑组织）
- 每章节一句话讲什么（不展开正文）
- 长度目标（每节大致字数）
- 风格 reference（参考样本 + 风格 DNA，见下文 #风格参考）
- 写作硬约束（参考 #风格硬约束）

#### "概念层层展开"是什么意思

把概念按"由浅到深 / 由位置到内部 / 由是什么到为什么"的顺序展开。例如 Harness 笔记的层：

1. **定义层** —— Harness 字面是什么 + 在 AI 里是什么 + 它在概念家族里的位置
2. **边界层** —— 模型不做什么 / function calling 不做什么 → 这些才是 Harness 在做
3. **机制层** —— 一轮 loop 里 Harness 具体做什么
4. **深度层** —— Harness 的真正功夫在哪（错误处理）
5. **具象层** —— 拿真实产品（Cursor vs Claude Code）看不同 Harness 设计
6. **历史层** —— 为什么这个词最近才出现
7. **收口** —— 一个判断收尾（不是 takeaway）

不要把"相邻概念"堆在文末单独一节——那样太僵硬。把相邻概念散布到正文，在概念展开到自然需要区分的位置出现。

### 维度 3: draft 写作

#### 三条值得守的原则

1. **作者主线为骨，引用是辅助** —— 用作者自己的话讲清楚一件事，引用只在"这话不是我说的、是 X 说的"的硬支撑节点出现。2000 字的笔记，引用通常 ≤5 个。超过 8 个就是"金句串烧"，回头精简。
2. **引用化入叙事** —— 公众号文体下，正文挂链接读起来像综述。**正文 0 hyperlink**，引用化入叙事。**发布版不保留「## 参考资料」段**（张和明确要求，所有发布都删掉这一段；草稿里可临时留作核对，推送前删）。
3. **找不到一手源的具象 claim 直接砍** —— 凭印象 / "听说" / "我体验过" 都不算源。详见 [`feedback-zh-examples-must-have-source`](memory)。

#### 每段必有

- **硬判断（加粗）** —— 段落末或开头给一句明确的作者判断，不和稀泥。例如"模型本质上是一个纯函数"、"两个 Harness 在 happy path 上写法可能差不多，真正拉开差距的是异常路径"。
- **翻译层** —— 抽象概念后立刻配一句"这在产品里长什么样"。用第三人称客观陈述（"在 Cursor 里改 bug，看上去 Cursor 已经知道代码库"），**不用二人称对话感**（不写"你打开 X" / "你会发现"）。

#### 一手源的来源（优先级从高到低）

| 源类型 | 优先级 |
|---|---|
| 员工推特 / 公开发言（创始人、PM、工程师本人） | 一级 |
| 官方工程博客 / 官方文档原话 | 一级 |
| 播客 / YouTube 访谈片段（带时间戳） | 一级 |
| GitHub 代码 / commit / Issue 讨论 | 一级 |
| HN / Reddit 高赞拆解贴 | 二级 |
| Simon Willison / Hamel Husain 等公认实战派的第三方博客 | 二级 |
| 凭印象 / "听说" / "我体验过" | **禁止** |

写到具象 claim 但找不到源时：**砍掉**，不要硬撑。宁可少说一点。

### 维度 4: 配图（按判断标准来，不要凑）

**所有图直接用代码内嵌写在 draft.md 里**（mermaid / markdown 表格 / ASCII），**不生成独立的 HTML / PNG / excalidraw 文件**。详见 [`feedback-draft-visual-assets-late`](memory)。

判断要不要配图，按 [`feedback-when-to-use-diagrams`](memory)：

**✅ 真正需要图的情况**：
- 多元素 + 多种关系（包含 / 平级 / 协议 / 依赖）→ mermaid graph
- 循环 + 决策分支 → mermaid flowchart
- 3+ 对象 × 3+ 维度对比 → 优先 mermaid graph 用 subgraph 纵向并列（不要表格——手机竖屏看表格容易溢出）
- 时序交互（多方消息往返）→ mermaid sequenceDiagram

**❌ 不需要配图（看到这些立即停）**：
- 一维分类 / 单一轴 → 一句话能讲完，不要画 ASCII 轴
- 线性序列 / 时间线 → 文字按时间叙述就清晰，不要画 timeline
- 1-2 个事物的简单对比 → 一句话讲完
- 已经在文字里完整讲过的概念 → 配图就是冗余
- 流程只有 3 步以内、无分支、无循环 → 文字够

**草稿阶段禁止行为**：
- ❌ 生成独立的 `.html` 文件
- ❌ 跑 excalidraw + chromium 渲染 PNG
- ❌ 跑 markdown-to-cards 生成小红书卡片
- ❌ 写 `![image](xxx.png)` 引用一个还不存在的 PNG 文件

定稿后（用户说"可以发了 / 出物料了 / 开始排版"）才转最终物料。**配图出图默认走 `diagram-design` skill**（已装在 `~/.claude/skills/diagram-design`），不再用 mermaid.ink / excalidraw：

1. 把 draft.md 里的 mermaid 逻辑源翻成 diagram-design 的独立 HTML（内联 SVG），每张存 `diagram_N.html`。核心是它那套"反 AI 味"设计系统：**扁平无阴影 + 1px 发丝描边 + 每图只 1 个 coral 焦点 + 小圆角(≤8px) + 所有坐标/字号卡 4px 栅格**。
2. 中文配字体：标题 `'Instrument Serif','Songti SC'`，正文/节点 `'Geist','PingFang SC'`，技术标签 `'Geist Mono'`；字号在 skill 原生 12px 基础上整体放大以适配公众号手机端（仍卡 4px 栅格）。文字密度大的对比图用 HTML 网格、其余用内联 SVG，token 保持一致。
3. puppeteer 截图成 PNG：`node render.js diagram_N.html diagram_N.png`（deviceScaleFactor 2）。
4. 参考实现：`content/personas/zh_assistant/items/ZHC20260526_152214_001/`（diagram_1/2/3.html + render.js，2026-06-01 三图重做的样板）。详见 [[reference-diagram-design-skill]]。

### 维度 5: 独立审稿（推荐用 clean sub-agent）

**适用时机**：草稿基本稳定时；自己读了几遍但不确定还有什么问题时

按 [`feedback-use-clean-subagent-for-review`](memory)：派一个完全没有当前上下文的 sub-agent 通读 draft，可以避免主上下文偏见（主对话里反复改过的稿，主 agent 容易自我感觉良好）。

sub-agent prompt 的关键要素：

- 给读者画像（不是技术人员，但能读懂 JSON / grep）
- 给 draft 路径 + skeleton 路径
- 让它**先做纯读者反应**（逐段标记困惑、想问但作者没回答、跳过了关键一步、重复、未解释术语）
- 再做整体性诊断（7 项：能不能复述 X / 关键疑问 / 逻辑链断裂 / 概念边界 / 历史脉络 / 结构权重 / 例子是否服务于讲清楚）
- **只做诊断，不给修改建议**，把"该怎么改"留给作者决定

### 维度 6: humanizer 检测（定稿前过一遍）

**适用时机**：内容、结构、事实都稳定后；准备交付前

调 [`humanizer`](skill) 做 final pass，按 `~/.claude/skills/humanizer/ai-smell-cases.md` 的检测清单（13+ 条）逐项扫。最常踩的：

- 评价上面内容（"图上画得很干净"）
- 预告型引导（"三件事最值得记"）
- 揭晓型互动（"这件事背后的真实信号是"）
- 行动建议（"下次你看到 X 先别问 Y 问 Z"）
- 二人称对话感（"你打开 X" / "你在 Y 里"）
- 强调装腔（"讲得很死" / "钉到了墙上"）

每次写作发现的新 AI 味 case 都要追加到 `~/.claude/skills/humanizer/ai-smell-cases.md`，详见 [`feedback-humanizer-skill-iteration`](memory)。

---

## 风格硬约束（相对稳定，遇到时优先守）

这些是用户反复纠正过的硬底线，违反基本上一定会被打回。共享 [`feedback-zh-writing-style`](memory)：

- 禁止"——"全角破折号
- 禁止套路化场景开头（"班上同学反复问"、"最近有人在问"、"很多人第一次看到 X 会以为是 Y"）
- 禁止 takeaway / 应用上升段（"AI PM 能用这个概念做什么"、"评估 AI 产品时多问一句"）
- 禁止张和第一人称 + 张和本人专属经历（"我在小米..."、"我创业..."、"我带的学员..."）
- **副号里提到张和一律用敬称「张和老师」**（课代表/助教视角，不直呼"张和"）。引用其方法论写"张和老师在课程里讲过/张和老师给的框架"
- 禁止扮演引导者（不预告 / 不揭晓 / 不行动建议 / 不二人称对话感）
- 段间过渡用一句话引导，不靠加粗小标题硬切段
- **公众号正文不放微信二维码**（张和 2026-06-04 纠正，推翻早前"固定页脚加二维码"的说法）：二维码放进**飞书资料包/模板文档**里（文末一句"扫码加小助理微信" + 二维码图，用 `lark-cli docs +media-insert --align center`），不放在公众号文章。配套资料包用飞书链接**开放直给**，公众号不要做成"扫码/加好友才给本资料"。
- **配套资料包在文末自然带出，不做成独立大标题段**（张和 2026-06-04）：不要 `## 配套资料包` 这种单独单元，融进"写在最后"末尾一句话；**链接放在截图前面**（先给链接、再放文档截图）；截图要截**资料/模板文档正文本身**，别截目录/索引页；资料包描述一句话带过，别讲太复杂。
- **概览型配图前置**：讲"比传统多 N 块"这类全局结构图，放正文最前面（H1 之后、引言之前）当钩子，不要塞在中段。
- **框架/解读/对标类要客观完整，不要把单一亮点当成全部**：哪怕某个点（如"评测"）很有料，它通常只是完整框架里的一块，其他部分（架构、选型、边界、兜底…）也要客观铺全；立场是"真正的 X 就该这么写"，**不是"对标错了、我们才对"的打脸姿态**。差异化靠"完整+扎实+融入张和方法论"，不靠贬低对标。（2026-06 AI PRD 选题踩坑：初版把"AI PRD 核心=定义评测"写得过激进 + 带对立姿态，被纠正）

副号常用叙事切口：

- 「从 AI 产品经理的视角看……」
- 「我把这件事整理了一版……」
- 「最近在弄清楚 X 是什么……」

---

## 风格参考

### 主参考样本（必读，每次写副号前抽 5 分钟看一遍）

- **张和《长上下文工程：AI产品经理的新战场》** —— 飞书 wiki: https://li4p2wlpvm5.feishu.cn/wiki/Y6ShwIACiiVE36kjmw5chIhqn9c
  虽然挂在张和主号，但是副号知识笔记类的核心风格 reference。提取的 DNA：
  - 引用化入叙事，正文 0 hyperlink
  - 第一人称硬判断（"我把见过的长上下文问题归纳为四类"、"我的答案是"）
  - 加粗只用于核心论点不是关键词
  - 每讲完一段抽象概念立刻给"在产品里长什么样"
  - 结尾给作者的判断/总结，不给读者下行动指令

### 副号典型样本

- **Harness 笔记**：`content/personas/zh_assistant/items/ZHC20260526_152214_001/draft.md`
  副号知识学习笔记的工程化典型。包含：概念层层展开、相邻概念散布、3 张必要 mermaid 图、无 hyperlink 正文、独立审稿后定稿。

---

## 触发与边界

### 触发本 skill

- 用户说"给副号写 X" / "写知识笔记 X" / "把 X 概念讲清楚" 等
- content-ops 工作态下 `account: 副号` 的写作任务
- 用户说"写文章" 但目标账号已经确认是副号

### 不触发本 skill

- 主号写作 → 不走 skill，由 AI 直接撰写（`zh-writing-skill` 已弃用）
- 私域话术 / 朋友圈 / 群发 → `private-ops` 工作流
- 活动宣传 / 嘉宾介绍 / 招生 / 通知公告 / 致歉 → 不进 skill，按 content-ops.md 的运营事务文规则自己写

### 与其他 skill / workflow 的关系

| 关联 | 关系 |
|---|---|
| `workflow/content-ops.md` | 上层路由。决定是否进入写作 + 确认账号 + 创建 item 后调本 skill |
| ~~`zh-writing-skill`~~ | 已弃用（移到 tools/tmp）；主号正文改由 AI 直接撰写 |
| `humanizer` | 下游 skill，Phase 6 AI 味检测 |
| `zh-final-polish` | 替代 humanizer 的备选（更聚焦 ZH 语气），用户明确要求时调 |
| `zh-topic-mine` / `zh-topic-review` | 上游 skill，candidate 阶段 |

---

## 相关 memory（按需翻）

遇到下面这些情况时，对应 memory 是最快的参考：

- ⚠️ [`feedback-draft-visual-assets-late`](file:///Users/xpw/.claude/projects/-Volumes-ExtSSD2601-AI-Assistant-assistant-zh/memory/feedback_draft_visual_assets_late.md) — 草稿阶段图必须代码内嵌写在 md
- ⚠️ [`feedback-when-to-use-diagrams`](file:///Users/xpw/.claude/projects/-Volumes-ExtSSD2601-AI-Assistant-assistant-zh/memory/feedback_when_to_use_diagrams.md) — 配图判断标准 + 表格非必要不用
- [`feedback-zh-writing-style`](file:///Users/xpw/.claude/projects/-Volumes-ExtSSD2601-AI-Assistant-assistant-zh/memory/feedback_zh_writing_style.md) — 风格硬约束 + 不扮演引导者
- [`feedback-zh-examples-must-have-source`](file:///Users/xpw/.claude/projects/-Volumes-ExtSSD2601-AI-Assistant-assistant-zh/memory/feedback_zh_examples_must_have_source.md) — 举例必须有可追溯一手源
- [`feedback-use-clean-subagent-for-review`](file:///Users/xpw/.claude/projects/-Volumes-ExtSSD2601-AI-Assistant-assistant-zh/memory/feedback_use_clean_subagent_for_review.md) — 写完用 clean sub-agent 独立审稿
- [`feedback-humanizer-skill-iteration`](file:///Users/xpw/.claude/projects/-Volumes-ExtSSD2601-AI-Assistant-assistant-zh/memory/feedback_humanizer_skill_iteration.md) — 写作完发现的 AI 味追加到 humanizer case 库
- [`feedback-writing-process`](file:///Users/xpw/.claude/projects/-Volumes-ExtSSD2601-AI-Assistant-assistant-zh/memory/feedback_writing_process.md) — 写文章必须先想清楚再写

---

## 迭代说明

本 skill 是 2026-05-31 基于 Harness 笔记（ZHC20260526_152214_001）的写作经验沉淀的 v1。每次写作如果发现新的写作病/工作流问题，按这个顺序处理：

1. 如果是 AI 味问题 → 追加到 `~/.claude/skills/humanizer/ai-smell-cases.md`
2. 如果是工作流问题（配图、表格、引用、审稿等） → 追加到相关 memory（或本 skill 对应 Phase）
3. 如果是副号定位/类型问题 → 直接更新本 SKILL.md

不要让本 skill 变成只读文档。它必须吸收每次写作的真实暴露才能持续有用。
