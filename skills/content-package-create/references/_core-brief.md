# Core Brief 中间层

`core_brief.md` 是内容发布包制作的语义中间层：它不属于任何平台，不压字数，不按平台格式下料。

## 什么时候生成

用户要准备发布文案或要发布但还没有完整发布包时，先生成它：

- 裸 Markdown、视频、字幕、转写稿、口播切片目录。
- 用户说“准备标题 / 摘要 / 关键词 / 封面标题 / 发布物料”。
- 一稿多发。
- 已有某个平台发布包，但要新增另一个平台。

## 放在哪里

内容来自 item 目录时，放在同一目录：

```text
content/<persona>/items/<id>/core_brief.md
```

用户只给临时素材、还没有 item 目录时，先在对话里产出同样结构；一旦落盘发布包，就把 `core_brief.md` 一起落盘。

## 最小结构

```markdown
# Core Brief

## 来源
- 源稿：
- 内容形态：article | video | both
- 目标平台：

## 一句话核心判断
完整写清这条内容到底在讲什么，不压字数。

## 标题种子
- 完整句子 1
- 完整句子 2
- 完整句子 3

## 封面标题种子
- 可独立站住的封面文字 1
- 可独立站住的封面文字 2

## 发布页正文素材
- 关键场景：
- 工具名 / 方法名：
- 目标人群：
- 边界和反例：
- 可用金句：

## 关键词候选池
- 固定账号词：
- 主题词：
- 热点词（有来源才填）：

## 禁用内容
- 不确定数字：
- 不可写 CTA：
- 不可夸大的身份 / 承诺：
```

## 生成原则

小红书标题种子与主副标题配合，按 [标题写法](xiaohongshu-titles.md) 处理。种子数量按任务需要，不把结构示例中的数量当配额。

- 只读源稿一次，先形成统一核心判断。
- 标题种子必须是完整句子，不提前压到 20 字或 16 字。
- 每个平台从标题种子独立展开，不从另一个平台标题继续裁剪。
- 多平台时，闸门 A 展示 `核心判断 + 标题种子 + 封面标题种子` 给用户定调。
- 单平台或用户明确授权自动执行时，闸门 A 可自动通过，但仍要保留 `core_brief.md` 以供校验和复盘。

## 下游落盘

每个平台发布包仍按模板写：

```text
skills/platform-publish/assets/templates/publish_<platform>.md
```

落盘后先跑单文件校验：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check.py <publish_file> --platform <platform> [--form article|video]
```

多平台再跑集合校验：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/publish-prep/check_bundle.py <item_dir>
```
