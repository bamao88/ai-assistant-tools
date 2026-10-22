---
name: assistant_zh_topic-mine
description: |
  从张和的 client 新素材里做增量候选发现，默认写 `content/shared_candidates/YYYY-MM-DD_client-delta-HHMMSS.md`。
  这是保留旧口令习惯的稳定别名；候选层只是可选判断工件，不是正式写作前置。
  用户说"挖一轮选题"、"刷新候选"、"扫一下新素材里的选题"时触发；
  assistant_zh_knowledge-ingest 成功处理 client 新素材后也默认接这条链。
compatibility: Codex
allowed-tools:
  - Bash
  - Read
---

# assistant_zh_topic-mine

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


薄触发器。默认增量逻辑在 `content/candidate_discover.py`；只有显式要求全量重建时才回到 `content/candidate_mine.py`。

## 何时跑

| 触发场景 | 默认动作 |
|----------|------------|
| 用户只问“有什么选题可以写” | 不触发本 skill；先读 `content/candidates_index.md`，再按目标 persona 读最近的 `content/shared_candidates/*.md` 与 `content/<persona>/candidates/*.md` |
| 用户说"挖一轮选题/扫一下新素材" | `python3 -m content.candidate_discover` |
| 刚完成 assistant_zh_knowledge-ingest（client） | `python3 -m content.candidate_discover --from-ingest-report <report.json>` |
| 用户明确要“只扫这几个文件” | `python3 -m content.candidate_discover --files <path...>` |
| 用户明确说“全量重建候选池” | `python3 -m content.candidate_mine --source client` |

## 跑

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/assistant_zh
python3 -m content.candidate_discover
```

如果 assistant_zh_knowledge-ingest 刚写过结构化 report，用：

```bash
python3 -m content.candidate_discover --from-ingest-report /tmp/knowledge-ingest-report.json
```

如果用户明确要全量重建，再跑：

```bash
python3 -m content.candidate_mine --source client
```

增量发现会把候选写到 `content/shared_candidates/<today>_client-delta-<time>.md`。

## 报告

把 stdout 给用户讲清楚：
1. 本次扫了多少新素材
2. 提案阶段留下多少、聚合后写了多少候选
3. 候选文件路径（`content/shared_candidates/<today>_client-delta-<time>.md`），主动建议"要不要从这批里挑一条直接开写？"

如果新增 0，说明这批新素材没有新的 publish-worthy 命题，或者都已经被已有增量批次覆盖，这是正常的。

## 边界

- 不动 `knowledge_base/`（pipeline 自治）
- 不把 `content/topic_pool/` 当候选真源
- 默认是 client 增量发现，不是 market 全量扫描
- 用户没明确说全量重建时，不要默认跑 `content.candidate_mine --source client`
