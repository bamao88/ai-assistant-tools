---
name: assistant_zh_knowledge-ingest
description: |
  把原始素材（会议/课程/辅导转录、WeChat JSON、docx/md/txt/html 文档、市场调研日报）入库到
  张和的知识库（knowledge_base/）。内部走 Kimi pipeline：extract（抽观点）→ decide（读整个 wiki 判合并/新建/跳过）→ apply（落盘）。
  用户说"入库这个文件"、"整理这份转录"、"把这个文档放进知识库"、"处理 raw/ 下的新文件"时触发。
compatibility: Codex
allowed-tools:
  - Bash
  - Read
  - Glob
---

# assistant_zh_knowledge-ingest

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


这是一个**薄触发器 skill**——真正的工作在 Python pipeline 里完成，你只需要调起来并把结果给用户讲清楚。

## 行为

### 0. 输入是 URL 还是本地路径？

**先判断用户给的是远程 URL 还是本地路径。** pipeline 只接本地文件，URL 要先下载。

#### 腾讯会议链接（`https://meeting.tencent.com/...` / `https://wemeet.qq.com/...`）

1. 读取并调用通用 `platform-fetch` 的 `references/tencent-meeting.md`，按当前官方 MCP 路线获取逐字稿；采集身份与权限沿用该 reference。不要调用已退役的 `tools/tencent_meeting_downloader/` 路径，也不把 legacy 下载器当默认入口。
2. 逐字稿先存入本项目 `tmp/tencent_downloads/<timestamp>/` staging，保留来源 URL、会议身份和采集结果；只把成功取得的原始逐字稿 `.md`/`.txt` 放入 `knowledge_base/client/raw/meeting/`，不覆盖同名原件。
3. JSON 备份、索引、失败报告、诊断与视频留在 staging，不作为知识正文入库；失败项按采集结果说明，不编造原文或混成成功。
4. 把每份已取得的正文绝对路径交给下面 Step 1，继续完成本次入库。转录文件仍需 Step 2 的 cohort/scene 元信息；采集完成不是本任务结束。

#### 飞书妙记 / 会议链接

从已安装的 `lark-vc` 入口与当前 Minutes reference 取得原始文字记录，保持来源身份与权限；只需逐字稿时不以 AI 总结代替。将原文和来源标记保存到本项目 staging，再按上面的原件规则放入适当 raw 目录并回到 Step 1。不得凭记忆拼未注册的旧 Skill 或 CLI 命令。

#### YouTube / B站 / 小红书视频 / 抖音 / 本地音视频

读取并调用 `video-content` 获取逐字稿或字幕，按该 Skill 的当前采集/转录 reference 执行；只做本次入库需要的素材获取，不自动替用户启动研究报告或写作。拿到原始文字后，保存来源 URL、作者与转录方式，回到 Step 1 继续本次入库。不能把“请用户先自己下载”当成默认交付，也不调用已退役的 `video-research` Skill 名。

#### 其他网页 / 封闭平台资料

网页原文用当前网页读取能力；封闭平台原文从 `platform-fetch` 及其目标平台 reference 进入。先取得可追溯的本地正文，再交 pipeline；采集受账号权限或来源可用性阻塞时，明确缺哪份原文与恢复条件，不编造正文。

### 1. 判断目标文件

用户通常会给出：
- 一个路径（绝对或相对）→ 直接用
- 一个描述（"今天新收的转录"）→ `python -m workflow.knowledge_ingest run --list` 找候选，再确认
- 什么都没给 → 先 `--list` 看有没有待处理的

### 2. 转录素材的元信息补全（仅 scene 路径）

若目标是 `client/raw/meeting/` 下的转录，且文件名不符合协议 `YYYY-MM-DD_<cohort>_<scene>_<title>.txt`：

1. 先检查同名 sidecar `<文件名>.meta.json` 是否存在
2. 没有则问用户：cohort（c1/c2/c3/...）和 scene（theory_course/coaching/meeting/interview/other）
3. 把答案通过 `--cohort X --scene Y` 参数传给 pipeline；**不要**擅自改文件名

用户明确说"无所谓"、"你猜" → 直接跑，pipeline 会走 fallback 并在 lint 里标出来。

