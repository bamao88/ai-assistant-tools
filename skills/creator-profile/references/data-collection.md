# 数据采集标准流程

teardown / benchmark / niche-mapping / hook-decoding 共用的数据采集步骤、CLI 命令、字段映射、限流处理。所有抓取**强制 `--account 测试号`**。

---

## 一、采集所需输入

每个待研究博主，需要从用户处或主页 URL 拿到：

| 字段 | 来源 |
|------|------|
| `user-id` | 博主主页 URL `https://www.xiaohongshu.com/user/profile/{user-id}` |
| `xsec-token` | 主页 URL query 参数 `?xsec_token=...` |

> ⚠️ `xsec-token` 有时效，**调研当天获取，不能复用历史值**。过期会返回空数据。

---

## 二、CLI 命令清单（实测可用）

CLI 入口：`python /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py`

### 步骤 1：拿博主主页 + 笔记列表

```bash
python cli.py --account 测试号 user-profile \
  --user-id <USER_ID> \
  --xsec-token <XSEC_TOKEN>
```

返回 JSON 结构包含：
- `nickname`, `desc`, `fans`, `follows`, `interaction`, `total_liked` …
- `feeds`: 该用户的笔记列表（含 `feed_id`, `title`, `liked_count`, `collected_count`, `comment_count`, `xsec_token`, `note_url` 等）

### 步骤 2：拿 Top N 笔记详情

按 `liked_count + collected_count` 降序排，取 Top 10-15：

```bash
python cli.py --account 测试号 get-feed-detail \
  --feed-id <FEED_ID> \
  --xsec-token <FEED_XSEC_TOKEN> \
  --load-all-comments \
  --max-comment-items 30
```

⚠️ 注意：参数名是 `--feed-id`（不是 `--note-id`）。每篇笔记有**独立的 xsec_token**，从 `user-profile` 输出的 `feeds[].xsec_token` 拿，不是复用主页的 token。

### 步骤 3（可选）：关键词搜索补充

赛道扫描或验证选题热度时：

```bash
python cli.py --account 测试号 search-feeds \
  --keyword "押金避坑" \
  --sort-by 最多点赞 \
  --publish-time 半年内
```

---

## 三、字段映射（CLI 输出 → 拆解 10 张表）

### 表1（基础信息）映射

| 表1 字段 | 来源 |
|---------|------|
| 粉丝数 | `user-profile` → `fans` |
| 作品数 | `user-profile` → `notes_count` 或 `len(feeds)` |
| 总点赞收藏 | `user-profile` → `total_liked + total_collected` |
| 起号时间 | 笔记列表中最早一篇的 `time` |
| 更新频率 | 近 30 天 `feeds[].time` 计数 |

### 表3（粉丝画像）映射

xhs CLI 不返回粉丝画像数据。粉丝画像通过以下方式**推断**（在报告中显式标记"推断"）：
- 评论区头像/昵称样本（取 Top 笔记的评论列表，n ≥ 30）
- 博主自述（简介/置顶）+ 主营选题反推目标人群

### 表9（爆款笔记）映射

| 表9 字段 | 来源 |
|---------|------|
| 笔记链接 | `feeds[].note_url` |
| 发布日期 | `feeds[].time` |
| 标题 | `feeds[].title` |
| 点赞/收藏/评论 | `feeds[].liked_count` / `collected_count` / `comment_count` |
| 互动率 | (赞+藏+评) / 粉丝数 × 100% |

---

## 四、限流与异常处理

| 现象 | 处置 |
|------|------|
| `get-feed-detail` 返回 `null` 或 401 | xsec_token 已过期 → 重新从 `user-profile` 输出里取最新 token |
| 连续 5 次请求后响应明显变慢 | 已被限流 → 暂停 60 秒再继续 |
| `user-profile` 返回 `fans=0` 但博主明显有粉丝 | 命中风控 → 切到无登录态 cookies 或换时段 |
| 笔记列表少于实际 | xhs 只暴露公开笔记，私密笔记不可见 → 直接接受 |

**节奏控制**：
- 同一博主连续抓取间加 `sleep 0.5`
- 切换博主之间加 `sleep 2`
- 总采集量超过 50 个 `get-feed-detail` 调用时，分两批，中间停 5 分钟

---

## 五、采集输出建议（中间产物）

把采集到的原始 JSON 落盘到临时目录，便于复算：

```
/tmp/creator-profile/<赛道名>_<日期>/
├── profile_<博主A昵称>.json
├── profile_<博主B昵称>.json
├── detail_<feed_id>.json
└── search_<关键词>.json
```

报告里**只引用结论 + 关键数字**，不要把原始 JSON 贴进报告。

---

## 六、合规与安全（强制）

1. **账号锁定**：所有命令必须带 `--account 测试号`。出现其他账号（如 `wxp-self`）立即停止，向用户报警。原因：调研属于读取/嗅探操作，会污染主账号的推荐画像。
2. **只读公开数据**：禁止在调研阶段调用 `post-comment` / `like-feed` / `favorite-feed` / `reply-comment`，避免被对方博主察觉。
3. **隐私底线**：报告不记录博主联系方式（评论区私信号、外链等），不暴露非公开商务报价。
4. **样本最小化**：单博主 `get-feed-detail` 调用不超过 20 次；横向对比时每博主 Top 10 即可。

---

## 七、采集阶段 checklist

进入分析前必须打勾：

- [ ] 已获取每个博主的 user-id + 当天有效 xsec-token
- [ ] 所有命令带 `--account 测试号`
- [ ] `user-profile` 成功返回（fans/feeds 非空）
- [ ] Top N 笔记的 `get-feed-detail` 成功率 ≥ 80%
- [ ] 原始 JSON 已落盘到 `/tmp/creator-profile/<赛道>_<日期>/`
- [ ] 未触发限流（响应时间 / 错误率正常）
- [ ] 未调用任何写操作命令

**任何 ✗ → 排查根因（token 过期 / 账号错误 / 限流）→ 修复 → 重抓，不要带病进入分析阶段。**
