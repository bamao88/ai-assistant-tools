# Google 说 Skill 让模型涨 68 个点，Vercel 说 Skill 连基线都打不过，两家都没说错

Google DeepMind 3 月底发了一篇博客，给 gemini-3.1-pro 加了一个几页纸的 Skill，117 道编码题成功率从 28.2% 跳到 96.6%，整整 68.4 个百分点。

Vercel 一月底先发过另一篇博客，结论几乎完全相反：在 Next.js 16 的评测里，同样是给 Agent 喂 Skill，默认配置下成功率从 53% 涨到 53%，一个点没动；换成把同一份文档压成 8KB 塞进 `AGENTS.md`，直接干到 100%。

两边都是公开的评测数据，两边都没造假。把这两篇放在一起读，才能看出 2026 年这一波 Skill 热里真正发生的事，不是"Skill 有没有用"，而是"Skill 在什么前提下有用、在什么场景下会被自己的设计绊倒"。

**来源交代**

Philipp Schmid 和 Mark McDonald 是 Google DeepMind 的两个 Developer Relations 工程师，Philipp 在 X 上是 `_philschmid`，做 HuggingFace 那段时间就以"把模型的事讲清楚"出名。这次他们替 DeepMind 出面回应了一个外面问了很久的问题：作为模型厂自己，看 Skill 这条路怎么样？文章 3 月 25 日发在 Google Developers Blog 上，配套的 `gemini-api-dev` Skill 已经开源在 `google-gemini/gemini-skills` 仓库里。

Jude Gao 是 Next.js 团队的工程师，文章发在 Vercel 官方博客，时间是 1 月 27 日，比 Google 那篇早差不多两个月。Google 在自己博客的结尾点名引用了 Vercel 这篇，承认对方测出来 `AGENTS.md` 比 Skill 强，并说自己也在探索别的方式（比如直接走 MCP 拿文档）。两家观点对立，但彼此读过对方。

两篇文章值得放在一起读，是因为它们一起把"Skill 这个抽象到底解决了什么、还没解决什么"摆得很清楚，分别从模型厂和框架方两个完全不同的位置。

**Google 这边：把"我是谁、用哪个 SDK"做成一份 Skill，3.1-pro 直接打满**

Google 这篇的核心动作不复杂。他们做了一个叫 `gemini-api-dev` 的 Skill，里面就四件东西：Gemini API 的高层 feature 一览、当前在线的模型和各语言 SDK 清单、每个 SDK 的最基础示例代码、以及一份文档入口列表（写明这才是 source of truth）。

为了测这个 Skill 到底有没有用，他们搭了一套 117 道题的评测集。

- 117 个 prompt，分别生成 Python 或 TypeScript 代码，全部走 Gemini 各语言 SDK
- 涵盖 agentic coding、chatbot、文档处理、streaming、以及一批针对具体 SDK feature 的任务
- 评测有两个模式：vanilla（直接提示模型）和 with skill（开 Skill）
- 开 Skill 的模式下，模型拿到的系统提示词原样照搬 Gemini CLI 里的 snippets，工具只给两个：`activate_skill` 和 `fetch_url`
- 判失败的硬标准是"用了我们老 SDK"

跑出来的数字很干净：

- gemini-3.1-pro-preview：vanilla 28.2% → with skill **96.6%**，涨 68.4 个百分点
- gemini-3.0 Pro 和 Flash 的 vanilla 基线都是 6.8%，加 Skill 之后也涨上来了
- 2.5 系列模型加 Skill 也涨，但远不如 3 系列

Philipp 和 Mark 自己给这件事下的判断是："**Skills work, but they need reasoning.**" 用 3 系列这种推理能力强的模型，Skill 才能真把效果拉满；老一代模型即使给了同一份 Skill，也吃不下来。

按 domain 拆开看，几乎每一类任务都被打到 95%+。唯一一个明显拖后腿的分类是 _SDK Usage_，pass rate 95%。原文给了一个失败例子：

> When I use the Python api with the gemini 2.0 flash model, and when the output is quite long, the returned content will be an array of output chunks instead of the whole thing. i guess it was doing some kind of streaming type of input. how to turn this off and get the whole output together

prompt 自己点名要用 Gemini 2.0 flash，但 2.0 已经不在 `gemini-api-dev` Skill 列出的"当前模型"里。所有模型都答错，拿不准是该照用户的话用 2.0、还是该按 Skill 里的最新模型清单换掉。这是 Skill 这种"写死了当前状态"的设计里最尴尬的一类边界。

这一节的事实密度其实已经撑得起整章。Google 的判断很清楚：有 reasoning 能力的模型加一份维护得住的事实清单 Skill，就能把"知识断档"这个老问题压下去。

**Vercel 那边：同样的思路，在 Next.js 16 评测里 0 个百分点的提升**

