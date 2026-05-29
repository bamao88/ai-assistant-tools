# tencent-video-publish 封面生成中阻塞

## 复现步骤

1. 使用有效视频号登录态运行 `upload-video`。
2. 传入 `--thumbnail` 自定义封面。
3. 页面上传视频后，右侧封面预览区域停留在“生成中 个人主页和分享卡片(3:4)”。

## 期望行为

发布工具不应长时间卡死；如果官方默认封面生成迟迟不结束，应在可控时间内给出明确错误或 warning，并且不点击保存草稿/发表。

## 实际行为

原流程会等待官方默认封面生成状态最多 600 秒，导致自动化发布链路看起来卡住。页面在该状态下手动封面入口不可用，点击 `vertical-cover-wrap` 不会弹出上传封面窗口。

## 日志片段

测试命令使用 `--fill-only --cover-timeout 10` 后返回：

```text
thumbnail_warning: official video cover generation is still stuck after 10s; current_status='生成中 个人主页和分享卡片(3:4)'
submitted: false
```

诊断文件：

- `/tmp/tencent_video_debug/locator_diag_20260528_173018.json`
- `/tmp/tencent_video_debug/page_20260528_173018.png`

## 后续定位

对照 `dreammis/social-auto-upload` 当前 `uploader/tencent_uploader/main.py` 和失败页面 bundle，视频号实际上传链路会使用：

- `finderpre.video.qq.com`
- `finder.video.qq.com`
- `wxapp.tc.qq.com`

这些域名不在原 route-bypass 白名单里，解析出的 `183.60.230.*`、`43.129.*`、`43.159.233.*`、`43.174.88.*` 在修复前走 `utun11` 代理出口。页面主体域名能正常打开，但视频上传/回源/官方封面生成链路可能仍走代理，导致封面一直停在“生成中”。

已把上述域名补入 `engines/route-bypass/domains.txt` 并刷新路由；后续重新扫码后继续验证。

## 复测与修复

2026-05-28 20:26 复测真实 15 秒素材时，视频 blob 已可读取，但页面 console 报：

```text
Creating a worker from 'blob:https://channels.weixin.qq.com/...' violates Content Security Policy
```

同时 `rhino_video.wasm` 多次中止，官方封面无法完成抽帧生成。已在视频号 engine 的浏览器 context 中启用 `bypass_csp=True`，并把 `aladin.wxqcloud.qq.com` 加入 route-bypass。

2026-05-28 20:33 再次使用同一素材运行：

```bash
cli.py --headed upload-video ... --thumbnail ... --fill-only --upload-timeout 180 --cover-timeout 240
```

结果：

```json
{
  "success": true,
  "action": "filled_ready_to_submit",
  "submitted": false,
  "thumbnail_warning": null
}
```

结论：官方封面生成已恢复，自定义封面上传成功，流程停在最终提交前。
