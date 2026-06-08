# Claude Code 产品负责人首次开口：把 PM 这件事重做了一遍

Anthropic 月度 ARR 跑到 110 亿美金量级，全公司 PM 一共 30 到 40 个人。功能上线节奏从 6 个月压到 1 个月，常规 1 周，偶尔 1 天。Lenny 在播客里原话："I've never seen anything like the pace you folks at Anthropic are shipping at." 这套节奏背后到底动了哪几刀？Cat Wu 第一次出面，把传统 PM 工作里的协调、对齐、PRD、长路线图基本全部砍掉，只留下一件事：让一个想法在一周内变成线上功能。

Cat Wu 是 Anthropic Claude Code 和 Cowork 的产品负责人，和 Boris Chen 搭班子。Boris 是 Claude Code 的创造者，Lenny 之前请他上过一期，目前是这档播客单期播放量最高的一期。Cat 跟 Boris 的分工大致是 80% mind-meld + 20% 各自的偏执：Boris 抓 3-6 个月之后的 AGI 形态版本，定义"产品三到六个月后该长成什么样"，Cat 抓"从今天走到那个版本"的路径，外加跨团队不卡壳——研究、市场、销售、财务、容量，所有人朝同一个方向走。她原话说，自己更多时间花在 cross-functional 上，"让大家朝一个方向划船"。

Lenny Rachitsky 在 4 月 23 日请 Cat 上了一期播客，一个半小时，几乎没有客套话。Cat 平时不怎么公开露面，这是她第一次系统讲 Anthropic 的产品节奏是怎么搭起来的。视频上线两周播放量超过 20 万，硅谷做 AI 产品的几乎人手转过一遍。下面这几节按她说得最锋利的几段重排了顺序。

**功能上线节奏，从 6 个月压到 1 天**

Cat 一开口就把传统 PM 工作的预设打掉。AI 之前的技术迭代慢，所以才需要 6 到 12 个月的长路线图和跨团队对齐；模型每隔几个月跳一次能力，长路线图本身就在变形——你花一个季度做完的对齐文档，下一个模型版本一上线，里面的优先级就已经过期了一半。她在 Anthropic 看到的产品节奏，是把这一整套协调机制压成一条尽可能短的链条。

- 功能上线周期从 6 个月压到 1 个月，常规是 1 周，偶尔 1 天
- 内部走一个叫 Evergreen Launch Room 的频道：工程师 dogfood 完直接发帖，Sarah 带文档、Alex 带 PMM、Tara 和 Lydia 带 DevRel 跳进来，第二天就能把发布物料和文档全部出完
- 没有 launch readiness review，没有功能冻结日，没有跨团队 PRD 评审；PRD 只在"特别模糊的方向"或者"重基建项目"上写
- 网上有人猜他们快是因为内部偷用 Mythos 模型，Cat 当场否了。Cat 原话："we do use the models internally and I think this has increased our rate of shipping a little bit but I don't think it explains the bulk of the increase"
- 真正的解释是预期：团队默认任何想法应该一周内进用户手里，于是每一道流程都因此变得"很贵"，自然被磨掉

Cat 用的词是"remove every single barrier to shipping things"。我读到这句的时候停了一下：这不是流程更高效，是流程被砍掉了——多数公司还在问"如何让评审更快"，Anthropic 已经在问"这个评审还要不要"。

**Research Preview 是默认发布姿态，代价是产品一致性**

Anthropic 过去半年绝大多数新功能都挂着一个 Research Preview 标签，写着"早期产品，可能不会一直支持"。看起来像免责声明，但放在 Anthropic 这套节奏里，它其实是最重要的一种发布姿态——把"承诺"降级成"邀请测试"，一两周内丢出去拿反馈。这一招让团队不必先扛起长期支持的包袱，新东西才能真的进用户手里。

- Research Preview 让团队不用先承诺长期支持，就能把新东西塞到用户手里
- Cat 公开承认了这套姿态的代价。原话："we're sacrificing product consistency"
- 同一种能力同时存在多个 form factor：终端 Claude Code、桌面 Claude、网页和手机远程会话、Cowork 的文档协作入口；新用户经常分不清同一件事该在哪个入口做
- 解法不是替用户选一条 best path，而是同时放出去，让用户用脚投票
- 用 `/powerup` 这类内置 onboarding 来补学习成本。Cat 原话："we felt like the product should be intuitive enough that you don't actually need to go through any tutorial"——这是他们原本的原则，最后被现实推翻了
- Cat 公开承认产品哲学被现实推翻这件事本身就罕见——多数大厂不会在播客上退这一步
- Cat 的判断：长期看，产品最终会收敛，但收敛的方式不是 PM 在房间里画图，而是看哪条 form factor 先长出真实用户黏性

