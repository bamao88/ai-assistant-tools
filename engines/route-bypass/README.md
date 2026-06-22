# route-bypass

Route selected publishing hosts through the local Wi-Fi gateway while keeping the
rest of the Mac on the current Tailscale exit node. It is used before publishing
to Xiaohongshu and WeChat Channels so those platform requests do not leave via
the exit-node/proxy path.

This is a host-route helper with a small managed DNS fallback. It resolves
configured domains to current IPv4 addresses, then adds `/32` host routes
through the local gateway. For Xiaohongshu publish-critical hosts, it can also
write a marked `/etc/hosts` block using local-gateway DNS answers when the
system resolver is pinned to the Tailscale DNS path. Run it again when DNS
answers change.

## Usage

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply
```

Inspect current routes without changing anything:

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh status
```

Remove routes previously managed by this tool:

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh remove
```

Resolve only:

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh resolve
```

## Configuration

Default domains live in:

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/domains.txt
```

The default list currently includes:

- Xiaohongshu creator/publish hosts.
- Tencent Meeting web/MCP hosts and recording CDN hosts.
- WeChat Channels publish/login hosts and the Tencent Cloud media host observed
  during video publish flows.

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
  route table and the managed hosts block.
- Tailscale should have LAN access enabled when an exit node is active:
  `tailscale set --exit-node-allow-lan-access=true`.
- Only IPv4 is handled. The current Wi-Fi network has no IPv6 router, so this is
  sufficient for the verified setup.
