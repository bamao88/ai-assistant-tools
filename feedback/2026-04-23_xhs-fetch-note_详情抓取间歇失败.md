# 2026-04-23 · xhs-fetch-note · 详情抓取间歇失败

## 现象
- 同一个测试号登录会话内连续调 `get-feed-detail` 3 次，全部返回 `{"success": false, "error": "没有捕获到 feed 详情数据"}`
- 测试的 feed_id / xsec_token 组合全都是同一小时内刚从 `search-feeds` 返回的，理论上有效
- 上午同一个会话同一账号调同类命令 2/6 成功（盛老师、666yt），另外 4 个也失败
- 不是 cookies 过期（其他 search-feeds / list-feeds 命令同时段正常）

## 复现步骤
1. `search-feeds --keyword "全白空间 白踢脚" --sort-by 综合` 返回 66 条
2. 挑 3 条不同 note 分别 `get-feed-detail --feed-id X --xsec-token Y`
3. 3 条全失败

## 猜测
- 详情页面可能需要更长的页面加载时间（video note 或长文容易超时）
- 或当前 Chrome 实例打开的 tab 已经被其他任务污染
- 或 xhs 侧对频繁详情请求做了节流（同账号连续请求）

## 期望
- 失败时返回更具体的原因（timeout / tab 失效 / 反爬识别）
- 或自动重试 N 次再报错
- 或加个 `--wait` 参数让调用方控制等待时间

## 影响
- 今天 C20260423_002 笔记素材阶段需要抓 2-3 张白踢脚参考图做白踢脚正面案例，3 次都失败 → 主 agent 放弃该图位，方案回退为 5 张纯 Ms.H 单图