**AGI 信仰要刚刚好，多一分少一分都做不出产品**

整场访谈最锋利的一段，是 Cat 谈"AGI-pilled 的度"。做 AI PM 最难的活不是为未来的 AGI 设计产品——那种产品反而好做，本质就是一个聊天框加一堆 MCP 工具，模型自己问问题、自己调工具、自己 patch 自己的弱点，PM 几乎不用干涉。真正难的是反过来：榨干当前这一代模型的上限，让今天的用户今天就能用上。

- Cat 原话："It is very hard to be the right amount of AGI pilled"
- 极端 1：完全相信下一代 AGI 万能 → 做出来的产品今天根本不能用
- 极端 2：完全不相信模型还会跳 → 做出来的产品下一次模型升级就要废弃
- 当前一代怎么榨：让产品引导用户走到"模型的强项"上，并提供"补丁"绕过模型弱点
- Cat 给的方法是"build products that don't necessarily work yet"——先做出当前还不太行的原型，下一次模型升级直接换模型，看是不是缺口被补上了

这套"上一代→当前→下一代"的视角，正是我在训练营里反复讲的技术演进框架——AGI-pilled 像一根刻度尺，上调一格今天就崩，下调一格明年就废，PM 的认知深度最后落到"你押在哪一代"这一个判断。

**模型升级时，最重要的动作是删功能**

每出一版新模型，多数公司想的是"再加点新能力"。Cat 给的反直觉答案：先回头看哪些功能可以删。很多功能本来就是给老模型打的补丁，模型变强了，补丁就该撕掉。Cat 在播客里给了一个很具体的例子，能把这件事讲透。

- 早期 Claude Code 接到跨 20 处的重构任务，改完 5 处就停。Sid 给它加了一个 to-do list 工具，让模型先列清单再逐条划掉，成功率立刻拉满
- Opus 4 及以后的模型已经"naturally"会自己用 to-do list，不需要 prompt 提醒
- 每出一版新模型，团队会通读整个 system prompt，逐段问"这一条提醒模型还需要吗"，不需要就删
- 新模型解锁的不是"再加层提醒"，而是"原来跑不通的功能现在可以做了"。Cat 举的例子是 code review：之前几次都做失败，直到 Opus 4.5 / 4.6 和 Sonnet 4.6 才真正稳到 Anthropic 自己的工程师愿意 merge 前依赖它
- 现在 code review 能跑多个 agent 并发遍历整个 codebase，合成出一组"真问题"清单
- Anthropic 给自己定的硬规则："模型一发，先通读整个 system prompt"——不是审美洁癖，是节奏的源头

**有 taste 的工程师比"AI sense PM"更值钱**

外面一直在讨论 AI 时代还需不需要 PM。Lenny 把另一位嘉宾 Amol 的相反观点摆给 Cat：因为工程师 ship 太快，PM 和设计师反而需要更多，否则跟不上节奏。Cat 没接这个论点，她的答案是岗位边界在融化——工程师做一部分 PM 的活，设计师写前端代码，PM 自己也下场写代码。Anthropic 的招聘策略很明确：宁可招"有 product taste 的工程师"，让一个工程师从看到 Twitter 反馈到上线，全程几乎不需要 PM 介入。

- Cat 原话："we're pretty focused on hiring engineers with great product taste... there are many engineers on our team who are fully able to end to end go from see user feedback on Twitter through to like ship a product at the end of the week with almost no product involvement"
- 团队里几乎所有 PM 都做过工程师，或者现在还在 Claude Code 里写代码；连设计师也都做过前端
- 工程背景"在接下来几个月"对 PM 仍然有用，因为知道"这件事建起来多难"会影响优先级判断
- Cat 强调这个判断的时间窗口很短："every few months it seems like there's a large increase in coding capability which then changes what other roles are valuable"
- product taste 是稀缺技能，来自什么背景都行，但"能展示出来"的人 Anthropic 都会想招

这段跟我对 AI PM 市场的判断对得很齐：稀缺的本质不是人少，是市场对"什么是好的 AI PM"画像不清晰，认知差抹平了人就能靠拢。Anthropic 把画像收敛成一句更狠的话——能从用户反馈一路做到上线。

**Eval 是 PM 真正的新技能**

