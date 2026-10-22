#!/usr/bin/env python3
"""Validate a MiMi TV external-video social copy package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_ITEM_KEYS = {
    "item_id", "content_type", "object", "source", "segment",
}
REQUIRED_COPY_KEYS = {
    "post_title", "title_strategy_id", "benchmark_refs", "body", "keywords",
    "source_credit",
}
# 外部被动节目的平台标题固定前缀：竖线后一个半角空格，见 references/copy.md。
TITLE_PREFIX = "给猫看的动画片| "
CORE_KEYWORDS = {"猫", "猫咪电视", "猫咪动画片", "猫咪日常"}
TITLE_STRATEGIES = {
    "hook-question", "owner-scene", "object-search", "utility-proof", "novelty",
}
KNOWN_BENCHMARK_REFS = {
    "BH-001", "BH-002", "BS-001", "BS-002", "BO-001", "BO-002",
    "BU-001", "BU-002", "BU-003", "BN-001",
}
STRATEGY_REF_PREFIX = {
    "hook-question": "BH-",
    "owner-scene": "BS-",
    "object-search": "BO-",
    "utility-proof": "BU-",
    "novelty": "BN-",
}
FORBIDDEN = {
    "没有一只猫", "没有一只小猫", "所有猫", "一定会", "猫猫最爱",
    "治愈", "治疗", "改善焦虑", "官方", "原创", "已授权",
}
PASSIVE_FORBIDDEN = {"游戏", "互动", "点击有反馈"}
# 互动钩子放在独立的置顶评论里，见 references/copy.md「互动钩子」。
STRATEGY_TAGS = {
    "E0", "E1", "E2", "E3", "E4", "E5", "H1", "H2", "H3", "H4", "P1", "P2", "P3",
}
PINNED_COMMENT_MAX = 120
# 不写「够多少人／赞才做」式门槛。
PINNED_COMMENT_THRESHOLD = re.compile(
    r"(够|满|达到|超过|破)\s*[0-9一二三四五六七八九十百千万]+\s*(个|人|票|赞|条)"
    r"|(点赞|评论|投票|赞)\s*(够|满|达到|超过|破)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查猫猫电视机 Content Item 文案或历史文案包。")
    parser.add_argument("items", nargs="+", help="一个或多个 item.json；也兼容历史 JSON 文案包。")
    return parser.parse_args()


BODY_CTA_MAX = 60  # 非空白字符


def cta_text_errors(cta: str, label: str) -> list[str]:
    """结尾互动段的文字规则；默认版和各平台改写版共用。"""
    errors: list[str] = []
    if len("".join(cta.split())) > BODY_CTA_MAX:
        errors.append(f"{label} 不超过 {BODY_CTA_MAX} 个非空白字符")
    for phrase in sorted(FORBIDDEN):
        if phrase in cta:
            errors.append(f"{label} 出现禁用表达：{phrase}")
    if PINNED_COMMENT_THRESHOLD.search(cta):
        errors.append(f"{label} 不写人数／点赞门槛类承诺")
    if re.search(r"https?://|[#＃]\S+|\[话题\]", cta):
        errors.append(f"{label} 不放外链或话题串（小红书的链接用笔记自带的挂链功能）")
    if any(marker in cta for marker in ("素材来源", "视频来源", "转载自", "片段剪辑", "商业授权", "权利状态")):
        errors.append(f"{label} 混入来源、授权或内部备注")
    if sum(cta.count(mark) for mark in ("？", "?")) > 1:
        errors.append(f"{label} 只给一个动作，最多一个问题")
    return errors


def validate_body_cta(copy: dict) -> list[str]:
    """结尾互动段：默认版必须是正文最后的单独段落；各平台改写版另按平台字段检查。"""
    errors: list[str] = []
    cta = copy.get("body_cta")
    if cta is not None:
        if not isinstance(cta, str) or not cta.strip():
            return ["body_cta 必须是非空字符串"]
        cta = cta.strip()
        body = str(copy.get("body", "")).strip()
        if not body.endswith(cta) or not body[: -len(cta)].endswith("\n\n"):
            errors.append("body_cta 必须单独成段，并且是 body 的最后一段")
        errors += cta_text_errors(cta, "body_cta")
    overrides = copy.get("platform_overrides", {})
    if not isinstance(overrides, dict):
        return errors + ["platform_overrides 必须是对象"]
    for platform, override in overrides.items():
        if platform not in {"douyin", "bilibili"}:
            errors.append(f"platform_overrides 只支持 douyin、bilibili：{platform}")
            continue
        text = override.get("body_cta") if isinstance(override, dict) else None
        if not isinstance(text, str) or not text.strip():
            errors.append(f"platform_overrides.{platform}.body_cta 必须是非空字符串")
        elif cta is None:
            errors.append(f"platform_overrides.{platform} 需要先有默认 body_cta")
        else:
            errors += cta_text_errors(text.strip(), f"platform_overrides.{platform}.body_cta")
    return errors


def validate_engagement(copy: dict) -> list[str]:
    """检查可选的结尾互动段、置顶评论与策略标签。"""
    errors: list[str] = validate_body_cta(copy)
    tags = copy.get("strategy_tags")
    if tags is not None:
        if not isinstance(tags, list) or not tags or not all(isinstance(t, str) for t in tags):
            errors.append("strategy_tags 必须是非空字符串数组")
        else:
            unknown = sorted(set(tags) - STRATEGY_TAGS)
            if unknown:
                errors.append("strategy_tags 含未定义编号：" + "、".join(unknown))
            if len(set(tags)) != len(tags):
                errors.append("strategy_tags 不能重复")

    comment = copy.get("pinned_comment")
    if comment is None:
        return errors
    if not isinstance(comment, str) or not comment.strip():
        return errors + ["pinned_comment 必须是非空字符串"]
    comment = comment.strip()
    if len(comment) > PINNED_COMMENT_MAX:
        errors.append(f"pinned_comment 不能超过 {PINNED_COMMENT_MAX} 个字符")
    for phrase in sorted(FORBIDDEN):
        if phrase in comment:
            errors.append(f"pinned_comment 出现禁用表达：{phrase}")
    if PINNED_COMMENT_THRESHOLD.search(comment):
        errors.append("pinned_comment 不写人数／点赞门槛类承诺")
    if re.search(r"https?://|[#＃]\S+|\[话题\]", comment):
        errors.append("pinned_comment 不放外链或话题串")
    if any(marker in comment for marker in ("素材来源", "视频来源", "转载自", "片段剪辑", "商业授权", "权利状态")):
        errors.append("pinned_comment 混入来源、授权或内部备注")
    if sum(comment.count(mark) for mark in ("？", "?")) > 1:
        errors.append("pinned_comment 一条只给一个动作，最多一个问题")
    return errors


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"无法读取 JSON：{exc}"]

    missing_item = sorted(REQUIRED_ITEM_KEYS - set(data))
    if missing_item:
        return ["缺少 item 字段：" + "、".join(missing_item)]

    copy = data.get("copy", data)
    if not isinstance(copy, dict):
        return ["copy 必须是对象"]
    missing_copy = sorted(REQUIRED_COPY_KEYS - set(copy))
    if missing_copy:
        return ["缺少 copy 字段：" + "、".join(missing_copy)]

    if data["content_type"] != "external_passive_video":
        errors.append("当前阶段 content_type 必须为 external_passive_video")

    obj = str(data["object"]).strip()
    if not obj:
        errors.append("object 不能为空")

    source = data["source"]
    exception_approved = False
    if not isinstance(source, dict):
        errors.append("source 必须是对象")
        source = {}
    else:
        for key in ("platform", "channel", "original_title", "url", "usage_basis", "rights_status"):
            if not source.get(key):
                errors.append(f"source.{key} 缺失")
        exception = source.get("exception_approval")
        exception_approved = (
            isinstance(exception, dict)
            and exception.get("approved_by") == "project_owner"
            and bool(exception.get("approved_at"))
            and bool(exception.get("scope"))
        )
        platform = str(source.get("platform", "")).lower()
        if platform != "youtube" and not exception_approved:
            errors.append("非 YouTube 来源必须提供当前 item 的负责人单项批准记录")
        url = str(source.get("url", ""))
        if platform == "youtube" and "youtube.com/" not in url and "youtu.be/" not in url:
            errors.append("source.url 不是可识别的 YouTube 地址")

    segment = data["segment"]
    if not isinstance(segment, dict):
        errors.append("segment 必须是对象")
    else:
        mode = segment.get("mode", "clip")
        start = segment.get("start_seconds")
        end = segment.get("end_seconds")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            errors.append("segment.start_seconds / end_seconds 必须是数字")
        elif end <= start:
            errors.append("segment.end_seconds 必须晚于 start_seconds")
        elif mode == "full_source":
            if not exception_approved:
                errors.append("full_source 必须有负责人单项批准记录")
            if start != 0:
                errors.append("full_source 必须从 0 秒开始")
        if mode not in {"clip", "full_source"}:
            errors.append("segment.mode 必须是 clip 或 full_source")
        if segment.get("continuous") is not True:
            errors.append("当前只接受单个连续场景，segment.continuous 必须为 true")

    title = str(copy["post_title"]).strip()
    strategy = str(copy["title_strategy_id"]).strip()
    benchmark_refs = copy["benchmark_refs"]
    body = str(copy["body"]).strip()
    credit = str(copy["source_credit"]).strip()
    # 结尾互动段（copy.body_cta）是唯一允许出现「游戏」「互动」的正文位置，其余仍按被动节目规则。
    cta = str(copy.get("body_cta", "")).strip()
    body_main = body[: -len(cta)].rstrip() if cta and body.endswith(cta) else body
    authored_copy = " ".join((title, body))
    passive_scan = " ".join((title, body_main))

    if strategy not in TITLE_STRATEGIES:
        errors.append("title_strategy_id 不是已定义的对标策略")
    if not isinstance(benchmark_refs, list) or not 1 <= len(benchmark_refs) <= 3:
        errors.append("benchmark_refs 必须包含 1–3 个对标样本 ID")
    else:
        if len(set(benchmark_refs)) != len(benchmark_refs):
            errors.append("benchmark_refs 不能重复")
        if any(ref not in KNOWN_BENCHMARK_REFS for ref in benchmark_refs):
            errors.append("benchmark_refs 包含未登记的对标样本 ID")
        expected_prefix = STRATEGY_REF_PREFIX.get(strategy)
        if expected_prefix and not any(ref.startswith(expected_prefix) for ref in benchmark_refs):
            errors.append("benchmark_refs 至少要有一条与 title_strategy_id 对应")

    if not title.startswith(TITLE_PREFIX):
        errors.append(f"post_title 必须以固定前缀「{TITLE_PREFIX}」开头（半角竖线＋一个半角空格）")
    elif not title[len(TITLE_PREFIX):].strip() or title[len(TITLE_PREFIX)].isspace():
        errors.append("post_title 固定前缀后须紧接本期主题，且只保留一个空格")
    if "猫" not in title and (not obj or obj not in title):
        errors.append("post_title 至少要由猫咪用途或具体对象建立内容锚点")
    if strategy in {"object-search", "utility-proof"} and obj and obj not in title:
        errors.append(f"{strategy} 标题必须包含具体对象")
    if strategy in {"hook-question", "owner-scene"} and "猫" not in title:
        errors.append(f"{strategy} 标题必须包含猫咪视角")
    if strategy == "hook-question" and not any(mark in title for mark in ("？", "?")):
        errors.append("hook-question 必须使用开放问题，不能改写成绝对承诺")
    if not 8 <= len(title) <= 32:
        errors.append("post_title 建议保持 8–32 个字符")
    for phrase in sorted(FORBIDDEN):
        if phrase in authored_copy:
            errors.append(f"出现禁用表达：{phrase}")
    for phrase in sorted(PASSIVE_FORBIDDEN):
        if phrase in passive_scan:
            errors.append(f"出现禁用表达：{phrase}")

    # 正文是独立发布字段，不能混入来源组件、话题或内部审核信息。
    non_body_markers = (
        "素材来源", "视频来源", "来源署名", "转载自", "片段剪辑", "完整转发",
        "原作者", "商业授权", "权利状态", "审核备注", "logic/contract",
    )
    if any(marker in body for marker in non_body_markers) or (credit and credit in body):
        errors.append("body 混入来源、剪辑说明或内部备注；请移至独立字段")
    source_url = str(source.get("url", ""))
    source_title = str(source.get("original_title", ""))
    source_channel = str(source.get("channel", ""))
    if ((source_url and source_url in body)
            or (source_title and source_title in body)
            or (source_channel and "@" + source_channel in body)):
        errors.append("body 混入原链接、原题或作者署名；请使用来源组件")
    if re.search(r"[#＃]\S+|\[话题\]", body):
        errors.append("body 混入话题串；keywords 必须通过原生话题组件单独填写")
    if "\n\n" not in body:
        errors.append("body 必须用空行分段，不能把整篇压成一段")

    body_style = copy.get("body_style", "viewing-guide")
    compact_body = "".join(body_main.split())
    if not 40 <= len(compact_body) <= 180:
        errors.append("body 应保持约 40–180 个非空白字符")
    if body_style == "cat-fact":
        facts = copy.get("fact_sources")
        if not isinstance(facts, list) or not facts:
            errors.append("cat-fact 正文须保留独立 fact_sources 核对资料")
        elif any(not isinstance(fact, dict) or not fact.get("title")
                 or not str(fact.get("url", "")).startswith("https://") for fact in facts):
            errors.append("fact_sources 须含真实资料标题和 HTTPS 原链接")
    elif body_style == "viewing-guide":
        if "全屏" not in body:
            errors.append("body 缺少全屏使用提示")
        if not any(word in body for word in ("手机", "平板", "电视")):
            errors.append("body 缺少设备使用提示")
        if not any(word in body for word in ("放稳", "固定")):
            errors.append("body 缺少设备固定提示")
        if "每只猫" not in body or not any(word in body for word in ("不一样", "不同", "不感兴趣")):
            errors.append("body 缺少猫咪个体差异说明")
    else:
        errors.append("未知 body_style；先确认正文结构而不是套用观看说明")

    channel = str(source.get("channel", ""))
    original_title = str(source.get("original_title", ""))
    platform = str(source.get("platform", "")).lower()
    platform_label = {"youtube": "YouTube", "xiaohongshu": "小红书"}.get(platform, platform)
    if platform_label and platform_label not in credit:
        errors.append("source_credit 缺少真实来源平台")
    segment_mode = segment.get("mode", "clip") if isinstance(segment, dict) else "clip"
    if segment_mode == "full_source":
        if not any(phrase in credit for phrase in ("完整转发", "原片完整")):
            errors.append("full_source 的 source_credit 必须说明按原片完整转发")
    elif "片段剪辑" not in credit:
        errors.append("source_credit 必须说明片段剪辑")
    if channel and channel not in credit:
        errors.append("source_credit 缺少频道名")
    if original_title and original_title not in credit:
        errors.append("source_credit 缺少原视频标题")

    keywords = copy["keywords"]
    if not isinstance(keywords, list) or not all(isinstance(x, str) and x.strip() for x in keywords):
        errors.append("keywords 必须是非空字符串数组")
    else:
        if not 7 <= len(keywords) <= 9:
            errors.append("keywords 必须保留 7–9 个")
        if len(set(keywords)) != len(keywords):
            errors.append("keywords 不能重复")
        core = {"猫咪电视", "猫咪动画片"} if body_style == "cat-fact" else CORE_KEYWORDS
        missing_core = sorted(core - set(keywords))
        if missing_core:
            errors.append("keywords 缺少固定词：" + "、".join(missing_core))
        if obj and obj not in keywords:
            errors.append("keywords 缺少具体对象词")
        for word in PASSIVE_FORBIDDEN | {"猫猫最爱", "猫咪好物分享", "解压视频"}:
            if word in keywords:
                errors.append(f"keywords 出现禁用词：{word}")

    errors.extend(validate_engagement(copy))

    status = data.get("status", data.get("review_status"))
    if status not in {"draft", "review", "ready"}:
        errors.append("item 状态必须是 draft、review 或 ready")

    return errors


def main() -> None:
    args = parse_args()
    failed = False
    for raw in args.items:
        path = Path(raw).expanduser().resolve()
        errors = validate(path)
        if errors:
            failed = True
            print(f"失败 {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"通过 {path}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
