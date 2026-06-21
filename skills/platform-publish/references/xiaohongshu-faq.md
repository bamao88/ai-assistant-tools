# 小红书发布 · 常见问题 / 踩坑速查

> 实战中反复栽过的坑。发布前扫一遍；发布卡住先回这张表对症，别凭直觉绕。
> 真源命令与流程在 `xiaohongshu.md`，本文件只补「为什么 / 怎么不再犯」。

---

## ⚠️ #1 强制前置：route-bypass apply（漏了它，后面全白搭）

**症状**：视频/图片一直传不上去；上传卡死、转圈、超时；表面看是「网络慢」或「小红书抽风」，反复重试都不行。

**真因**：这台机器整机走 **Tailscale 海外出口**。小红书上传入口和分片 CDN（`ros-upload.xiaohongshu.com` / `ros-upload-d*.xhscdn.com`）只要有一部分掉到 exit node，就会出现上传 0%、卡死或极慢。页面能打开、能填字，唯独上传那一步失败——所以最容易误判成别的问题，绕一大圈。

**解法（发布前必跑，不是可选项）**：

```bash
tailscale set --exit-node-allow-lan-access=true 2>/dev/null || true
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply
```

把小红书相关 IP 和已观测上传 CDN 网段钉到本地网关出口，上传域名才通。**这一步通了，视频/图片秒传，后面标题/正文/标签/定时/封面才会一路顺。** 无 TTY 报 `sudo: a password is required` 时走 `osascript ... with administrator privileges` 兜底（见 `xiaohongshu.md`「网络分流前置步骤」）。

**自检**：不要只看 `ping ros-upload.xiaohongshu.com`。上传分片可能走 Akamai/Tencent 的轮换边缘 IP，单域名 ping 正常也可能上传 0%。必须看完整路由校验：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh status \
  creator.xiaohongshu.com edith.xiaohongshu.com \
  ros-upload.xiaohongshu.com ros-upload.xhscdn.com \
  ros-upload-d1.xhscdn.com ros-upload-d2.xhscdn.com ros-upload-d3.xhscdn.com ros-upload-d4.xhscdn.com \
  ros-upload-d5.xhscdn.com ros-upload-d6.xhscdn.com ros-upload-d7.xhscdn.com ros-upload-d8.xhscdn.com
```

`route decisions for route target IPv4` 中任意上传 IP 出现 `interface=utun*` 或 `destination=default`，都说明分流没生效，别往下走。2026-06-22 已观测到会导致上传 0% 的边缘包括 `23.59.252.*`、`184.27.185.*`、`212.129.158.241`。

页面停留超过 ~30 分钟再点发布前，重跑一次 apply（路由会过期）。

---

## #2 上传要传「软链解析后的真实文件」

媒体文件常是软链（symlink）。**直接把软链路径喂给上传，引擎解析失败或传空。** 先解析成真实路径再传：

```bash
realpath "<可能是软链的路径>"   # 用解析后的真实绝对路径去 --video / --images
```

所有路径一律绝对路径；不要在命令行内联中文文件名，写临时文件更稳。

---

## #3 标题：按 ✅ 拍板的那条选，别自己改

标题从已确认（✅ 拍板）的候选里取，不临场改写、不机械截断。只有「超过 20 单位必须压缩」时才按语义重写到 19–20 单位（规则见 `xiaohongshu.md` 标题检查）。封面文字≠笔记标题，可分开，但都不要凭空造。

---

## #4 封面：用「已经开着的发布页」那一步改，别动引擎

改封面走当前浏览器页面的原生交互：**修改封面 → 上传 → 确定**，在已打开的发布页上点。不要试图用 CLI/引擎重走一遍封面逻辑，会和页面状态打架。

---

## #5 验证发布流程：用 fill，**永远不点发布**

要验证「能不能发出去」时，跑到填表（`fill-publish` / `fill-publish-video` / 长文走到 `next-step` 发布页）即可，**绝不调用 `click-publish` / `publish` / `publish-video`**。

- 测试 / 验证 / 演练 = 走到发布页就停，报告「测试通过」。
- 图文/视频的真实发布由**用户手动点**发布按钮；只有长文「正式模式」按 `xiaohongshu.md` 明确放行才自动 `click-publish`。
- 用户中途取消 → 必须 `save-draft`，不要直接关 tab。

---

## 一句话排查顺序

传不上去 → **先看 #1（route-bypass status 所有上传目标都不能走 `utun*`）**，九成是它 → 再看 #2 路径是不是软链 → 都没问题再怀疑登录态 / 平台本身。