Vercel 这边的实验对象不是模型厂的 SDK，而是 Next.js 16 的新 API。Next.js 16 引入了 `'use cache'`、`connection()`、`forbidden()`、`cacheLife()`、`cacheTag()`、async `cookies()` / `headers()` 这些训练数据里基本没有的 API。Jude Gao 团队想测的问题是：给 Agent 配一个 Next.js 文档 Skill，能让它写对这些新 API 吗？

他们一开始也"赌 Skill 会赢"，原文原话是 "**We started by betting on skills.**" 结果跑下来：

- Baseline（不给任何文档）：53%
- 默认装上 Skill：**53%，零提升**
- 56% 的评测里，Skill 根本没被触发，Agent 拿得到，但选择不用
- 在 Build / Lint / Test 拆分里，装 Skill 的成绩反而比 baseline 还差一点（test 项 58% vs baseline 63%）

也就是说，默认配置下，往环境里塞一个不被调用的 Skill，可能反而是干扰。Vercel 把这个现象归到一个更普遍的事上："agents not reliably using available tools is a known limitation of current models." Skill 是被动等召唤的，模型不召唤，它就不存在。

接下来 Vercel 试了"主动指令"：在 `AGENTS.md` 里写一句"先探索项目再调用 Skill"。

- 加这一句之后，Skill 触发率拉到 95%+，pass rate 涨到 **79%**（+26pp）
- 但指令的具体措辞会戏剧性影响结果：写 "You MUST invoke the skill" 让 Agent 一上来就读文档，结果 anchor 在文档样式上、错过项目本身的上下文；写 "Explore project first, then invoke skill" 让 Agent 先建心智模型再查文档，效果更好
- 在 `'use cache'` 这一题上，前一种写法写对了 `page.tsx` 但完全漏掉了必改的 `next.config.ts`；后一种写法两个都写对了

同样的 Skill、同样的文档、同样的模型，只是 prompt 里一句话的措辞变了，结果就差出一截。Jude Gao 用的词是 "brittle for production use"，脆，不适合上生产。

然后他们走了一个相反方向的实验：把那一整套文档**索引**（不是文档本身）压成 8KB 的 pipe-delimited 格式，直接塞进 `AGENTS.md`，并在最前面写一句关键指令——

> IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning for any Next.js tasks.

Agent 拿到的是一张"路标"，知道哪个目录下放着哪些 mdx 文档；要用的时候直接去 `.next-docs/` 里读对应文件。结果：

- AGENTS.md 索引方案：**Build 100% / Lint 100% / Test 100%**，整体 100% pass rate
- 比默认 Skill 高 47 个百分点，比"显式指令调用 Skill"高 21 个百分点
- 索引本身从 40KB 压到 8KB，文档总量没变，但塞进系统提示词的是索引，不是全文

Jude Gao 给出的解释是三件事：第一，没有决策点，`AGENTS.md` 的内容每一轮都在 system prompt 里，Agent 不需要"决定要不要查"。第二，一致可用，Skill 是异步加载、被调用才出现的，`AGENTS.md` 每轮都在场。第三，没有顺序冲突，Skill 会逼模型决定"先看文档还是先看项目"，被动上下文回避了这个问题。

值得注意的是，Vercel 没把 Skill 全盘否定。原文最后一段明确写："Skills aren't useless. ... Skills work better for vertical, action-specific workflows that users explicitly trigger." 例子是"升级我的 Next.js 版本"、"迁移到 App Router"这种用户主动触发的纵向工作流，那种场景下用户的指令本身就是召唤，Skill 的"按需"特性就成立了。

**两边的差异不是对错，是在测两件不同的事**

把 Google 和 Vercel 的实验放在一起看，最容易踩进去的解读是"Skill 有用 vs Skill 没用"。这层解读其实没抓到点。

两边在测的根本不是同一件事。

- Google 测的是：模型主动接到一个**自己 SDK 相关**的任务，能不能借助 Skill 把"老 SDK / 老 API"这个错改对。任务里"和 Gemini 打交道"是显式的，Skill 的召唤条件天然成立
- Vercel 测的是：模型在写**应用代码**的过程中，能不能在没人提示的情况下意识到"我现在该去查 Next.js 16 的文档"。这一步是模型自己要做的判断，恰恰是当前模型的弱项

换句话说，Google 那边 Skill 的"召唤决策"被任务描述本身解决了，剩下的全是"找到正确文档、读懂、写对代码"，这是 reasoning 强的模型擅长的事，所以 3.1-pro 一上就打 96.6%。Vercel 那边 Skill 的"召唤决策"才是真正的瓶颈，56% 的失败案例都死在这一步。

这也解释了为什么 Vercel 显式加一句"先探索项目再调用 Skill"就能从 53% 跳到 79%，这一句话的作用本质上是把"召唤决策"从 Agent 那边搬到了 `AGENTS.md` 这边，让它变成确定的、每轮都生效的硬指令。而再往前推一步、干脆把索引直接塞进 `AGENTS.md`，就是把"决策"彻底取消，不再问 Agent"你要不要查"，而是直接告诉它"查"。

