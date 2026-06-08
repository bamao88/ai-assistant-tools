# 今日头条无插件直传 Spike 结论

日期：2026-06-08

## 结论

本批不实现今日头条无插件直传。公开 `vendor/wechatsync` 仓库没有 `toutiao` adapter 源码，只能看到文档、manifest 和 content script 线索；实际适配大概率在 `packages/core/src/adapters/platforms/private` 私有 submodule 中。

## 已确认事实

- `packages/core/src/adapters/platforms/` 公开源码中没有 `toutiao.ts`。
- `.gitmodules` 指向 `packages/core/src/adapters/platforms/private`，远端为私有仓库 `wechatsync-private-adapters`。
- `packages/extension/src/content/toutiao.ts` 注释说明 content script 的 fetch 不会自动注入 `msToken/a_bogus`，需要 background 在 MAIN world 执行。

## 风险

今日头条草稿接口可能依赖浏览器页面上下文生成 `msToken`、`a_bogus` 或其它风控签名。若是这样，纯 Node Cookie 直传不稳定，不能和知乎/掘金/CSDN 同批承诺。

## 下一步

1. 在已登录头条号的浏览器中手动保存一篇草稿。
2. 用 DevTools Network 记录草稿保存、图片上传、草稿编辑 URL。
3. 确认请求是否需要浏览器实时生成 `a_bogus` / `msToken`。
4. 如果请求只依赖 Cookie + 固定 CSRF/header，再新增 `toutiao` direct adapter。
