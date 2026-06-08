作者：张和，8年AI产品负责人经验，先后负责过小米AI视觉产品、自动驾驶AI数据闭环体系、大模型落地手机OS，目前在创业做AI应用出海和教育。欢迎微信私聊henryai2024

一. 开篇结论：这才是LLM的第一个杀手级应用！

我认为，ChatGPT Deep Research极有可能成为LLM对人类社会造成真正冲击的第一个杀手级应用。

为什么说它“可能是第一个”？因为在Deep Research这个产品里，我们**第一次**看到了既能多轮思考、又能主动规划和反复自我纠错的AI Agent形态。它不再只是简单回答问题，而是像一个能够“持续研究、不断校对修正、还能规划后续步骤”的实习助理。

**上限极高：如果考虑所有可能的研究场景，Deep Research目前的“平均水平”或许只有40分；但在那些定义明确、重复繁琐的检索或资料整合场景里，它的综合得分可以冲到80分（后面都有实测案例）。****
****
****偶尔会严重翻车，但在需求明确的专业场景中可媲美人类实习生：面对模糊新领域或缺乏明确行业共识的课题时，Deep Research偶尔会出现只有10分的“大翻车”；但只要需求足够专业且边界相对清晰，它又能稳定在60分左右，媲美“初级产品经理级”的研究输出。****
****
****千万不要忽视，千万用发展的眼光看待：当前的效果只使用了o3微调版，如果等到o4甚至o5出现，且在deep research中使用o4 pro（使用更大算力），这个产品不排除在今年内就能实现让实习生感到危机的程度。25年底，o5 pro+ deep research，称之为AGI的前夜绝不过分。****
****
****我从1月份Gemini Deep Research出来没多久就在深度使用，很多人都没看懂谷歌该产品的牛逼之处。OpenAI的该产品也是一样，don&#39;t sleep on it，真正牛逼的agent就是这个！****
****
**![](https://mmbiz.qpic.cn/sz_mmbiz_jpg/diaoia8WzhsqZicQMJ2zOmoyMWRoTLoyHc56eIyIribqvlmnsBicNj9CpXu5sibS1wpF30pnhDdFnbepBgKXDyFIzNVw/640?wx_fmt=jpeg&amp;from=appmsg)**
**
## 二. 产品核心剖析：从架构到能力

## 

### 2.1 什么是Deep Research？

### 

Deep Research是OpenAI推出的一款**深度研究型AI Agent**，拥有强推理、多模态处理、多轮自我纠错能力，能执行类似人类“实习生”的系统性调研工作流程。

核心流程明确需求并打破需求中的模糊点，主动向用户追问细节；（实测追问效果非常好，远超Gemini Deep Research）
制定初步调研或拆解计划（可在它的Thinking Trace中看到）；
依次执行小任务（包括搜索、爬取或解析PDF、网页等）；
如果发现偏离或有新需求，立刻更新规划，持续迭代。
这一切让Deep Research在“自动化研究助理”方向上走得更远，也让我们看到了一个超越一般联网搜索工具如Kimi, Perplexity或DeepSeek联网搜索的AI工作形态。

下图：Deep Research的思考过程极其有趣，经常会在搜索的过程中修正认知，调整研究方向，和人类在连续好几天的工作过程中的思路迭代非常像！

![](https://mmbiz.qpic.cn/sz_mmbiz_png/diaoia8WzhsqZicQMJ2zOmoyMWRoTLoyHc5QDuhiaUyQ53qdbUMlucmYl3TkBfE5JXwNoVzNicFTo6PU7ygiazI4phTQ/640?wx_fmt=png&amp;from=appmsg)

### 2.2 与ChatGPT/Deepseek/Gemini Research等的差异

### 

**多轮深度长周期任务规划和执行：Deep Research会在执行任务进行很多次不同层级的规划，和一般“问答式”或“30秒内快速生成文本”的工具很不一样。****
****
****多模态+代理执行：除了文字，它还能解析PDF/图片，并且在网页打不开或信息不足时具备一定自我修正能力。****
****
****更高的任务上限：背后的O3模型经过特定微调，尤其强化了复杂任务规划能力。这让它远胜过简单浏览器插件或传统ChatGPT网络搜索模式。
**
### 2.3 使用流程与对话式反馈

### 

**交互式澄清：当你提出一个研究需求，比如VC方向的行业报告，Deep Research会先询问“聚焦哪个细分赛道”“时间区间”“需要多深的技术拆解”之类的问题。****
****
****Thinking Trace可视化：它会把规划过程、遇到错误的原因、下一步计划都记录在思考轨迹中。阅读这些思考过程，本身也能帮助我们理解AI如何迭代地进行研究。
**
## 三. 实测案例分析和对比：上限很高，但偶尔也会严重翻车
下面分享我在短短一个晚上对Deep Research所做的10多个案例测试。其中有的非常惊艳，有的则需要多轮纠正才能看出成效。**
**

### 3.1 高分案例：重复繁琐+定义明确

### 

**案例A：GPT-4论文200多个作者信息爬取**

**任务描述：让Deep Research找到2023年初GPT-4 Technical Report中所有作者的学历、教育背景、工作履历、目前就职单位等详细资料。****
****
****表现：Deep Research先分解子任务：①获取作者名单 → ②挨个检索每位作者 → ③整合信息并去重 → ④若信息不全则再次搜索。****
****
****结果：一次完成度高，表格信息误差较低，整体可打到80分。**
下图：上下滑动查看超长对话截图

![](https://mmbiz.qpic.cn/sz_mmbiz_png/diaoia8WzhsqZicQMJ2zOmoyMWRoTLoyHc5tUYYvTWNawqmxkubOd3BZv2P5RCicM5N61ZMfX3ibazUVeLciclAdx4PQ/640?wx_fmt=png&amp;from=appmsg)
**相同任务对比DeepSeek的联网搜索：**

**deepseek首先根本没找到作者名单！其次找个理由说OpenAI署名公司名，没有个人名称。最终是0分。**

**截图如下**

![](https://mmbiz.qpic.cn/sz_mmbiz_png/diaoia8WzhsqZicQMJ2zOmoyMWRoTLoyHc5mRzN6kVGmQFbnDVMic4TNXnYVou4wUHjekseaibNH79RKWLe4XWgo8zg/640?wx_fmt=png&amp;from=appmsg)**
**

**案例B：繁琐的调研任务，效果还可以**

**任务描述：收集谷歌CEO Sundar Pichai和DeepMind CEO最近两年的公开访谈和演讲，并用YouTube链接制成表格。****表现：Deep Research在过程中主动处理失效链接，搜索完又回头重新校对。****结果：最终输出质量堪称“一次成型”，可在70分左右（部分讲座没搜到漏了）。下图：上下滑动查看超长对话截图，由于公众号限制，完整多轮对话点此链接https://chatgpt.com/share/67a0ad1b-c808-8012-811f-2abfca6ca174

**

![](https://mmbiz.qpic.cn/sz_mmbiz_png/diaoia8WzhsqZicQMJ2zOmoyMWRoTLoyHc5D1nZqibDtoQg0hWzcJhRWOG6dnZLAdYC1KckDSXfro3hof6FhmIVAbQ/640?wx_fmt=png&amp;from=appmsg)*
*

**总结**：对于繁琐但需求明确的互联网信息搜集整理任务，Deep Research的多轮规划和自动纠错让效率大幅提升。在人力角度，这些工作本需花大量时间；它却能在十来分钟内完成。

### 3.2 中等案例：需求明确但专业度高

### 

**案例：真实AI产品经理需求，写一份多模态大模型在AR眼镜中的落地与评测报告**

**任务描述：要求Deep Research输出关于多模态模型在AR眼镜的落地方案，并重点分析视觉理解能力及测试指标，提供中英文双语参考信息。****表现：它能给出比较专业的测试方案，并针对AR眼镜的特殊性（硬件限制、场景需求）做了较深入的剖析。****打分：整体可达60分，相当于一个初阶AI产品经理的水平。****不足：看起来Deep Research对于特别新的重点信息，比如GPT-4o, Gemini 2.0 Flash等情况没有查询到，后续在多轮反馈中人工提示后才逐渐完善。****
****
**下图：上下滑动查看截图，由于公众号限制，完整多轮对话点此链接：https://chatgpt.com/share/67a0df1d-0e88-8012-b015-549ed7f4f453

![](https://mmbiz.qpic.cn/sz_mmbiz_png/diaoia8WzhsqZicQMJ2zOmoyMWRoTLoyHc5vo8gKOiaJ7HcYEskibqU2k0ftjlbrFXz3PeJPAVVxzK2QaiaUUTQwovyw/640?wx_fmt=png&amp;from=appmsg)**总结**：当需求较为清晰且资料在网上可查时，Deep Research能很好地拆解和产出。但若用户想追踪“最前沿”或“最新发布”的动态，可能还需自己提供更具体的关键词。

对比：此任务对比Gemini Deep Research，谷歌对意图解读完全错误，同时连大模型方向都没有查到而是输出了一些很传统的AI落地和测评方案，完全被OpenAI吊打。

下拉滑动查看Gemini Deep Research报告

![](https://mmbiz.qpic.cn/sz_mmbiz_png/diaoia8WzhsqZicQMJ2zOmoyMWRoTLoyHc5icOLbqkkiblibY5SJpWJp5ReCUZJRW5KCicKqd8sYWzyGV3rWYbCM1scTg/640?wx_fmt=png&amp;from=appmsg)

### 3.3 低分案例：不确定+概念模糊
**案例：AI Agent行业研究报告（VC视角）**

**任务描述：让Deep Research基于VC视角，写一份关于“AI Agent”行业的研究报告。但我最初并未给它清晰的“AI Agent”定义。****问题：它在搜索与思考过程中严重发散——一会儿查OpenAI的融资信息，一会儿又跳到Character.ai等聊天工具。迟迟无法定位真正的“自动化代理型Agent”。****多轮纠正：只到后来我加入“只搜索英文资料”“参考OpenAI对Agent的定义”等限制，它才逐步聚焦。最开始可算10分不及格，经过多次迭代后，最高才接近40分。**下图：下滑查看截图，由于公众号限制，完整对话点此链接：https://chatgpt.com/share/67a0dede-7c60-8012-9a5b-42bcd9ada13b&nbsp;

![](https://mmbiz.qpic.cn/sz_mmbiz_png/diaoia8WzhsqZicQMJ2zOmoyMWRoTLoyHc5lzoT0ibn4PZAGCzFhnRQbetyibAK6xTApspP2VuLq7rmcm5eWojl20yA/640?wx_fmt=png&amp;from=appmsg)
**总结**：如果用户的目标本身充满不确定性或行业概念缺乏统一定义，那么Deep Research的自动规划就会大打折扣。需要强力人工介入才能扭转局面。

## 四. 更大潜力：对标与未来展望

## 

### 4.1 对比国内外竞品
**Gemini Research：谷歌也推出过一个类似的多轮研究工具，但在“规划深度”与“自主纠错”方面，明显没有Deep Research这么彻底。****Perplexity/Deepseek/Kimi：多为“一阶搜索+AI回答”，缺乏长时多步思考及动态调整。****结论：Deep Research让“多轮分步拆解、自动纠错”成为实际可用的功能，上限非常高，也在个别场景下表现出接近专业研究助理的水准。
**
### 4.2 O4、O5与AGI的前夜
**持续升级：OpenAI正在研发O4，甚至到2025年年末大概率会有O5。届时，Deep Research或许能更好地处理前沿信息，或者完全兼容语音、图像、文档各类多模态数据。****对人力市场的冲击：对初级分析师、助理、数据挖掘人员的影响将最先凸显。许多“搜集-整理-报告写作”类型的任务，都能由AI替代或大幅减少人力成本。
**
### 4.3 国内玩家的机遇与挑战
**模型规模+专业微调：要赶上O3的多步推理、广泛知识面，并且在深度研究场景中保持稳定，难度非常高。****
****
****专注垂直领域：中国市场也许可以在特定行业（如医疗、金融、法律）做专业调优，用半自动化流程结合大模型，形成差异化竞争。
**
## 五. 结尾：深刻启示

## 

总的来说，Deep Research在以下方面给我们带来深刻启示：

**完整的“研究闭环”：可以多次检索、调整思路，执行中或执行后不断修正。****惊艳的高分场景：当需求清晰、信息可得时，Deep Research的表现堪比人类实习生甚至更好。****痛点亦明显：当需求模糊或信息源头缺失，它也会大幅跑偏，输出低质结果，需要多轮人工干预。
**然而，如Sam Altman所言，这款产品依旧可能为全球GDP带来个位数增长的冲击，可见它在未来一至两年内具有重大潜力。对个人、企业和产业来讲，掌握好这个工具可能是一次“卡位”，能让你在信息时代更快完成原本需要几天的工作。

**如果你觉得以上测评对你有所启发，欢迎扫码加我微信，我会邀请你加入我组织的微信群。**

**与我在平时工作中做的深度AI竞品调研分析相比，本文由于时间紧迫和篇幅所限，还可以更加深度和专业，尚有一些有亮点的洞察来不及加入，我后续还会在朋友圈和微信群中分享更多深度洞察。**

我的微信二维码![](https://mmbiz.qpic.cn/sz_mmbiz_jpg/diaoia8WzhsqZicQMJ2zOmoyMWRoTLoyHc5U6m8iarGUIxgiaDz0EFQLEh3biaficaHYI2pyktc6dtVTrGVsN8W8ic7BOQ/640?wx_fmt=jpeg&amp;from=appmsg)

          
            var first_sceen__time = (+new Date());
            if ("" == 1 && document.getElementById('js_content')) {
              document.getElementById('js_content').addEventListener("selectstart",function(e){ e.preventDefault(); });
            }