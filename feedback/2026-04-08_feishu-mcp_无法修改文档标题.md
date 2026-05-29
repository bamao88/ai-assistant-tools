# feishu-mcp 无法修改文档标题

## 日期
2026-04-08

## 工具
feishu-mcp / batch_update_feishu_block_text

## 问题
用文档ID作为blockId尝试更新标题文本，返回 invalid param (1770001)。文档标题是特殊块，不能通过 batch_update_feishu_block_text 修改。

## 期望行为
支持修改文档标题，或提供 update_document_title 工具

## 实际行为
只能手动在飞书界面修改标题
