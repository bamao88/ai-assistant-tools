---
status: fixed
---

# publish_long_article.py 两个持续复现的 Bug

**日期**: 2026-04-03
**工具**: xiaohongshu_skills / publish_long_article.py
**报告者**: assistant_zh
**严重程度**: 高（每次长文发布都会触发，需要人工手动修复）

---

## Bug 1：描述文本未正确填入

### 复现步骤

1. 执行 `next-step --content-file /tmp/xhs_la_desc.txt --images ... --topics ...`
2. 描述文件内容 279 字

### 期望行为

发布页描述框完整填入 279 字描述文本

### 实际行为

日志显示 "已填写发布页描述（279 字, 实际 122 字）"，但实际页面上描述区域为空，只有标题和话题标签。

### 日志片段

```
2026-04-03 16:28:21,586 WARNING xhs.publish_long_article: 等待描述框超时，继续尝试
2026-04-03 16:28:21,588 INFO xhs.publish_long_article: 已填写发布页描述（279 字, 实际 122 字）
```

### 根因分析

1. **等待和填充使用了不同的 selector**：
   - 等待阶段：`p[data-placeholder*="输入正文描述"]`
   - 填充阶段：`div.tiptap.ProseMirror`
   - 这是两个不同的元素，等待超时后直接用错误的元素填充

2. **`execCommand('insertText')` 对 ProseMirror/TipTap 编辑器不可靠**：
   - 小红书发布页用的是 TipTap（基于 ProseMirror）富文本编辑器
   - `execCommand` 可能被编辑器拦截或部分执行
   - 导致 279 字只插入了 122 字，甚至可能插入到了错误的位置

3. **没有校验实际插入结果**：
   - 返回值是 `el.textContent.length`，即使插入失败也可能返回已有内容的长度
   - 没有对比输入长度和实际长度来检测失败

### 建议修复

- 填充前先 focus + click 目标元素，确保光标在正确位置
- 改用 ProseMirror 兼容的插入方式：`dispatchEvent(new InputEvent('insertText', {data: text}))` 或直接操作编辑器的 state/transaction
- 参考 `publish.py` 中普通图文发布的描述填充逻辑（第 371-401 行使用了 `[role='textbox']` selector）
- 插入后校验 `textContent` 是否包含预期内容，不匹配则重试

---

## Bug 2：长文模板占位首图未删除

### 复现步骤

1. 先执行 `long-article` 填写长文（自动选择模板，模板会生成一张占位封面图）
2. 再执行 `next-step --images card_00_cover.png card_01.png ...` 上传 8 张卡片图

### 期望行为

删除模板生成的占位首图，替换为上传的 8 张卡片图

### 实际行为

占位首图保留，8 张卡片图追加在后面，共 9 张图。用户需要手动删除第 1 张。

### 日志片段

```
2026-04-03 16:28:31,697 INFO xhs.publish_long_article: 封面区域已加载，初始图片 0 张
2026-04-03 16:28:42,773 INFO xhs.publish_long_article: 已删除 0 张旧图片（初始 0 张）
2026-04-03 16:28:44,777 INFO xhs.publish_long_article: 封面图片替换完成，最终 1 张（目标 8 张）
```

### 根因分析

1. **初始图片检测 selector 不匹配**（第 206 行）：
   ```python
   init_count = page.evaluate("document.querySelectorAll('.close-btn').length") or 0
   ```
   长文模板生成的占位图的删除按钮可能不是 `.close-btn` class（可能是 `.delete-btn`、`.remove-btn` 或其他），导致 `init_count = 0`

2. **删除逻辑在 init_count=0 时直接跳过**（第 271-272 行）：
   ```python
   if deleted_count >= init_count:  # 0 >= 0 → True，立即 break
       break
   ```
   因为检测到 0 张初始图片，删除循环直接退出，什么都没删

3. **没有 fallback 检测机制**：只依赖 `.close-btn` 一个 selector，没有尝试其他可能的按钮 class 或用 `<img>` 标签数量做交叉验证

### 建议修复

- 在浏览器中 inspect 长文模板占位图的 DOM 结构，确认删除按钮的实际 class
- 增加 fallback selector 列表：`.close-btn, .delete-btn, .remove-btn, [class*="close"], [class*="delete"]`
- 用图片元素数量（`img` 标签或 `.image-item` 等）做交叉验证，不要只依赖按钮 class
- 修复删除逻辑：即使 init_count=0，上传后如果发现总图片数 > 目标数，也应该尝试删除多余的图片
- 增加初始检测超时时间（当前 10 秒可能不够模板渲染）

---

## 影响范围

这两个 bug 在**每次长文发布流程中都会触发**，需要用户手动：
1. 删除第 1 张占位图
2. 手动粘贴描述文本

已确认在 2026-04-03 的发布中复现。
