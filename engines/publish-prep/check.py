#!/usr/bin/env python3
"""publish_<account>.md 校验器（读 platform_rules.yaml）。

把「Claude 肉眼守门」升级成「脚本跑 + 只看疑似」：校验一份发布物料是否
① 下游可解析（视频号 item.py / 小红书 extract_frontmatter 的契约）
② 合规（标题字数、关键词数、摘要区间、无导流 CTA、无 raw mermaid）。

用法:
    python3 check.py <publish_file.md> --platform xiaohongshu [--form article|video]
返回 JSON: {ok, platform, form, errors[], warnings[]}
"""
import sys
import re
import json
import argparse
from pathlib import Path

import yaml

import config

CTA_PATTERNS = ["评论区", "扣1", "扣 1", "私我领", "关注我", "私信我", "扣个1", "点赞关注"]


def cn_width(s: str) -> int:
    """小红书式宽度：CJK/全角=1，英数半角每 2 计 1，向上取整。"""
    w = 0.0
    for c in s:
        w += 1.0 if (ord(c) > 0x2E7F or '＀' <= c <= '￯') else 0.5
    return int(w + 0.5)


def split_frontmatter(md: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", md, re.S)
    if not m:
        return {}, md
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return (fm if isinstance(fm, dict) else {}), m.group(2)


def read_section(text: str, heading: str) -> str:
    pat = re.compile(rf"^##\s+{re.escape(heading)}(?:\s|[（(]|$).*$", re.M)
    m = pat.search(text)
    if not m:
        return ""
    nxt = re.search(r"^##\s+", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    return text[m.end():end].strip()


def rules_for(platform: str, form: str | None):
    rules = yaml.safe_load(config.PLATFORM_RULES.read_text(encoding="utf-8"))["platforms"]
    p = rules.get(platform)
    if p is None:
        return None, f"platform_rules.yaml 无平台键 {platform!r}"
    if "variants" in p:
        v = p["variants"].get(form or "article")
        if v is None:
            return None, f"{platform} 需 --form（article|video），当前 {form!r}"
        merged = {k: val for k, val in p.items() if k != "variants"}
        merged.update(v)
        return merged, None
    return p, None


def check(path: Path, platform: str, form: str | None) -> dict:
    errors, warnings = [], []
    rule, err = rules_for(platform, form)
    if err or rule is None:
        return {"ok": False, "platform": platform, "form": form, "errors": [err or "无规则"], "warnings": []}

    md = path.read_text(encoding="utf-8")
    fm, body_md = split_frontmatter(md)

    # ---- 视频号：走 item.py 契约（## 标题候选 一个 ✅ / ## 正文 / 视频号精简 行）----
    if platform == "shipinhao":
        title_sec = read_section(md, "标题候选")
        checked = [l for l in title_sec.splitlines() if "✅" in l and re.match(r"^\s*[-*]\s+", l)]
        if len(checked) != 1:
            errors.append(f"视频号需 ## 标题候选 恰含 1 个 - ✅ 标题（当前 {len(checked)}）")
        else:
            t = re.sub(r"[✅\-\*`\s]|(\*\*)", "", checked[0]).strip()
            lo, hi = (rule.get("short_title") or {}).get("min"), (rule.get("short_title") or {}).get("max")
            n = len(t)
            if lo and hi and not (lo <= n <= hi):
                errors.append(f"短标题 {n} 字，需 {lo}-{hi}：{t}")
        if not read_section(md, "正文"):
            errors.append("视频号缺 ## 正文 段")
        if not any("视频号精简" in l and re.search(r"#[\w一-鿿-]+", l) for l in md.splitlines()):
            errors.append("视频号缺『视频号精简』+ #标签 同行（下游 parse_shipinhao_tags 读不到）")
        body_text = read_section(md, "正文")

    # ---- 小红书：走 extract_frontmatter 契约（frontmatter block-list keywords）----
    elif platform == "xiaohongshu":
        title = str(fm.get("title", "") or "")
        tmax = (rule.get("title") or {}).get("max", 20)
        if not title:
            errors.append("小红书缺 frontmatter title")
        elif cn_width(title) > tmax:
            errors.append(f"标题 {cn_width(title)} 宽（UTF-16），需 ≤{tmax}：{title}")
        kw = fm.get("keywords")
        if not isinstance(kw, list) or len(kw) < (rule.get("keywords") or {}).get("min", 3):
            errors.append("keywords 需 frontmatter YAML 块列表（- 项）且 ≥3；flow list/占位不合格")
        elif not re.search(r"^keywords:\s*\n(?:[ \t]*-\s+.+\n?)+", md, re.M):
            errors.append("keywords 非块列表格式（extract_frontmatter 只认 `keywords:\\n  - x`）")
        if form == "article":
            ab = str(fm.get("abstract", "") or "")
            amin, amax = (rule.get("abstract") or {}).get("min", 20), (rule.get("abstract") or {}).get("max", 200)
            if not (amin < len(ab) <= amax):
                errors.append(f"abstract {len(ab)} 字，需 {amin}–{amax}")
        body_text = read_section(md, "正文") or body_md

    # ---- 公众号 / 其他 ----
    else:
        title = str(fm.get("title", "") or "")
        tmax = (rule.get("title") or {}).get("max")
        if tmax and title and len(title) > tmax:
            errors.append(f"标题 {len(title)} 字，需 ≤{tmax}")
        if platform == "gongzhonghao":
            dig = str(fm.get("digest", "") or "")
            if dig and len(dig) > (rule.get("digest") or {}).get("max", 120):
                errors.append(f"digest {len(dig)} 字，需 ≤120")
        body_text = body_md

    # ---- 通用：无导流 CTA / 无 raw mermaid ----
    for pat in CTA_PATTERNS:
        if pat in (body_text or ""):
            errors.append(f"正文含导流 CTA『{pat}』（限流风险，删）")
    if "```mermaid" in md:
        warnings.append("残留 ```mermaid``` 源码块，定稿应转图")
    if "——" in (body_text or ""):
        warnings.append("正文含破折号「——」")

    return {"ok": not errors, "platform": platform, "form": form,
            "errors": errors, "warnings": warnings}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("publish_file")
    ap.add_argument("--platform", required=True)
    ap.add_argument("--form", default=None)
    a = ap.parse_args()
    res = check(Path(a.publish_file), a.platform, a.form)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
