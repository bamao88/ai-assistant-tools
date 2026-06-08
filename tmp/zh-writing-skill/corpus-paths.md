# corpus-paths：素材路径地图

> 本文件分两部分：
> 1. **已 bundle 的样本索引**——`samples/` 下当前 30 个文件，按 reference 分类
> 2. **源路径地图**——指向 `knowledge_base/` 下更多未 bundle 的样本，用于添加新样本时定位
>
> 各 reference 文件的"参考文章"段直接用 `samples/X-xxx/...md` 相对路径。本文件用作扩展索引。

---

# Part 1：已 bundle 的样本（30 个文件）

## A-firsthand/（10 篇）

### 业内复盘子模板（3 篇）★

- `samples/A-firsthand/业内复盘_张和_我在小米推了两年.md` ★ 唯一张和样本
- `samples/A-firsthand/业内复盘_eugene_Principal_IC_Advice.md` — 31 条 Principal IC 建议
- `samples/A-firsthand/业内复盘_ethan_Working_with_Wizards.md` — Wizard 范式（自创术语+学术类比）

### 反主流单点子模板（4 篇）

- `samples/A-firsthand/反主流单点_深思圈_Agent终局.md` — 开篇反转 + 层级递进
- `samples/A-firsthand/反主流单点_刘小排r_天兵天将.md` — 反主流人生选择论证
- `samples/A-firsthand/反主流单点_hamel_Stop_Saying_RAG.md` — 一句反主流标题 + 短而锋利
- `samples/A-firsthand/反主流单点_ethan_Against_Brain_Damage.md` — 分学习/创造/团队三层论证

### 踩坑指南子模板（3 篇）

- `samples/A-firsthand/踩坑指南_刘小排r_ClaudeCode防封号.md` — 第一性原理推导规则背后逻辑
- `samples/A-firsthand/踩坑指南_刘小排r_最穷技术栈.md` — 数据对比 40 倍差冲击力
- `samples/A-firsthand/踩坑指南_刘小排r_RAG可以不学.md` — 反主流技术判断 + 经验路线

## B-knowledge-system/（9 篇）

### 张和已写过的同形态作品（3 篇）★

- `samples/B-knowledge-system/张和_长上下文工程.md` ★ 自创"四种失效模式"分类法
- `samples/B-knowledge-system/张和_AI产品落地架构.md` ★ 教材式四模块结构 + Workflow vs Agent 选型
- `samples/B-knowledge-system/张和_RAGFlow深度架构.md` ★ 单产品深度架构拆解（PM 视角）

### 海外天花板样本（6 篇）

- `samples/B-knowledge-system/eugene_Compound_with_AI.md` — Context/Config/Verification/Delegation/Loop 五层框架
- `samples/B-knowledge-system/eugene_Product_Evals.md` — 三步法骨架，每步给具体执行指标
- `samples/B-knowledge-system/hamel_LLM_Evals.md` — 50+ FAQ 形式构建知识库
- `samples/B-knowledge-system/lilian_Reward_Hacking.md` — 概念谱系拆分 + 数学推导 + 缓解方法全景
- `samples/B-knowledge-system/ethan_Shape_of_AI.md` — 自创概念三件套（Jaggedness/Bottlenecks/Reverse Salient）
- `samples/B-knowledge-system/ethan_Guide_to_Which_AI.md` — Models/Apps/Harnesses 三层框架

## C-single-source/（7 篇）

### 高在场度（推荐 ZH 走这档，1 篇）

- `samples/C-single-source/高在场度_Anthropic评估二次解读.md` — 跟着原文走但加大量产品视角解读

### 中在场度（轻编译+观点，3 篇）

- `samples/C-single-source/中在场度_深思圈_a16z观点.md` — 硅谷 KOL 观点引入，逐项展开
- `samples/C-single-source/中在场度_深思圈_ClaudeCode之父预测.md` — 人物访谈编译，信息与解读均衡
- `samples/C-single-source/中在场度_深思圈_2026红杉年度.md` — 大会内容提炼

### 低在场度（ZH 反面教材，2 篇）

- `samples/C-single-source/低在场度_Assistant-Axis论文.md` — 几乎纯论文翻译，作者影子很淡
- `samples/C-single-source/低在场度_DeepSeek-V4论文.md` — 直接转译国外大佬解读

### 学术精讲（不该走，1 篇借鉴细节）

- `samples/C-single-source/学术精讲_PaperAgent_Harness论文.md` — 严格学术结构

## D-product-feel/（4 篇）

- `samples/D-product-feel/深思圈_当AI不再只是工具.md` — 个人体验开场 + 升华到产品形态范式
- `samples/D-product-feel/深思圈_当AI写了80的代码.md` — 用场景切入组织问题
- `samples/D-product-feel/深思圈_Notion产品负责人.md` — 引用一线产品高管观点
- `samples/D-product-feel/深思圈_美国AI开处方获批.md` — 数据化案例复盘产品逻辑

