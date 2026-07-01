# route-bypass

Route selected hosts through the local Wi-Fi gateway while keeping the rest of
the Mac on the current Tailscale exit node. This helper is retained for
transcription and historical diagnostics. `platform-publish` no longer uses it
as a publishing preflight.

This is a host-route helper with a small managed DNS fallback. It resolves
configured domains to current IPv4 addresses, then adds `/32` host routes
through the local gateway. For configured hosts, it can also write a marked
`/etc/hosts` block using local-gateway DNS answers when the system resolver is
pinned to the Tailscale DNS path. Run it again when DNS answers change.

## Usage

The `video-slicer` transcription line uses the platform wrapper
with platform `transcribe` to pin the **whole** transcription path to the local
gateway before each transcription — domestic ASR API hosts (Volcengine / Aliyun) AND
the public upload stations (`uguu.se` / `0x0.st`), so "upload the audio to a public
host" also egresses locally. This mirrors the manual "turn off the proxy" path that
works, without actually disabling the VPN. (OSS hosts are pinned too but the OSS
channel is disabled — credentials expired 2026-06.) Its CLI
(`engines/video-slicer/video_slicer/transcribe/cli.py`) runs this automatically:

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh transcribe apply
```

`apply` is intentionally safe to rerun. It resolves the current platform IPs
again, adds any newly returned IPs to the local gateway route set, applies
platform static network routes when configured, and refreshes managed hosts when
a platform needs that fallback. If edge IPs change, run the same `apply` again;
do not hand-edit `/etc/hosts` or add ad hoc routes.

When there is no interactive TTY, the helper falls back to macOS
`osascript ... with administrator privileges` so Codex/Claude sessions can still
show the normal administrator authorization window instead of failing with
`sudo: a password is required`.

Inspect current routes without changing anything:

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh transcribe status
```

Resolve only:

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh transcribe resolve
```

The lower-level helper remains available for debugging:

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply
```

Remove routes previously managed by this tool:

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh remove
```

## Configuration

Default domains live in:

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/domains.txt
```

The default list currently includes:

- Xiaohongshu creator/publish hosts.
- WeChat Channels publish/login hosts and the Tencent Cloud media host observed
  during video publish flows.
- WeChat Official Account draft/publish API and cover image hosts.
- Bilibili and Douyin creator/login/submit hosts. Douyin also has static `/24`
  network routes for observed creator/CDN edge ranges because its DNS answers
  can rotate immediately after a host-route apply.
- Zhihu, Juejin, CSDN, Baijiahao, SegmentFault, and Toutiao article draft hosts.
- Tencent Meeting web/MCP hosts and recording CDN hosts.
- Cloud transcription (video-slicer) hosts (platform `transcribe`): Volcengine
  `openspeech.bytedance.com`, Aliyun `dashscope.aliyuncs.com`, the public upload
  stations `uguu.se` / `0x0.st`, and the OSS upload endpoints (OSS channel disabled —
  credentials expired 2026-06).

The script uses `Wi-Fi` by default. Override when needed:

```bash
XHS_ROUTE_SERVICE="Ethernet" ./scripts/xhs-route-bypass.zsh apply
```

State is stored outside the repo:

```text
~/.xhs-route-bypass/managed-ips.txt
~/.xhs-route-bypass/managed-nets.txt
```

The managed hosts block is written directly in `/etc/hosts`:

```text
# BEGIN xhs-route-bypass managed hosts
...
# END xhs-route-bypass managed hosts
```

Do not add manual one-off hosts entries for publishing domains. Use `apply` to
refresh the block and `remove` to delete it.

## Notes

- `apply` and `remove` need administrator privileges because they edit the macOS
  route table and the managed hosts block. In non-interactive shells, confirm the
  macOS administrator authorization dialog when it appears.
- Tailscale should have LAN access enabled when an exit node is active:
  `tailscale set --exit-node-allow-lan-access=true`.
- Only IPv4 is handled. The current Wi-Fi network has no IPv6 router, so this is
  sufficient for the verified setup.