### 3. 判断生产 vs 测试

**默认走生产** —— 用户说"入库"就是真入库。

**下面任一情况改走 sandbox**（不污染真实 wiki）：
- 用户明说"测试"、"试一下"、"先跑一下看看"、"演练"、"不确定"
- 文件是从 tmp/、Downloads/ 等明显临时位置
- 用户在试新 prompt、新 decide 规则、验证 pipeline 行为
- 连续多份素材里有 1-2 份你不确定是不是要真入库

**不知道是生产还是测试 → 直接问用户一句话**，别猜。

### 4. 调 pipeline

**生产**：
```bash
cd /Volumes/ExtSSD2601/AI_Assistant/assistant_zh
REPORT=/tmp/knowledge-ingest-report.json
python3 -m workflow.knowledge_ingest run --file <绝对路径> [--cohort cX] [--scene Y] [--source 类型] --report-file "$REPORT"
```

**Sandbox**（同参数，换 `sandbox run`，会自动 init 快照）：
```bash
cd /Volumes/ExtSSD2601/AI_Assistant/assistant_zh
python3 -m workflow.knowledge_ingest sandbox run --file <绝对路径> [--cohort cX] [--scene Y] [--source 类型] --report-file /tmp/knowledge-ingest-sandbox-report.json
# 跑完看差异
python3 -m workflow.knowledge_ingest sandbox diff
# 满意就扔掉 sandbox；不满意也扔掉
python3 -m workflow.knowledge_ingest sandbox clean
```

**Dry-run**（只想看 decide 判决不落盘，**仍会调 Kimi**）：
```bash
python3 -m workflow.knowledge_ingest run --file <path> --dry-run
```

source 自动嗅（路径推断）：
- `client/raw/meeting/`  → `transcript`
- `client/raw/chat/`     → `wechat`
- `client/raw/*`         → `document`
- `market/raw/`          → `market`（实际上建议走 `market` 子命令，不走 `run`）

自动嗅不准时加 `--source` 显式指定。

### 4. 报告

解析 stdout：
- `extracted N viewpoint(s)`
- `applied=X  pending=Y`
- `report → /tmp/...json`
- 有 `fallback` warning → 转达给用户（"文件名没带协议/sidecar，建议下次补上"）

**若 pending > 0**：主动提示用户"有 Y 条待决策，要不要现在 `assistant_zh_knowledge-triage` 处理？"——这些条目是 Kimi 拿不准的，需要人判断。

**若是生产模式 + sink=client + 非 dry-run + report 里有成功处理的文件**：默认继续执行一轮增量候选发现，不要等用户再提醒：

```bash
python3 -m content.candidate_discover --from-ingest-report "$REPORT"
```

只有 `market`、`sandbox`、`dry-run` 三种情况，不接后续候选发现。

### 5. 失败处理

- **缺 KIMI_API_KEY**：提示用户检查 `knowledge_base/.env`；不尝试其他方案
- **extract/decide Kimi 调用失败**：stdout 会标明，把错误原话给用户，别重试
- **apply 失败**：pipeline 自动降级到 pending，继续处理剩下的观点，不中止

## 边界

- 不直接读文件内容自己判断主题 → 那是 pipeline 的工作，你只管调度
- 不手写 wiki 页 → apply.py 已经按 schema 处理，你改了就破坏 frontmatter/log
- 不处理 market 源走 `run` 子命令 → 用 `market` 子命令（先读 `knowledge_base/AGENTS.md` 和本项目 `workflow/knowledge-management.md` 的市场入库合同）
- 遇到 pending 不要代用户决策 → 引导到 `assistant_zh_knowledge-triage`
- 不直接把 URL 传给 pipeline — pipeline 只接本地路径，先走 Step 0 下载
- 下载产物的 `summary.json` / `manifest.json` / `failures.json` / `.json` 段落备份 本身不入库，留 staging 追溯用
- 采集临时产物先放 staging，再只将来源明确的原始正文放进相应 raw 目录；原件同名时先核对，不能覆盖
- 采集失败按当前 adapter 报告说明；日志不能包含凭据，未取得正文的项目不能进入知识 pipeline
