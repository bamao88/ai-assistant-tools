"""Dump current cookies from a running xhs profile via CDP Storage.getCookies.

Usage: dump_cookies.py <slot> <port> <out_path>"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, "/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts")

from xhs.cdp import Browser  # type: ignore[reportMissingImports]
from chrome_launcher import ensure_chrome, has_display  # type: ignore[reportMissingImports]

slot = sys.argv[1]
port = int(sys.argv[2])
out_path = sys.argv[3]
profile_dir = f"/Users/xpw/.xhs/accounts/{slot}/chrome-profile"

ensure_chrome(port=port, headless=not has_display(), user_data_dir=profile_dir)
time.sleep(1)
browser = Browser(host="127.0.0.1", port=port)
browser.connect()
page = browser.get_or_create_page()

cookies = page._send_session("Storage.getCookies", {}).get("cookies", [])

payload = {
    "slot": slot,
    "port": port,
    "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "count": len(cookies),
    "cookies": cookies,
}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

identity = {"web_session", "customer-sso-sid", "a1", "webId", "x-user-id-creator.xiaohongshu.com", "access-token-creator.xiaohongshu.com"}
visible = [c["name"] for c in cookies if c.get("name") in identity]
print(json.dumps({"slot": slot, "out_path": out_path, "count": len(cookies), "identity_cookies": visible}, ensure_ascii=False))
