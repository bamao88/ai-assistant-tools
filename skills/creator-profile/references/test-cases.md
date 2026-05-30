# 测试用例

用于跑通 creator-profile skill 各子能力的真实博主样本。每个用例记录：博主 URL、user-id、最近有效的 xsec-token（当天获取有效）、用途说明。

> ⚠️ xsec-token 有时效，**调研当天获取，不能复用历史值**。过期需重新从主页 URL 取。

---

## 测试博主 A（teardown 基准测试）

| 字段 | 值 |
|------|-----|
| 主页 URL | https://www.xiaohongshu.com/user/profile/59757acd50c4b45e6e9a90df |
| user-id | `59757acd50c4b45e6e9a90df` |
| xsec-token（首次录入 2026-05-30）| `ABTrryLjYJcucTxGK2_4zkOwONwwlru8bEfa0raV91yBw=` |
| 用途 | teardown 子能力的端到端冒烟测试博主 |
| 备注 | 从 PC 端搜索结果页复制 URL 获得 |

**采集命令（每次需用当天有效 token）**：

```bash
# 主页 + 笔记列表
python cli.py --account 测试号 user-profile \
  --user-id 59757acd50c4b45e6e9a90df \
  --xsec-token "<当天有效 TOKEN>"

# Top N 笔记详情（feed-id 和 xsec-token 从上一步输出的 feeds[] 取）
python cli.py --account 测试号 get-feed-detail \
  --feed-id <FEED_ID> \
  --xsec-token <FEED_XSEC_TOKEN> \
  --load-all-comments \
  --max-comment-items 30
```

---

## 新增测试用例格式

```markdown
## 测试博主 X（子能力 / 用途描述）

| 字段 | 值 |
|------|-----|
| 主页 URL | ... |
| user-id | `...` |
| xsec-token（录入日期）| `...` |
| 用途 | ... |
| 备注 | ... |
```
