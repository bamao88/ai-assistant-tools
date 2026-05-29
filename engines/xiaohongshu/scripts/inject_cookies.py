"""Empirically test: can we restore an xhs session by injecting saved JSON cookies?

Steps:
1. Launch Chrome on given port + profile
2. Read saved cookie dump JSON
3. Inject every cookie via CDP Network.setCookie
4. Navigate to xiaohongshu.com/explore
5. Sleep, then check if URL stays on /explore (logged in) or hits login flow
6. Also run check-login via the engine to compare verdict

Usage: inject_cookies.py <slot> <port> <dump_path>"""

from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, "/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts")

from xhs.cdp import Browser  # type: ignore[reportMissingImports]
from chrome_launcher import ensure_chrome, has_display  # type: ignore[reportMissingImports]

slot = sys.argv[1]
port = int(sys.argv[2])
dump_path = sys.argv[3]
profile_dir = f"/Users/xpw/.xhs/accounts/{slot}/chrome-profile"

with open(dump_path, encoding="utf-8") as f:
    dump = json.load(f)

raw_cookies = dump.get("cookies", [])
print(f"injecting {len(raw_cookies)} cookies from {dump_path}")

ensure_chrome(port=port, headless=not has_display(), user_data_dir=profile_dir)
time.sleep(1.5)
browser = Browser(host="127.0.0.1", port=port)
browser.connect()
page = browser.get_or_create_page()

# First clear all current cookies on .xiaohongshu.com to avoid mixed-state
try:
    page._send_session("Storage.clearCookies", {})
except Exception as e:
    print(f"clearCookies warning: {e}")

# Inject each cookie
injected_ok = 0
injected_fail = 0
for c in raw_cookies:
    payload = {
        "name": c.get("name"),
        "value": c.get("value"),
        "domain": c.get("domain"),
        "path": c.get("path", "/"),
        "secure": c.get("secure", False),
        "httpOnly": c.get("httpOnly", False),
    }
    if c.get("expires", -1) > 0:
        payload["expires"] = c["expires"]
    if c.get("sameSite"):
        payload["sameSite"] = c["sameSite"]
    try:
        result = page._send_session("Network.setCookie", payload)
        if result.get("success", True) is False:
            injected_fail += 1
        else:
            injected_ok += 1
    except Exception as e:
        injected_fail += 1
        print(f"failed {c.get('name')}: {e}")

print(f"injected ok={injected_ok} fail={injected_fail}")

# Navigate to /explore and observe
page.navigate("https://www.xiaohongshu.com/explore")
try:
    page.wait_for_load(timeout=20)
except Exception:
    pass
time.sleep(3)

final_url = page.evaluate("window.location.href")
title = page.evaluate("document.title")
# Look for login markers
has_login_canvas = page.evaluate(
    "Boolean(document.querySelector('canvas[class*=qrcode], .login-container, .qrcode-img, [class*=qrcode_overlay]'))"
)
visible_login_text = page.evaluate(
    "Array.from(document.querySelectorAll('*')).slice(0, 200).some(el => (el.innerText||'').includes('扫码登录') || (el.innerText||'').includes('登录小红书'))"
)

print(json.dumps({
    "slot": slot,
    "final_url": final_url,
    "title": title,
    "has_login_canvas": has_login_canvas,
    "visible_login_text": visible_login_text,
    "verdict": "SESSION RESTORED" if not has_login_canvas and not visible_login_text else "SERVER REJECTED (cookies sent but server shows login)",
}, ensure_ascii=False, indent=2))
