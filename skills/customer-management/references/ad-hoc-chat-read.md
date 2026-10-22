# ad-hoc 读聊天 / 找人（私聊检索）

回答"谁私聊我领回放""谁要退差价"这类**跨人、自由检索**问题的入口。两个命令都**只读、0-LLM、不写盘、不联网**。

## 为什么有这节(背景)

代码迁移(散脚本 → tools 引擎)时,把"读某人解码聊天"的 agent 入口弄丢了:解码逻辑被收进
`capabilities/analyze/core.py`,只在 employment/profile 内部可达,7 个写回命令里没有"读聊天"。
干净 agent 没命令可用 → 直接读 raw `messages_user_*.json` → 撞上 zstd 压缩 hex → 误判"正文加密、卡住"。
本节的两个命令补回这个入口,`core` 也已能解压 zstd。

## 数据现实(关键,先记住)

- `content` 约 **9 成是明文**,直接可读。
- `28b52ffd…` 开头的 hex 是 **zstd 压缩,不是加密**。绝大多数(尤其 `type=1`)是**真人对话**(群发课程/回放链接、学员反馈、试听询问)。`core.normalize_messages` 已自动 `try_decode_zstd` 解压;只有解压出 `<…>` XML 的才是系统消息(归 `system`/L1,可忽略),真解不出的二进制才归 `control`。
- **`isSelf` 字段永远是 0,不可信**。方向(谁发的)靠 staff 名单(`staff_exclude.json` / `core.is_staff_sender`),命令已内置。
- 默认采集身份读取项目根 `config/customer-management.private.json` 的 `collection_account.wxid`（项目根解析见 SKILL.md）；raw 数据湖与图片容器都来自该账号。

## `search-chat`(跨人找候选)

```
python3 -m customer-management search-chat \
  --any <kw>...            # 关键词 OR 子串匹配（或 --regex <pat>）
  [--side any|from-them|from-staff]   # from-them=只看对方发的
  [--since YYYY-MM-DD] [--until YYYY-MM-DD]
  [--layer text|all]      # 默认 all（含解压出的 zstd 真消息；找回放/退差价务必 all）
  [--context N]           # 每条命中前后 N 条上下文（默认 1）
  [--limit-people N] [--max-hits-per-person N]
  [--format text|json]
```
输出:命中的人(昵称 + wxid)+ 解码片段。agent 据此再用 `read-chat` 钻进某人细看。

## `read-chat`(读某一个人)

```
python3 -m customer-management read-chat --wxid <wxid> \
  [--layer text|all]      # text=L0 文字层（默认）；all=含图片/语音/系统事件标记
  [--since/--until YYYY-MM-DD] [--format text|json] [--no-info-map]
```
输出:**信息地图**(各层计数 + 加好友日期 + 怎么取图)+ 时间序、角色标注的解码 transcript。

## 两个合成查询示例

下方日期与金额为合成演示参数，实际检索时换成用户指定的时间范围和待核对金额。

**Q「谁最近私聊要退差价」**
```
python3 -m customer-management search-chat --any 退差价 差价 退款 --side from-them --since 2026-01-01 --layer all
# 显式说"退差价/差价"的会直接命中；隐式表达(如"我是某个价格买的")改用金额关键词:
python3 -m customer-management search-chat --any 100 200 --side from-them --since 2026-01-01
# 命中者要核实付款金额 → 读图：
python3 -m capabilities.acquire.resolve_images --wxid <wxid>
```

**Q「谁转发海报领回放(训练营学员除外)」**
```
python3 -m customer-management search-chat --any 回放 领回放 录播 评测 海报 --side from-them --since 2026-01-01 --layer all
# 训练营学员除外 = 排除 all_student.json 里"学期"非空的人(用 read-chat/gather 交叉核对)
# "回复了回放还没出来" = 看对方那条之后助理是否回过"还没出来"(read-chat 看上下文)
```

## 注意

- `--layer all` 才包含解压出的 zstd 消息;`text` 与旧行为对齐(只 L0)。
- "训练营学员除外" / "差价金额" 等业务判断要联 `all_student.json`(`学期`/`累计有效消费金额`),命令只负责把聊天读出来。
- 仍是只读:跑完 `git status` 对数据仓应无改动。
