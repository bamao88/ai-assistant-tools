---
title: "Google 实测：一份几页纸的 Skill 把模型准确率从 28% 拉到 96%"
abstract: |
  Google DeepMind 出了一份只有几页纸的 gemini-api-dev skill：解释 API feature、列当前 SDK、给 sample code、指向官方文档。

  就这么个 cheatsheet，把 gemini-3.1-pro-preview 在 117 道编码题上的成功率从 28.2% 拉到 96.6%。

  但同一份 skill 装到老一代 2.5 系列模型上几乎没用。Google 自己的解读是：skill 需要强 reasoning 才能用得起来。

  几乎同一时间，Vercel 拿出反方数据：在他们的 Next.js 评测里，AGENTS.md 跑出 100%，skill 默认配置下连基线都打不过。

  两套数据加在一起，是 agent skill 这条路最近最值得看的一次双向验证。
keywords:
  - AI产品经理
  - Claude Code
  - agent skill
  - Gemini
  - AGENTS.md
  - 上下文工程
  - Vercel
  - Google DeepMind
  - reasoning
  - SDK
---

# Google 实测：一份几页纸的 Skill 把模型准确率从 28% 拉到 96%

你有没有遇到过这种事：让 Claude Code 或 Cursor 写一段调用某个最新 SDK 的代码，它一本正经地写出来，跑不通，回头一看，是它在用半年前已经被废弃的 API。第一反应是模型太笨。但模型并没有笨——它训练完那一刻，世界停在那一刻，外面 SDK 一直在动，它不知道。

这个"知识断层"不是某个模型的问题，是所有大模型的结构性缺陷。最近一个月，Google DeepMind 和 Vercel 几乎同时拿出了两套针对这个问题的实测数据，结论指向同一个方向，但路线分歧很大。这篇就把这两套数据拆开摆给你看。

Philipp Schmid 和 Mark McDonald 是 Google DeepMind 的 Developer Relations Engineer，3 月 25 日他们在 Google Developers Blog 上发了一篇《Closing the knowledge gap with agent skills》，公开了 Gemini API skill 的设计和评测数据。Vercel 这边的对照样本来自 Jude Gao（Next.js 团队工程师）1 月 27 日发的《AGENTS.md outperforms skills in our agent evals》。一边是 SDK 厂自己出 skill 给自己模型用，一边是框架厂在客户端 agent 上跑横向对比。两套实验都很硬，但结论几乎完全相反。

**Google 这份 skill 简单到让人怀疑它能干什么**

把 Google 出的 `gemini-api-dev` skill 打开看，会发现它没什么"机制"可言——就是一份给模型读的 cheatsheet。

- 解释 Gemini API 有哪些高层 feature
- 列出当前每种语言的 SDK 和对应模型
- 给每个 SDK 配几段基本 sample code
- 把官方文档的入口地址列出来，作为 source of truth

Philipp 在博客里自己点破了这件事的本质："This is a basic set of primitive instructions that guide an agent towards using our latest models and SDKs, but importantly also refers to the documentation to encourage retrieving fresh information from the source of truth."

skill 之外，他们只额外给了模型两个工具：`activate_skill`（激活这份 skill）和 `fetch_url`（去把文档原文拉下来读）。系统提示词直接复用了 Gemini CLI 现成的 prompt snippets。整个机制能在一张纸上画完。

这件事第一眼看上去很怪——模型训练数据里本来就有海量 Gemini 相关代码，再灌一份简介能多多少？数据出来之后，问题的提法就变了：不是"模型不知道"，而是"模型知道的东西已经过时了"。一个不会的模型，灌进去就学到；一个学错了又自信的模型，你不告诉它"现在不用这个了"，它会一直用错的方式自信地往下写。Skill 在这里的角色，是把模型脑子里那批过期记忆压下去，让它走当下版本的路径。

**真正反直觉的发现：聪明模型加 skill 暴涨，笨模型加几乎没用**

这是博客里最值得拆的一组数据，因为它颠覆了"越笨的模型越需要外部知识"的直觉。

- gemini-3.1-pro-preview 在 117 题上的 vanilla 成功率是 28.2%，加 skill 之后 96.6%，整整 +68.4 个百分点
- 3.0 Pro 和 Flash 的 vanilla 基线只有 6.8%，加 skill 后虽然有提升，但远不如 3.1
- Gemini 2.5 老系列模型加同一份 skill，提升非常有限
- Philipp 在博客里的原话："Using modern models with strong reasoning support makes a difference"

按直觉，模型越笨越需要 cheatsheet。但实际数据反过来。Google 给的解读其实抓到了关键：skill 看着是"一份知识"，本质上是"一份指令"——这里有最新的 SDK，那里有文档地址，写代码的时候记得去查。要执行这份指令，模型需要做一连串判断：什么时候该激活 skill？写到第几行该 fetch 文档？fetch 回来的内容跟我训练里记得的冲突了，我信哪个？这一连串判断都是 reasoning 的活。笨模型不是不会读这份 skill，是不会用——读完了，下一秒还是按训练里的旧记忆往下写，没有那个"等一下，我应该先去查"的反思动作。