Vercel 自己总结的三个机制（no decision point / consistent availability / no ordering issues）其实是一件事的三种说法：当前模型在"主动调用未被指定的工具"这件事上不可靠，所以越能避免让它做这个决策，效果越稳。

这个判断和"主 Agent 应不应该拆子 Agent"是同一类问题。子 Agent 拆出去的代价就是上下文断裂、主 Agent 看不到子 Agent 经过的判断；Skill 被独立成 on-demand 的资源，代价就是模型必须自己决定何时召唤，而这个决策本身不可靠。能放进主上下文里的东西，往往就别拆。

**模型厂和框架方对 Skill 这层抽象的态度，其实并不冲突**

Google 是模型厂，看 Skill 时关心的是"我作为 SDK 维护方，能不能用一份轻量的东西，把训练数据里没有的最新 SDK 状态推给所有用我家模型的 Agent"。在这个视角下：

- Skill 是模型外的**事实清单**：模型固化的训练知识 + Skill 提供的当前 SDK 状态 = 写对代码
- 维护成本极低（几页纸 + 一份示例代码），适合 SDK 这种"接口稳定、版本更替快"的场景
- Google 自己也承认了一个长期问题：Skill 没有好的更新机制。用户装上之后，Skill 在他们的 workspace 里就成了静态文件，过几个月可能就过时了，反而成了误导
- Google 给的下一步方向是"试试直接走 MCP 拿文档"，也就是把"静态 Skill"换成"实时拉文档"，从根上解掉过时问题

Vercel 是框架方，看 Skill 时关心的是"开发者在写 Next.js 应用时，Agent 怎么稳定地用上正确的、版本匹配的 API"。在这个视角下：

- Skill 的"按需召唤"模型不可靠：开发者在写业务代码的时候不会每条指令都喊"请用 Next.js 16 文档"
- 真正稳的是把"文档索引 + 一句明确的检索指令"放进 `AGENTS.md`，每轮都在
- Vercel 也明确留了 Skill 的位置：用户**主动触发**的纵向工作流（比如版本升级 codemod、框架最佳实践应用）依然是 Skill 最自然的形态

两边的判断合在一起看，可以归到一个更朴素的分界线：Skill 是不是被显式触发。任务描述里天然包含"这是 Gemini SDK 相关的活"，Skill 就站得住；任务描述里没有任何信号能触发 Skill，那 Skill 就必须靠模型自己判断，这一步是当前模型的弱项。

对国内做 Agent 产品的团队来说，这里有一个挺实用的推论：评测一个细分 Agent 的时候，不能只测"我家 Agent 在最佳路径上的成功率"，得加一组对照，同样的题目扔给 Claude Code 加一个通用 Skill 跑一遍。如果你的细分 Agent 干不过 CC 加 Skill，那说明你的架构或者对模型能力的理解可能已经落后于今天这一波 Agent 时代。架构和 Claude Code 类似水平的细分 Agent，正常应该能稳定打过 CC 加 Skill 这条基线，因为你拥有 Skill 拿不到的领域工具、权限和数据。打不过，得回头看是基线选错了，还是产品架构真的过时了。

**我的思考：Skill 涨 68 个点和 AGENTS.md 涨 47 个点，背后是同一件事**

Google 的 +68.4pp 和 Vercel 的 +47pp，其实都在说同一件事的两半：模型训练数据有断档，必须有一种机制把"当前事实"喂进去。Google 选的喂法是 Skill，前提是任务自带召唤信号；Vercel 选的喂法是 `AGENTS.md` 索引，前提是召唤这件事不能交给模型。两边都在解"知识断档"，只是判断"召唤"在哪个场景下成立。

我更愿意提一笔那个 40KB → 8KB 的细节。Skill 时代关于上下文成本的争论里，常见反对声是"塞太多东西会污染上下文"。Vercel 给的答案是：塞进去的不需要是文档本身，而是文档**索引**——一张让 Agent 知道"去哪儿找"的路标。这跟我之前画过的"上一代→当前→下一代"代际划分恰好对应：上一代靠 fine-tune 把领域知识训进模型，当前这一代把领域知识做成可热更新的外部资产，下一代很可能是模型自己动态去拉。

我的判断是 Skill 这层抽象目前处在过渡期的中间形态，比 fine-tune 灵活、比纯 MCP 重，按召唤生效。等模型在"主动调用未被指定工具"这件事上变可靠，Skill 这条路才真正打开。

也欢迎大家留言聊聊：你自己做 Agent 时，是赌 Skill 那边，还是赌 `AGENTS.md` 这边？

（织入了 topic-agent-cc-plus-skill-benchmark、topic-agent-split-context）
