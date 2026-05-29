# xiaohongshu_skills — search-feeds / list-feeds 返回的 xsec_token 为空

**status: cannot-reproduce**
**处理日期: 2026-04-15**

## 结论（2026-04-15 复现验证）

**无法复现**。用 `张和_专业号_小红书` 账号实测，`search-feeds` 返回的 xsec_token 有正常值。

另测试了空 token 调用 `get-feed-detail` 的效果：页面能导航但 `__INITIAL_STATE__` 数据为空，说明 xsec_token 是必要参数。

之前添加的 workaround（`urls.py` 空 token 省略参数）已回滚。

**后续**：若测试号账号能复现，需单独排查该账号登录态或 Chrome 状态。

## 日期
2026-04-08

## 工具
xiaohongshu_skills / cli.py search-feeds, list-feeds

## 复现步骤
1. `cli.py --account '测试号_小红书' search-feeds --keyword '设计师黄姣 长沙 装修'`
2. `cli.py --account '测试号_小红书' list-feeds`

## 期望行为
返回的每个 feed 对象应包含有效的 xsec_token，用于后续 get-feed-detail 和 user-profile 调用

## 实际行为
所有 feed 的 xsec_token 字段为空字符串，导致无法获取笔记详情和用户主页

## 影响
无法批量下载用户笔记图片素材（需要 xsec_token 才能调用 get-feed-detail）
