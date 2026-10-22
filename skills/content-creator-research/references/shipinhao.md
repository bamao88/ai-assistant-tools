# 微信视频号账号研究

支持公开账号定位、作品列表、详情与可见评论；命令、账号映射、分页字段和诊断真源见 [视频号采集 reference](../../platform-fetch/references/shipinhao.md)。只在本次研究涉及视频号时读取。

先确认搜索结果中的 `username` 与目标账号一致，再分页读取作品；昵称不能代替账号标识。当前 CLI 入口位于 `engines/wechat-channels-fetch/scripts/cli.py`，使用 `engines/tencent-video-publish/.venv/bin/python`。测试账号映射按现行 reference 解析，不将小红书的 slot 名照搬到视频号。

保留 `object_id`、`nonce_id`、描述、发布时间、媒体类型、平台公开互动指标和原始响应位置。需要正文、画面或讲述结构时读取作品实际内容；列表描述和封面不能替代完整视频。字幕/关键帧按平台采集的视频分支补齐，不因本次账号研究而自动剪辑成片。

分页是否结束以响应证据为准；`--max-pages`、`--limit` 是执行范围，不证明历史完整。账号、接口、登录或权限错误按诊断结果处理；不复制 Cookie、不更改发布账号配置，不使用互动或上传命令。
