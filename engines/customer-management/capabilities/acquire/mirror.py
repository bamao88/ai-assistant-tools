#!/usr/bin/env python3
"""
pull_customer_management.py — 飞书「客户管理」表 → 本地只读镜像

把飞书唯一真源表 tblfCYoeornDw0XF 整表拉到本地 customer_management_mirror.json，
之后所有"5期多少人 / 各渠道多少 / 各标签分布"等统计都本地秒答，不再每次走 MCP/网络。

⚠️ 只读镜像：本脚本只发 GET，永不写飞书。飞书永远是真源，本地是缓存快照。
   需要最新数据就重跑本脚本刷新；不要拿镜像反推回写飞书。

用法（迁移后从 engine 根跑）:
    python3 -m capabilities.acquire.mirror            # 拉全表 + 写镜像 + 打印分布
    python3 -m capabilities.acquire.mirror --quiet     # 只写文件不打印摘要
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

# engine 根（capabilities/acquire/ → up 2）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

MIRROR_FILE = config.MIRROR_FILE

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"


def run_lark(args: list[str], timeout: int = 60) -> dict:
    """跑 lark-cli，返回解析后的 JSON data 字段。复用 sync_to_feishu.py 的鉴权方式。"""
    cmd = ["lark-cli", "--as", "bot", "--profile", LARK_PROFILE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"lark-cli failed: {' '.join(args[:6])}... stderr={res.stderr[:300]}")
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"lark-cli non-JSON: {e} stdout_head={res.stdout[:200]}")
    if data.get("code") != 0:
        raise RuntimeError(f"feishu error code={data.get('code')} msg={data.get('msg')}")
    return data.get("data", {})


def fetch_fields() -> list[dict]:
    """拉字段 schema（字段名 / 类型 / 下拉选项），存进镜像供参考。"""
    data = run_lark([
        "api", "GET",
        f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields",
        "--params", json.dumps({"page_size": 100}),
    ])
    out = []
    for f in data.get("items") or []:
        entry = {"field_name": f.get("field_name"), "field_id": f.get("field_id"),
                 "ui_type": f.get("ui_type")}
        opts = (f.get("property") or {}).get("options")
        if opts:
            entry["options"] = [o.get("name") for o in opts]
        out.append(entry)
    return out


def fetch_all_records() -> list[dict]:
    """分页拉全表，返回 [{record_id, fields:{...}}]（字段保留 API 原样）。"""
    all_items: list[dict] = []
    page_token = ""
    while True:
        params: dict[str, Any] = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        data = run_lark([
            "api", "GET",
            f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
            "--params", json.dumps(params, ensure_ascii=False),
        ])
        all_items.extend(data.get("items") or [])
        if not data.get("has_more"):
            break
        page_token = data.get("page_token") or ""
        if not page_token:
            break
        time.sleep(0.2)
    return all_items


def field_text(value: Any) -> str:
    """把飞书各种字段值压成可读字符串，方便统计/查询。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "✓" if value else ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = []
        for v in value:
            if isinstance(v, dict):
                parts.append(v.get("text") or v.get("name") or "")
            else:
                parts.append(str(v))
        return " ".join(p for p in parts if p)
    if isinstance(value, dict):
        return value.get("text") or value.get("name") or ""
    return str(value)


def print_summary(records: list[dict]) -> None:
    """打印几个高频分布，拉完一眼看到价值。"""
    cohort = Counter()
    tag = Counter()
    for r in records:
        f = r.get("fields", {})
        for c in (f.get("几期学员") or []):
            cohort[c if isinstance(c, str) else field_text(c)] += 1
        t = field_text(f.get("客户标签"))
        if t:
            tag[t] += 1
    print(f"\n总记录数: {len(records)}", file=sys.stderr)
    print("\n几期学员分布:", file=sys.stderr)
    for k, v in cohort.most_common():
        print(f"  {k:<12} {v}", file=sys.stderr)
    print("\n客户标签分布:", file=sys.stderr)
    for k, v in tag.most_common():
        print(f"  {k:<12} {v}", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description="飞书客户管理表 → 本地只读镜像")
    p.add_argument("--quiet", action="store_true", help="不打印分布摘要")
    args = p.parse_args()

    print("[pull] 拉字段 schema ...", file=sys.stderr)
    fields = fetch_fields()
    print("[pull] 拉全表记录 ...", file=sys.stderr)
    records = fetch_all_records()
    print(f"[pull] 共 {len(records)} 行 / {len(fields)} 字段", file=sys.stderr)

    mirror = {
        "_meta": {
            "source": "feishu 客户管理（唯一真源）",
            "app_token": APP_TOKEN,
            "table_id": TABLE_ID,
            "wiki_url": "https://izux3goqsa.feishu.cn/wiki/ENIFwsi9cilbJ3km9DCcyRMTngd?table=tblfCYoeornDw0XF",
            "synced_at": datetime.now().isoformat(timespec="seconds"),
            "total_records": len(records),
            "readonly": True,
            "note": "只读快照。刷新重跑 pull_customer_management.py。不要反向写飞书。",
        },
        "fields": fields,
        "records": records,
    }
    MIRROR_FILE.write_text(json.dumps(mirror, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[pull] 已写 {MIRROR_FILE.relative_to(config.DATA_ROOT)}", file=sys.stderr)

    if not args.quiet:
        print_summary(records)


if __name__ == "__main__":
    main()
