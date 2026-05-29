# xhs-publish-article: `long-article` 找不到"写长文" tab

**日期**：2026-04-21
**工具**：`/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/xhs/publish.py::_click_publish_tab`
**账号**：张和_专业号_小红书

## 复现步骤

1. `check-login` 返回 `logged_in: true`（xiaohongshu.com/explore 已登录）
2. 手动访问 `https://creator.xiaohongshu.com/publish/publish?source=official`，确认已登录并能看到"上传视频 / 上传图文 / 写长文"三个 tab
3. 执行 `long-article --title-file ... --content-file ...`

## 期望

找到并点击"写长文" tab，进入长文编辑器。

## 实际

抛出 `PublishError: 没有找到发布 TAB - 写长文`，尽管 debug 打印里页面上存在两个 `text: "写长文"` 的 `.creator-tab` 元素。

## 诊断线索（从 debug 信息里）

```
{"text":"写长文","html":"<div class=\"creator-tab\" button-hp-installed=\"1\" data-hp-kind=\"creator-tab-写长文\" aria-hidden=\"true\" tabindex=\"-1\" style=\"position: absolute; opacity: 1e-05; pointer-events: auto; inset: 0px auto auto 2..."}
{"text":"写长文","html":"<div data-v-1ff40f7c=\"\" data-v-0b179352=\"\" class=\"creator-tab\" data-hp-bound=\"1\"><span data-v-1ff40f7c=\"\" class=\"title\">写长文</span></div>"}
```

两个"写长文"元素：
- 第一个有 `aria-hidden="true"` + `opacity: 1e-05` + `pointer-events: auto`（像是引导/埋点覆盖层）
- 第二个是真实 tab，但它**没有 `data-hp-bound` 之外的显式可见性标记**

猜测：`_click_publish_tab` 的选择器可能只认 `creator-tab.active`，或者用 `[text()="写长文"]` 拿到第一个命中的 aria-hidden 隐藏元素，然后判定为"不可见 → 无有效 tab"并抛错。

## 建议修复方向

- 选择器过滤 `aria-hidden="true"` 的元素，或者优先选 `data-hp-bound="1"` 且未被 `aria-hidden` 的 `.creator-tab`
- 或直接用 `[data-v-1ff40f7c] .creator-tab:has(.title:contains("写长文"))` 这种 DOM 穿透的选择器

## 临时绕路

**手动点击**：用户在已开的 Chrome 窗口里手动点"写长文" tab，进入编辑器后，后续的 `long-article` 填写/`next-step` 流程在新的 URL 上可能正常（未验证）。或者整个发布流程走手动。
