# Benchmark Corpus

这个文件用于建立“真正好文章”的参照系。它不是风格库，不用于抽句式、复刻段落结构或模仿口头禅；它用于判断一篇文章到底属于哪一种高质量形态，以及缺哪一种质量发动机。

使用任何 benchmark shape 前，先执行 `zhang-viewpoint-first.md`。benchmark 只能帮助选择文章形态，不能替代张和观点。外部天花板样本用来学习“如何论证得更深”，不是用来把张和文章改写成另一个作者的观点。

## 先修正一个错误

不要把“像深思圈”当成唯一目标。深思圈有些文章开头强、信息密度够、节奏顺，但也有明显公众号套路：固定反问开场、宏大判断过密、结尾号召重复。它们适合拆维度学习，不适合整体复刻。

同样，不要把“张和唯一认可样本”当完整风格圣经。正样本只用于提炼“为什么它成立”，不能变成结构模板。

## 可作为 80 分基准的文章形态

### 1. 业内人士深度复盘

**代表样本**

- `../../../.agents/skills/content-writing-guide/refer/张和：OpenAI悄悄跟进Skill：我在小米推了两年的方向，字节用豆包手机助手做出来了.md`
- `../../../.agents/skills/content-writing-guide/refer/张和：Manus五个月前的争议性决策，才是扇动蝴蝶翅膀的关键.md`

**为什么它成立**

- 文章不是从材料开始，而是从作者被现实事件刺痛的位置开始。
- 作者有不可替代的“我为什么能讲”：亲历、判断兑现、实测、行业位置。
- 不是单点观点，而是多个反常识判断串成行业全景。
- 读者读完会觉得“这件事只有真正做过的人才会这么拆”。

**80 分最低线**

- 至少有一个张和不可替代素材：大厂经历、真实项目、实测、课程/学员中可匿名化的真实 bad case、长期判断兑现。
- 不能只把张和履历贴在开头；履历必须进入论证链。

### 2. PM 视角技术教材

**代表样本**

- `corpus-paths.md` 中的张和同形态作品：`张和_长上下文工程`、`张和_AI产品落地架构`、`张和_RAGFlow深度架构`
- Eugene Yan, `Product Evals in Three Simple Steps`: https://eugeneyan.com/writing/product-evals/
- Hamel Husain, `Your AI Product Needs Evals`: https://hamel.dev/blog/posts/evals/
- Anthropic, `Building effective agents`: https://www.anthropic.com/research/building-effective-agents

**为什么它成立**

- 文章不是翻译资料，而是把多源信息重新组织成 PM 可以使用的判断框架。
- 有自创分类法或明确决策框架，而不是“第一第二第三”的信息归档。
- 每一节都回答一个产品决策问题：什么时候用、什么时候不用、失败怎么识别、如何评测。
- 读者能带走一个可以落地的表、流程、评估口径或边界判断。

**80 分最低线**

- 至少 3 个一手信源或强案例，且不是按来源分节。
- 必须产出一个“填好的”样例或决策框架，不能只给空清单。

### 3. 体感报告 / 产品实测

**代表样本**

- `../../../.agents/skills/content-writing-guide/refer/深思圈：Stripe每周1300个AI写的PR.md`
- `../../../.agents/skills/content-writing-guide/refer/深思圈：OpenClaw之后,为什么大多数人还是感觉差一截.md`
- Simon Willison, `Here’s how I use LLMs to help me write code`: https://simonwillison.net/2025/Mar/11/using-llms-for-code/

**为什么它成立**

- 开头有真实使用场景，不是抽象趋势。
- 产品细节能被读者看见：入口、交互、成本、约束、失败点、替代方案。
- 作者不是“介绍产品”，而是在回答“这个产品改变了哪条工作流”。
- 好的体感报告会有取舍：它告诉你这东西在什么条件下有效，也告诉你边界在哪里。

**80 分最低线**