聊到 PM 的新技能，Cat 把 eval 拎得很高，但讲法和市场上常听到的不一样——不是"建几百条 eval 覆盖所有 case"，而是"用 10 条好 eval 把目标说清楚"。这件事我自己在训练营和咨询里反复讲过，听到 Anthropic PM 头讲一遍，落地动作几乎一模一样，多少有点惊喜。

- Cat 原话："You don't need to build hundreds of evals for them to be useful. Just building 10 great evals is important for helping the team quantify what the goal is"
- PM 跳进 eval 的时机：某个功能"需要更精确的产品定义"时
- 输出形态：5 条 eval + 怎么跑 + 哪条过哪条不过 + 用什么 prompt 把成功率提上去
- 团队还有专门一个 pod 跟 research 配合，把 Claude Code 行为拆细量化，找最大改进空间
- Cat 自己有两个"高质量 evaluator"标签：Amanda（塑造 Claude 性格的人，连"什么算成功的 character"都能讲清楚）；Claude Code 团队的午餐桌（新模型一上来，挨个问 vibe，"这版模型不够解释自己"、"太爱写 memory"、"loves to test itself"，再回去查数据看是不是普遍模式）

Eval 这套用法，本质是用最少几条样本把"什么叫做对了"钉死——评测不是为了覆盖率，是为了让研发知道下一步该改哪。我看到 Anthropic 把"找谁来当 evaluator"也算进 PM 的能力地图，比国内大多数团队前置了一整层认知。

**Cat 的工作 motto：Just do things, jobs are fake**

访谈最后的 lightning round，Lenny 问 Cat 的人生格言。她给的答案是 "Just do things"——然后补了一句更狠的："I think jobs are fake." 这两句话在硅谷已经被不少人引用过，Cat 是这句话最近半年最积极的传播者之一。

- 完整说法："If you understand the constraints, you can figure out what you can do and then just like try to do it quickly, learn from the mistakes and apologize or fix them if you did something wrong"
- Cat 解释这句话的能量来自哪：传统公司岗位边界画得很死，"这块代码这个团队碰，那块不许碰"；"Just do things" 给团队的是"可以跨边界做事，先把事做了"的许可
- Cat 自己的来历：在 Scale AI 20 人时进去，没有流程、问题很大；这段经历让她相信"在没人告诉你怎么做的时候自己把事做了"是可以训练出来的肌肉
- 配套机制：team principles 文档写清楚关键用户是谁、目标是什么、可以牺牲什么；任何人不需要找 PM 或 stakeholder 解锁，自己就能拍板
- Cat 给所有听众的建议："Find the repetitive parts that you can pass to Claude, iterate on those automations until the success rate is very high"——但她加了一条狠话：90-95% 准的 automation 不算 automation，剩下 5-10% 的精度必须靠人去磨
- Cat 本人也还在踩坑——她训练 Cowork 帮她做 Gmail inbox zero，原话是 "it is definitely not there"

**我的思考：这场访谈真正在说的，是 PM 这个岗位的减法时代**

我听完这一期，反复回放的不是那些数据，而是 Cat 全程的姿态。她没用一句"我们重新定义了 PM"的口号，但她讲的每一段都在做同一件事——删。删长路线图、删跨团队评审、删功能冻结日、删 PRD 默认要求、删模型变强后已经不需要的 prompt 补丁、删那些"应该一直支持"的产品承诺。剩下来的 PM 工作只有两块：把目标钉死（team principles + 10 条 eval），把发布通道铺平（Evergreen Launch Room + Research Preview）。中间那些"协调、对齐、风险管理"，全交给"预期"本身去解决——团队默认一周上线，于是所有挡路的东西都自动变贵，没人愿意为它付时间，慢慢就被磨掉了。

我前段时间一直在想 2026 会不会是广义 AGI 元年。Cat 这场访谈给了我一个偏侧面的证据：当模型每几个月跳一次能力，PM 这个岗位最有价值的动作不再是"加法"——加流程、加文档、加路线图、加跨团队会议——而是反过来的"减法"。减到最后只剩下两件事的人，才能跟得上模型的节奏；减不下去的，就会在每一次模型升级时被自己上一版的 PRD 拽住后腿，眼看着隔壁团队用一周时间把你预计两个月才能做完的功能上了线。

这件事对国内做 AI 产品的人最实用的一条推论：别再优化你的 PRD 模板了，先回头问哪些 PRD 根本不该写。

也欢迎大家留言聊聊，你在自己工作里，哪一道流程是 Cat 这套"砍掉而不是优化"的逻辑下最该被砍的。

（织入了 exp-pm-tech-three-gen-framework / topic-ai-pm-hiring-cognition-gap / exp-eval-driven-at-scale / topic-2025-2026-agi-inflection）
