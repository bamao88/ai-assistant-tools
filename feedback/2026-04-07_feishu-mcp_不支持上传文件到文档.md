# feishu-mcp 不支持上传非图片文件到文档

## 日期
2026-04-07

## 工具
feishu-mcp / batch_create_feishu_blocks + upload_and_bind_image_to_block

## 问题
- `batch_create_feishu_blocks` 的 blockType 只支持 text/code/heading/list/image/mermaid/whiteboard，没有 file 类型
- `upload_and_bind_image_to_block` 只能上传图片（png/jpg），不支持 xlsx/pdf/docx 等文件
- 导致无法通过 API 将附件（如 Excel 模板）插入飞书文档

## 期望行为
- 支持 file blockType，可以创建文件块
- 或者提供 upload_file_to_document 工具，支持上传任意文件类型到文档

## 实际行为
只能手动打开飞书文档拖入文件

## 场景
为小红书笔记生产流程中，需要将 Excel 模板附件一起放入飞书云文档供审核