换个说法：**skill 是外部知识，reasoning 是用知识的能力，两者缺一不可。** 一个没有 reasoning 的模型给再多 skill 也吃不进去；一个有 reasoning 但没 skill 的模型，本事再大也突破不了知识截止日期那道墙。

**Vercel 用 Next.js 16 跑了同样的对照实验，结论几乎相反**

如果只看 Google 这一份数据，你会以为 skill 是清晰的赢家。Vercel 的实验把这个判断打了个对折。

Jude Gao 在博客里直接给出了所有四组配置的对照成绩：

- Baseline（不给文档）：53%
- Skill 默认行为：53%（相对基线 +0 点）
- Skill + 在 AGENTS.md 里加显式调用指令："Before writing code, first explore the project structure, then invoke the nextjs-doc skill for documentation"：79%（+26 点）
- 直接在 AGENTS.md 里嵌入一份压缩到 8KB 的文档索引：100%（+47 点）
- 关键观察：56% 的评测场景里，skill 根本没被 agent 主动调用

Jude 在文章里给了一个让人警觉的细节：默认配置下 skill 不仅没正向作用，在某些指标上还略低于基线（test 通过率 58% vs 63%），他的解释是"an unused skill in the environment may introduce noise or distraction"——一个挂在那儿不被用的 skill，反而会变成干扰源。

更微妙的是指令措辞的脆弱性。同一份 skill、同一份文档，Vercel 测出来两种措辞的差距巨大：

- "You MUST invoke the skill"——agent 先读文档，被文档里的写法锚住，反而漏掉了项目本身的上下文
- "Explore project first, then invoke skill"——agent 先建立项目心智模型，再把文档当参考查，结果更好

Vercel 给出的核心命题是："Prefer retrieval-led reasoning over pre-training-led reasoning"——把这句话直接嵌进 AGENTS.md 的索引段，agent 才会真正去查文档而不是凭记忆。他们最终的判断是：与其多绕一层让模型决定"要不要激活某个 skill"，不如直接把核心指令塞进每次都会被读的默认上下文里，反而更稳。

**两套数据放在一起看，路线分歧的本质是什么**

把 Google 和 Vercel 的两组数据并排摆，会发现它们并不真的矛盾，反而是同一个机制的两面。

- Google 测的是同质场景（自家 SDK + 自家模型 + 主动配置激活 skill 的 system prompt），所以 skill 路径跑得动
- Vercel 测的是异质场景（第三方框架 + 通用 agent + 默认行为不显式触发 skill），所以默认 skill 路径几乎不工作
- Google 数据里也承认了 Vercel 的发现："we know from Vercel's work that direct instruction through AGENTS.md can be more effective than using skills"
- 两边都同意一件事：决定 skill 能不能起作用的，不是 skill 本身，而是"模型有没有 reasoning 在合适的时机去调用它"
- 两边也都同意：agent 默认不会很聪明地知道"现在该激活某个 skill"

这两份实验其实代表了两种工程哲学的对峙。AGENTS.md 追求的是**确定性**——每次都读、不靠模型判断；skill 追求的是**可组合性**——你可以装一堆 skill，模型按需取用，不浪费上下文。简单场景下 AGENTS.md 够了，约定俗成、所有 agent 都读得到、零认知成本。复杂场景下 skill 的可组合性会发挥价值——你不可能把所有可能的场景都塞进同一份 AGENTS.md，那样上下文会爆。

但有一个共同结论必须记住：**任何依赖"模型决定要不要激活我"的 skill，一旦模型没判断对，就是白做。** 这就是为什么 Google 那份实验里专门给模型配了"激活 skill"的 system prompt，否则连激活这一步都未必能稳定触发；Vercel 拿掉这个 prompt，56% 的场景里 skill 直接被无视。两边数据放一起，得出的是同一个铁律——skill 的可调用性，远比 skill 的内容质量更脆弱。

**Skill 真正的坑是更新机制，不是设计本身**

Google 这篇博客末尾还留了一段让我反复看了几遍的话。Philipp 自己提了一个非常关键的隐患："Skill simplicity is a huge benefit, but right now there isn't a great skill update story, other than requiring users to update manually. In the long term this could leave old skill information in user's workspaces, doing more harm than good."

把这句话翻成大白话就是：

- skill 装进用户工作区之后，SDK 升级、文档更新、最佳实践变了，怎么把新版本同步过去？
- 目前的方案就是手动重装
- 这意味着用户工作区里很可能装着一份已经过时的 skill——它本来是用来解决"模型知识过期"的问题，结果它自己也过期了
- 一份过时的 skill 比没有 skill 更危险，因为模型会信任它："看，这是我的官方知识"

