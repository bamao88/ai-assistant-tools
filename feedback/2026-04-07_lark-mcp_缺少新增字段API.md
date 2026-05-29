---
status: fixed
resolution: 迁移到官方 lark-cli，原生支持 +field-create，同时移除了自建 lark-mcp 和第三方 feishu-mcp
---

# lark-mcp 缺少"新增字段"API

## 工具
lark-mcp

## 问题简述
lark-mcp 当前只有 `bitable_v1_appTableField_list`（列出字段），没有"新增字段"的 API。飞书官方 API 支持 `POST /open-apis/bitable/v1/apps/:app_token/tables/:table_id/fields` 创建字段，但 lark-mcp 未封装此接口。

## 复现步骤
1. 调用 `bitable_v1_appTableField_list` 可以正常列出多维表格字段
2. 需要为已有表格新增字段时，找不到对应的 MCP 工具
3. 搜索所有可用工具，确认不存在 `field_create` 或类似命名的工具

## 期望行为
提供 `bitable_v1_appTableField_create` 工具，支持为已有多维表格新增字段（文本、单选、多选等类型）。

## 实际行为
只能列出字段，无法通过 API 新增字段，只能手动在飞书 UI 中操作。

## 影响场景
- 自动化运营流程中需要动态扩展表格结构
- 当前案例：需要为"选题池"表格新增"内容类型""修改意见""图片状态"三个字段

## 建议
封装飞书官方 `POST /bitable/v1/apps/:app_token/tables/:table_id/fields` 接口即可。
