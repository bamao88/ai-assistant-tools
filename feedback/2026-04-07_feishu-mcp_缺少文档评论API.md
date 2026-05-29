# feishu-mcp 缺少文档评论读取 API

## 工具
feishu-mcp

## 问题简述
feishu-mcp 当前没有读取/创建文档评论的 API。飞书官方支持 `GET /open-apis/drive/v1/files/:file_token/comments` 等评论相关接口，但 feishu-mcp 未封装。

## 复现步骤
1. 用户在飞书文档中通过划线评论功能添加了评论
2. Agent 需要读取这些评论来获取审核意见
3. 搜索所有 feishu-mcp 工具，找不到 comment 相关工具

## 期望行为
提供文档评论的读取和创建工具：
- 读取文档所有评论（含评论位置、内容、回复）
- 创建评论/回复评论

## 实际行为
无法通过 API 读取飞书文档评论，只能读取文档正文内容。

## 影响场景
- 内容审核流程中，审核者习惯用划线评论给出具体修改意见
- Agent 无法读取评论，导致需要用替代方案（在文档正文中写意见）

## 建议
封装飞书官方文档评论相关接口：
- `GET /drive/v1/files/:file_token/comments` — 获取评论列表
- `POST /drive/v1/files/:file_token/comments` — 创建评论
- `POST /drive/v1/files/:file_token/comments/:comment_id/replies` — 回复评论
