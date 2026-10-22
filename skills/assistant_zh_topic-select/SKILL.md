---
name: assistant_zh_topic-select
description: |
  候选探索 skill。负责把素材收口到共享候选 `content/shared_candidates/*.md` 或目标 persona 的 `content/<persona>/candidates/*.md`，帮助 `main`
  判断哪些 topic 值得推进；不再负责 formalization 或 `content-spec.md`。
compatibility: Codex
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
---

# assistant_zh_topic-select

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


你只负责候选探索，不负责正式对象登记。

## 必读

1. `content/candidates_index.md` 与 `content/shared_candidates/README.md`
2. `knowledge_base/client/profile/boss-profile.md`
3. `knowledge_base/client/profile/account-positioning.md`
4. `knowledge_base/client/profile/topic-selection-principles.md`
5. `knowledge_base/client/profile/content-strategy.md`
6. `.agents/skill-data/assistant_zh_topic-select/memory-bank/strategy.md`

## 按需追加读取

- 若需要参考历史表现和近期数据反馈，再读 `.agents/skill-data/assistant_zh_topic-select/memory-bank/performance-insights.md`

## 候选探索的原则

- 第一轮只判断“值不值得写”，不判断“能不能做爆款”
- 优先找：一手观察、具体方法、工程/产品取舍、可复用框架
- 包装层（标题 hook、发布节奏、转化）只能在 shortlist 之后做 tie-break
- 默认不要把题目写成焦虑、打脸、喊口号
- 除非原始材料本身如此，否则不要预设“反共识”是最高价值
- 候选层主字段写 `topic`，表示选题陈述；`title_candidates` 才是工作标题方向

## 候选探索

- 先按 `content/candidates_index.md` 定位目标 persona，再读取最近的 `content/shared_candidates/*.md` 与 `content/<persona>/candidates/*.md`；默认增量发现写共享候选目录
- 如果用户只是问“有什么选题可以写/最近有什么题”，默认只读最近批次并做推荐，不默认重跑
- 如需按默认增量方式刷新，调用：

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/assistant_zh
python3 -m content.candidate_discover
```

- 如需只扫特定一批刚入库的素材，调用：

```bash
python3 -m content.candidate_discover --from-ingest-report /tmp/knowledge-ingest-report.json
```

- 只有用户明确说“全量重建候选池 / 回填旧素材”时，才调用：

```bash
python3 -m content.candidate_mine --source client
```

- 生成候选时，`topic` 要先写清“这篇文章写什么”；`selection_reason` 再回答为什么值得展开
- `title_candidates` 只写工作标题，不提前套小红书情绪模板
- 增量批次要把 `source_artifacts[]` 写进 frontmatter，作为已处理素材真源

## 交回 `main`

当用户明确要求“开始写”“直接写这个”“推进正式内容”时：

1. 停止候选层工作
2. 把已确定 topic 与 source_refs 交回 `main`
3. 由 `main` 直接进入 `生产`
4. 由 `main` 创建 `content_id`、最小 `state`、`draft.md`

## 禁区

- 不直接写 `draft.md`
- 不创建 `content-spec.md`
- 不登记 `content/content_index.yaml`
- 不把外部系统当真源
- 不把 `content/topic_pool/` 当候选真源