- 没有真实实测、截图、使用路径、失败 case 或对标产品，不写长文。
- 不能把官方发布稿改写成“我觉得这个产品很重要”。

### 4. 反主流单点

**代表样本**

- `corpus-paths.md` 中的 Hamel `Stop Saying RAG Is Dead`
- `corpus-paths.md` 中的 Ethan `Against Brain Damage`
- `../../../.agents/skills/content-writing-guide/memory-bank/best-cases.md` 里点赞较高的反主流标题文章

**为什么它成立**

- 只有一个足够尖的判断，全文围绕它不断加压。
- 不是“唱反调”，而是指出主流叙事漏掉的变量。
- 证据短、硬、贴近作者经验，不靠材料堆满。

**80 分最低线**

- 观点必须可被反驳，不能是“大家要更重视 X”。
- 文章最好短一些，别把一个单点判断撑成 4000 字空转。

### 5. 高在场度单源解读

**代表样本**

- `C-single-source/references/深思圈_2026-05-03_LangChain团队AIagent销售营销最佳实践.md`
- `C-single-source/references/深思圈_2026-04-10_a16z当AIAgent成为软件的主要用户.md`
- Google Developers Blog, `Closing the knowledge gap with agent skills`: https://developers.googleblog.com/closing-the-knowledge-gap-with-agent-skills/
- Vercel, `AGENTS.md outperforms skills in our agent evals`: https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals

**为什么它成立**

- 外部原文只是弹药，作者自己的产品判断才是主角。
- 读者不是来看“这篇英文文章说了什么”，而是看“张和会从这里判断什么”。
- 好的单源解读会把原文转成一个可执行工具：baseline 表、评测方案、选型框架、产品风险清单。

**80 分最低线**

- 单源解读如果没有张和视角，默认最多 65 分。
- 只要全文节标题能改成“原文第一点 / 第二点 / 第三点”，就不是高质量解读。

## 外部天花板样本怎么用

- Eugene Yan：学“体系化、可执行、工程化验收”，不学英文博客语气。
- Hamel Husain：学“反主流 + eval 实战 + 不信 vibes”，不学短文碎片化。
- Ethan Mollick：学“自创概念命名 + 学术类比 + 现实案例”，不硬造玄学概念。
- Lilian Weng：学“概念谱系和边界”，不把张和号写成论文综述。
- Simon Willison：学“真实使用细节和工具体感”，不学日更碎片结构。
- Anthropic / Google / Vercel / LangChain 官方博客：学原始事实和工程边界，不学企业公关稿口吻。

## 对 `rev80` 这类稿件的新判断

`ZHC20260510_193305_001 - 细分Agent产品，先过这条Skill基线.rev80.md` 事实更准，也有 baseline 表，但它仍然不能算真正 80 分文章，原因是：

- 它属于“高在场度单源解读 / PM 技术判断”的混合型，但没有足够的张和不可替代素材。
- 文章的核心动作是“解释 Google + Vercel 两篇文章”，不是“张和用自己的经验重新定义一个产品判断”。
- baseline 表是有用的，但像抽象建议；缺一个填好的真实样例或训练营/项目 bad case。
- 它读起来像一篇合格的 AI 产品分析稿，不像一篇能增强张和专家人设的主账号文章。

如果要把这类稿真正推到 80 分以上，优先补：

1. 张和自己跑过或看过的一个细分 Agent baseline case。
2. 一个“通用模型 + 文档 / skill / 产品方案”的填好对比表。
3. 一个产品团队因为没跑 baseline 而误判壁垒的匿名 bad case。

没有这些素材，就应降级成短帖或资料评论，不要继续靠文风返修。

## 使用规则

写作前在 `topic-preflight.md` 里先选择一个 benchmark shape。审稿时在 `zh-editor-review.md` 里检查文章是否达到了对应 shape 的最低线。

一篇文章可以混合两种形态，但只能有一个主形态。主形态不清楚，通常意味着文章在同时服务热点、转型、招生、方法论和资料解读，应该回到 brief 砍目标。
