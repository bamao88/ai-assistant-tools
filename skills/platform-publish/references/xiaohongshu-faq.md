# 小红书发布 · 常见问题 / 踩坑速查

> 实战中反复栽过的坑。发布前扫一遍；发布卡住先回这张表对症，别凭直觉绕。
> 真源命令与流程在 `xiaohongshu.md`，本文件只补「为什么 / 怎么不再犯」。

---

## ⚠️ #1 默认前置：publish-network-preflight apply（漏了它，后面大概率卡上传）

**症状**：视频/图片一直传不上去；上传卡死、转圈、超时；表面看是「网络慢」或「小红书抽风」，反复重试都不行。

**真因**：这台机器整机走 **Tailscale 海外出口**。小红书上传入口和分片 CDN（`ros-upload.xiaohongshu.com` / `ros-upload-d*.xhscdn.com`）只要有一部分掉到 exit node，就会出现上传 0%、卡死或极慢。页面能打开、能填字，唯独上传那一步失败——所以最容易误判成别的问题，绕一大圈。

**解法（默认发布网络模式 `local-egress` 下发布前先跑）**：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh xiaohongshu apply
```

把小红书相关 IP 和已观测上传 CDN 网段钉到本地网关出口；当 Tailscale DNS 把 `www.xiaohongshu.com` / `ros-upload.xiaohongshu.com` 解析到坏边缘时，`route-bypass` 还会写一个带 BEGIN/END 标记的受控 `/etc/hosts` 块，改用本地网关 DNS 返回且可连接的边缘。**这一步通了，视频/图片秒传，后面标题/正文/标签/定时/封面才会一路顺。** 无 TTY 报 `sudo: a password is required` 时走 `osascript ... with administrator privileges` 兜底（见 `xiaohongshu.md`「网络分流前置步骤」）。小红书 IP 或上传边缘变化时，重复运行同一条 `publish-network-preflight`，它会重新解析当前 IP 并刷新受控 hosts；不要手工猜 IP。

如果总入口已锁定 `current-egress`（用户明确要求“不走本地流量 / 跳过本地分流 / 直接走当前网络”），本条作为风险提示，不再强制阻断；小红书视频 CLI 命令前加 `PLATFORM_PUBLISH_NETWORK_MODE=current-egress`，也可同时加 `--skip-route-bypass`。

**自检**：不要只看 `ping ros-upload.xiaohongshu.com`。上传分片可能走 Akamai/Tencent 的轮换边缘 IP，单域名 ping 正常也可能上传 0%。必须看完整路由校验：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh xiaohongshu status
```

`route decisions for route target IPv4` 中任意小红书主页、创作者中心或上传 IP 出现 `interface=utun*` 或 `destination=default`，都说明分流没生效，别往下走。CLI 还会实际探测 `https://www.xiaohongshu.com/explore` 和 `https://ros-upload.xiaohongshu.com/`；只看路由表不够，因为系统 DNS 曾把上传根域解析到 `43.159.95.157`，虽然路由走 `en1` 但 TCP 超时，导致上传 0%。2026-06-22 已观测到会导致上传 0% 或页面打不开的边缘包括 `23.59.252.*`、`96.7.244.*`、`184.27.185.*`、`212.129.158.241`、`43.159.95.157`。

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

## #4 封面：视频发布必须走引擎内置封面步骤

视频发布时 `--cover` 是必填项。正常流程直接用 `fill-publish-video` / `publish-video --cover ...`，引擎会在同一个发布页完成 **修改封面 → 上传 → 确定 → 等待发布按钮可点**。不要再调用 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/tmp/...` 下的临时封面脚本。

---

## #5 验证发布流程：测试用 fill；正式发布才用一键入口

要验证「能不能发出去」时，跑到填表（`fill-publish` / `fill-publish-video` / 长文走到 `next-step` 发布页）即可，测试号演练不点击最终发布。

- 测试 / 验证 / 演练 = 走到发布页、确认按钮可点就停，报告「测试通过」。
- 用户明确确认正式发布/定时发布，且测试号稳定性门槛已满足后，视频可逐条使用 `publish-video` 一键正式入口。多条笔记是队列，不是并发；一条成功并写状态后才进入下一条。
- 用户中途取消 → 必须 `save-draft`，不要直接关 tab。

---

## 一句话排查顺序

传不上去 → 如果本次是默认 `local-egress`，**先看 #1（publish-network-preflight status 不能走 `utun*`，CLI host probe 必须通过）**，九成是它 → 再看 #2 路径是不是软链 → 都没问题再怀疑登录态 / 平台本身。若本次按用户要求走 `current-egress`，先汇报当前网络出口可能是上传失败原因，再决定是否切回默认本地分流复测。
