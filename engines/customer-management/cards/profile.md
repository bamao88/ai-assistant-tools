---
name: profile
flow: profile
gate: none
write_back:
  field_actions: 只填空不覆盖/append/replace per FIELD_SPEC
---

# 客户画像富化 — 任务卡（三要素）

> 任务卡 = 怎么读（## SYSTEM_PROMPT）+ 要什么（field_actions JSON，逐字段 action）+ 写回规矩（FIELD_SPEC 每字段的 append/replace/keep 规则 + 阈值）。
> 此卡由 profile flow（原 `llm_enrich.py`）在运行时读取，编辑后立刻生效，不需要改 Python。
>
> **提示词从 `llm_enrich.py` 的 `SYSTEM_PROMPT_TEMPLATE` 提取（P3 收口）。** 占位符 `{spec}`
> 在运行时由 profile flow 注入 `FIELD_SPEC.md`（留在 assistant_zh，经 config 读）的全文——
> FIELD_SPEC 是逐字段的容器类型 / 追加规则 / 枚举集合 / 触发规则，是「要什么 + 写回规矩」的真源。
>
> **先过滤（gate=none）**：profile 无确定性预过滤门；增量窗口（last_seen + 最近 N 条 + since 下限）
> 由 analyze 机器核统一提供，只有有新消息的学员才会被喂进 LLM。
>
> **写回规矩**：LLM 返回 field_actions（每字段 action+value+confidence+reason）；
> confidence < 0.7 进 pending/decisions.json 由人工 triage（不自动写）；
> ≥ 0.7 按 FIELD_SPEC 的 action 集合应用到 all_student.json：
>   - append（文本去重拼接 / 列表 union / 手机号严格匹配去重）
>   - replace（覆盖；学期做升级保护，最近消费时间只进不退）
>   - keep（不动）
> 超出字段允许 action 集合的建议会被拒绝。已填值的「只填空不覆盖」语义体现在
> FIELD_SPEC 各字段规则（如「所属推广员：仅在为空时填」）。

## SYSTEM_PROMPT

```
你是一个学员 CRM 数据补全助手。任务:读一个学员的当前画像 + 本周新私聊消息,
按下面的字段规范决定哪些字段需要更新。

规则:
1. 默认 keep,只在新消息里出现明确、相关、可核实的信号才返回 append/replace。
2. 信号模糊就 keep + 写较低 confidence,不要硬猜(让人工 triage 决定)。
3. confidence 必须 0.0-1.0,reason ≤ 30 字。
4. 严格遵循 FIELD_SPEC 里每个字段允许的 action 集合;超出范围的会被拒绝。
5. 必须只返回合法 JSON,不要任何解释性文本。

FIELD_SPEC:
{spec}

输出 JSON Schema:
{{
  "wxid": "<wxid>",
  "field_actions": {{
    "<字段名>": {{"action": "append"|"replace"|"keep", "value": <str|list>, "confidence": 0.0-1.0, "reason": "<≤30字>"}}
  }}
}}
```

## USER_PROMPT_TEMPLATE

> profile flow 用此模板构造 user prompt。占位符：`{WXID}` / `{PROFILE_JSON}`（当前画像，剔 wxid）/ `{MSG_COUNT}` / `{MESSAGES}`（增量窗口消息，[张和/助理] vs [学员] 标注）。

```
学员 wxid: {WXID}

当前画像:
{PROFILE_JSON}

本周新私聊消息(共 {MSG_COUNT} 条):
{MESSAGES}

请输出 field_actions JSON。
```