---

# Part 2：源路径地图（knowledge_base/ 下未 bundle 的样本）

> 添加新样本时按以下路径找。基础路径：`/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/`

## 张和原作

`client/raw/works/`（4 篇全部已 bundle）

辅助：
- `client/raw/chat/` — 张和与用户对话记录（170+ JSON，第一人称素材验证）
- `client/raw/meeting/` — 会议纪要（如 `20260411_张和的快速会议.md`）
- `client/wiki/expertise/` — 张和专长主题维基

## 国内竞品（4 账号 / 87 篇，已 bundle 12 篇）

### 刘小排r（20 篇，已 bundle 3 + 1 = 4 篇）
- 主流形态：体感实测型(50%) + 反主流断言型(40%)
- 适用 reference：**A-firsthand**（踩坑指南 + 反主流单点）
- 路径：`market/raw/competitor/gzh-accounts/刘小排r/`

### 深思圈（20 篇，已 bundle 8 篇）
- 主流形态：编译+观点型(40%) + 体感报告型(25%) + 反主流型(20%)
- 适用：**D-product-feel** + **C-single-source**（中在场度）+ **A-firsthand**（反主流）
- 路径：`market/raw/competitor/gzh-accounts/深思圈/`

### AI产品阿颖（20 篇，未 bundle）
- 主流形态：编译+观点型(60%) + 体感型(30%)
- 适用：参考价值有限（轻量编译，ZH 不该模仿）

### PaperAgent（27 篇，已 bundle 1 篇）
- 主流形态：论文精讲型(44%) + 编译+观点型(30%)
- 适用：**反面教材**（ZH 不该走纯论文精讲）
- 路径：`market/raw/competitor/gzh-accounts/PaperAgent/`

## 海外博主（5 位 / 67 篇，已 bundle 12 篇）

### Eugene Yan（8 篇，已 bundle 3 篇）★
- 主流形态：知识体系型(40%) + 业内复盘(25%) + 体感(25%)
- 适用：**B-knowledge-system**（首选国际参考）+ **A-firsthand**（业内复盘）
- 路径：`market/raw/competitor/overseas-bloggers/eugene-yan/`

### Hamel Husain（7 篇，已 bundle 2 篇）
- 主流形态：知识体系(15%) + 反主流(15%) + 工具评测(45%) + 个人踩坑(15%)
- 适用：**B-knowledge-system** + **A-firsthand**（反主流单点）
- 路径：`market/raw/competitor/overseas-bloggers/hamel-husain/`

### Ethan Mollick（19 篇，已 bundle 4 篇）★
- 主流形态：业内复盘 + 自创概念(47%) + 反主流单点(37%) + 实测 demo(10%)
- 适用：**A-firsthand**（业内复盘）+ **B-knowledge-system**（自创概念）
- 路径：`market/raw/competitor/overseas-bloggers/ethan-mollick/`

### Lilian Weng（3 篇，已 bundle 1 篇）
- 主流形态：知识体系综述(100%)，半年一篇 paper 级长文
- 适用：**B-knowledge-system**（天花板）
- 路径：`market/raw/competitor/overseas-bloggers/lilian-weng/`

### Simon Willison（30 篇，未 bundle）
- 主流形态：工具播报型(57%) + 编译评论(27%)
- 适用：**作素材源监控**，结构上不模仿（碎太碎）
- 路径：`market/raw/competitor/overseas-bloggers/simon-willison/`

### Drew Breunig（0 篇 — 占位）
- Context Engineering 这个词的主推之一，可后续补充

## extra-samples（已全部 bundle）

`market/raw/competitor/extra-samples/`（3 篇全部已 bundle 到 C-single-source/）

## 元数据 / 索引文件

- `content/topic_supply/market/raw/competitor/research-report.md` — 87 篇竞品 + 67 篇海外的 8 形态归类报告
- `knowledge_base/ai_pm_wiki/wiki_structure.json` — 飞书知识库结构（76 节点）
- `knowledge_base/ingest_state.json` — 已处理文件 MD5 索引
- `knowledge_base/lint_report.json` — 文档质量审计

---

## 添加新样本时

1. 选定要 bundle 的源文件（路径基于 `knowledge_base/`）
2. 复制到对应 `samples/X/` 目录，重命名为 `子模板_作者_标题.md`（短、可识别）
3. 更新对应 reference 文件的"参考文章"段（加新路径 + 学习点一句话）
4. 更新本文件 Part 1 索引（加路径 + 一句话说明）

**docx 转 md** | `textutil -convert txt -output 目标.md 源.docx`