skill 和 agent 这套基础设施现在最缺的不是新 feature，是**版本管理**和**信任链路**。每一份 skill 应该有版本号、有发布时间、有自动检测过期的机制。当 skill 自己过期了，它应该主动告诉模型："我的内容已经超过 3 个月没更新了，请优先去原文档查"。这听起来像是非常基础的工程实践，但目前没有任何 skill 仓库系统化做这件事。可以预见接下来两三年 agent skill 生态会经历一次跟 npm 早期一样的痛——大量过时包、依赖冲突、版本错位。区别是，npm 里一份过时代码至少不会伪装成正确，agent skill 里一份过时知识却能让你的 agent 自信地按错的方向跑半天。

**Skill 的本质是经验翻译，不是 prompt 合集**

把 Google 和 Vercel 的数据放在一起再看一遍，会发现它们都在用各自的方式回答同一个问题：什么样的 skill 才真正配叫 skill？

- Google 的 skill 之所以能起作用，是因为它给的是 SDK 厂自己最权威的版本信息 + 文档入口，而不是泛泛的"使用建议"
- Vercel 的 AGENTS.md 之所以能跑到 100%，是因为它给的是"version-matched documentation"——按项目当前 Next.js 版本精准匹配的文档索引
- 两边真正生效的内容形态都不是 prompt 模板，是**结构化的、可溯源的、贴版本的指令**
- 反过来，市面上大量 skill 还停留在"把几段提示词打包发出来"的阶段，既没有工具配合，也没有权限边界，更没有版本管理

我前段时间在训练营里跟学员讲过一个判断标准：**好的 skill 来源就两种——要么是业务专家手把手教，要么是把行业专业书籍里的方法论灌进去。** 同时它必须搭配相应的工具和权限，本质是"代表你把你的经验翻译成引导模型的话，让它知道在什么场景下用什么工具、怎么干、注意事项是什么"。如果你的 skill 既不是这两种来源，又没有工具和权限的搭配——那它就是一份漂亮的废话，模型读不读都一样。

Google 这次的 skill 之所以能让 gemini-3.1 暴涨 68 个点，不是因为他们写了多花哨的 prompt，是因为他们把"当前哪些 SDK 是活的、文档在哪、sample code 长什么样"这些**只有 SDK 维护者自己最清楚的事实**结构化地放进去了。这是别人替代不了的位置。

**我的思考：CC + Skill 已经是新基线，做不过它就该重做架构**

把这两份数据合起来看，对做 AI 产品的人来说，最该被记住的不是某条结论，而是这条参照线本身。

一个非工程出身的人，给 Claude Code 装一份合适的 skill，做出来的 agent 行为能把通用模型的成功率从 28% 拉到 96%——这件事的真实意味是：**Claude Code + 通用 Skill 已经成为新的产品基线**。如果你做的细分 agent 干不过这个基线，你就要回头审视一下你的架构是不是已经落后于 agent 时代了。

正常情况下，跟 Claude Code 同级架构的细分 agent，加上你领域的专业 skill，理论上应该能超过 Claude Code 加一个**通用**skill——因为你的 skill 更贴你的场景。如果你做不过，三种可能：要么你的架构里有冗余的子 agent 拆分（上下文被切成几段，每段都看不到全貌），要么有过度的工作流编排（agent 变成执行流水线上的一颗螺丝，失去了 reasoning 的余地），要么是你的 skill 本身就没有好好沉淀经验——还停留在"prompt 合集"阶段。

而 Vercel 那一面的数据是另一种提醒：哪怕你 skill 做得再好，如果 agent 在合适的时机不会调用它，那 skill 等于不存在。所以做产品的人不能只盯着 skill 内容质量，还得盯着 agent 是不是真的会用它——这就回到了"模型 reasoning 强不强"和"默认上下文里有没有显式触发指令"这两件事。Google 用 system prompt 显式触发，Vercel 干脆把指令前置到 AGENTS.md。两种解法形态不同，本质都是不让 skill 的命运挂在模型一念之间。

回到最初那个数字：28.2% → 96.6%。这不是"AI 变聪明了"，是"AI 拿到了自己一直缺的那块东西"。那块东西叫上下文。每一个做产品、做工程、做培训的人，能给 AI 的最有价值的礼物，就是把你这个行业、你这个公司、你这个项目的上下文，结构化地交给它——并且想清楚，是该让它每次都读到，还是该让它在某个时机主动来取。

也欢迎大家留言讨论你怎么看 skill 和 AGENTS.md 这两条路线。

（本文织入了 topic-agent-cc-plus-skill-benchmark、exp-skill-development-core 两条张和知识库判断。）
