#!/usr/bin/env python3
"""
从运行中的 Chrome (CDP) 导出 cookies 为 Playwright storageState 格式
不需要解密，直接从 CDP 获取明文 cookies
"""
import json, socket, struct, base64, time, urllib.request, os

CDP_PORT = 9222
OUTPUT = "/Volumes/ExtSSD2601/AI_Assistant/tools/var/state/storage_state.json"

def ws_connect(ws_url):
    from urllib.parse import urlparse
    p = urlparse(ws_url)
    s = socket.create_connection((p.hostname, p.port or 80))
    key = base64.b64encode(b"exportcookies123").decode()
    s.send((f"GET {p.path} HTTP/1.1\r\nHost: {p.hostname}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
    buf = b""
    while b"\r\n\r\n" not in buf: buf += s.recv(4096)
    return s

def ws_send(s, mid, method, params=None):
    msg = json.dumps({"id": mid, "method": method, "params": params or {}}).encode()
    n = len(msg)
    hdr = bytes([0x81, 0x80|(n if n<126 else 126)]) + (struct.pack(">H",n) if n>=126 else b"")
    s.send(hdr + bytes(4) + msg)

def ws_recv(s, timeout=10):
    s.settimeout(timeout)
    try:
        h = s.recv(2)
        if not h: return None
        b1, b2 = h
        n = b2 & 0x7f
        if n == 126: n = struct.unpack(">H", s.recv(2))[0]
        elif n == 127: n = struct.unpack(">Q", s.recv(8))[0]
        if b2 & 0x80: s.recv(4)
        d = b""
        while len(d) < n:
            chunk = s.recv(min(65536, n-len(d)))
            if not chunk: break
            d += chunk
        return json.loads(d)
    except: return None

def export_cookies_via_cdp():
    # 获取浏览器级别的 target
    version = json.loads(urllib.request.urlopen(f"http://localhost:{CDP_PORT}/json/version").read())
    browser_ws = version.get("webSocketDebuggerUrl")
    if not browser_ws:
        print("无法获取浏览器 WebSocket URL")
        return

    s = ws_connect(browser_ws)

    # 使用 Storage.getCookies 获取所有 cookies
    ws_send(s, 1, "Storage.getCookies")

    deadline = time.time() + 10
    while time.time() < deadline:
        r = ws_recv(s, 5)
        if r and r.get("id") == 1:
            cookies_raw = r.get("result", {}).get("cookies", [])
            break
    else:
        print("超时")
        s.close()
        return

    s.close()

    # 转换为 Playwright storageState 格式
    cookies = []
    for c in cookies_raw:
        cookies.append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "expires": c.get("expires", -1),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False),
            "sameSite": c.get("sameSite", "None")
        })

    state = {"cookies": cookies, "origins": []}
    with open(OUTPUT, "w") as f:
        json.dump(state, f, indent=2)

    from collections import Counter
    domain_counts = Counter(c["domain"] for c in cookies)
    x_cookies = [c for c in cookies if "x.com" in c["domain"] or "twitter" in c["domain"]]

    print(f"✓ 导出 {len(cookies)} 个 cookies → {OUTPUT}")
    print(f"  X/Twitter: {len(x_cookies)} 个")
    print(f"  主要域名: {dict(list(domain_counts.most_common(8)))}")

if __name__ == "__main__":
    export_cookies_via_cdp()
