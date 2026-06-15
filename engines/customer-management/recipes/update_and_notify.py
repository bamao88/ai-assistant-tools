#!/usr/bin/env python3
"""
update_and_notify.py

执行学员数据更新 pipeline 并输出结构化摘要：
1. 读取 last_sync_summary.json（最新微信同步增量）
2. 运行 capabilities.recognize（确定性认：群成员/wxid/手机号/学期；含原 enrich 学期推断）
3. 统计总学员数、各期分布
4. 导出 all_student.csv（飞书多选字段用逗号，utf-8-sig）
5. 输出结构化摘要 JSON（供 Claude 后续同步飞书用）
"""

import json
import os
import subprocess
import sys
import csv
from datetime import datetime
from pathlib import Path

# engine 根（recipes/ → up 1）：子进程 `-m` 调用以此为 cwd/PYTHONPATH 锚点。
ENGINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_ROOT))
import config

BASE_DIR          = str(config.BASE_DIR)
WECHAT_STATE_DIR  = str(config.WECHAT_STATE_DIR)
STUDENT_FILE      = str(config.STUDENT_FILE)
CSV_FILE          = str(config.CSV_FILE)
SUMMARY_FILE      = str(config.SUMMARY_FILE)
SYNC_SUMMARY      = str(config.SYNC_SUMMARY_FILE)
OVERRIDES_FILE    = str(config.MANUAL_OVERRIDES_FILE)

# pipeline 步骤以 engine 模块形式跑（cwd=ENGINE_ROOT）
# P3: extract_students + enrich_students 合并为 capabilities.recognize（确定性合一）。
PIPELINE_MODULES = [
    "capabilities.recognize",
]

# CSV 字段顺序
CSV_FIELDS = [
    "wxid", "微信昵称", "其他名称", "手机号", "收货地址",
    "所在群", "学期", "渠道", "所属推广员", "购买商品",
    "累计消费次数", "累计有效消费金额", "最近消费时间",
    "自我介绍", "复训", "添加微信",
]

# 飞书多选字段（用逗号分隔）
MULTISELECT_FIELDS = {"所在群", "复训", "添加微信"}


def load_manual_overrides():
    """读取 manual_overrides.json。
    返回:
      globally_locked: set，飞书同步时对所有人跳过这些字段（不写入）
      per_wxid: dict {wxid: {field: value}}，对特定人强制写入指定值
    """
    if not os.path.exists(OVERRIDES_FILE):
        return set(), {}
    with open(OVERRIDES_FILE, encoding="utf-8") as f:
        data = json.load(f)
    globally_locked = set(data.get("_globally_locked_fields", []))
    per_wxid = {k: v for k, v in data.items() if not k.startswith("_")}
    print(f"[覆盖] 全局锁定字段: {globally_locked}")
    if per_wxid:
        print(f"[覆盖] 个人修正: {len(per_wxid)} 人")
    return globally_locked, per_wxid


def load_sync_summary():
    """读取最新微信同步摘要（可选，文件不存在时返回空摘要）。"""
    if not os.path.exists(SYNC_SUMMARY):
        print(f"[WARN] 未找到 {SYNC_SUMMARY}，跳过增量摘要读取")
        return {}
    with open(SYNC_SUMMARY, encoding="utf-8") as f:
        return json.load(f)


def run_pipeline():
    """依次运行 pipeline 模块（engine 模块形式，cwd=ENGINE_ROOT）。"""
    for mod in PIPELINE_MODULES:
        name = mod
        print(f"\n{'='*50}")
        print(f"运行: {name}")
        print('='*50)
        result = subprocess.run(
            [sys.executable, "-m", mod],
            capture_output=False,  # 直接打印到终端
            cwd=str(ENGINE_ROOT),
        )
        if result.returncode != 0:
            print(f"[ERROR] {name} 返回码 {result.returncode}，终止")
            sys.exit(result.returncode)
        print(f"[OK] {name} 完成")


def export_csv(students):
    """导出 all_student.csv，飞书多选字段用逗号，utf-8-sig 编码。"""
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for s in students:
            row = {}
            for field in CSV_FIELDS:
                val = s.get(field, "")
                if field in MULTISELECT_FIELDS and isinstance(val, list):
                    # 多选字段：逗号分隔
                    row[field] = ",".join(str(v) for v in val if v)
                elif isinstance(val, list):
                    # 其他数组字段：分号分隔
                    row[field] = ";".join(str(v) for v in val if v)
                elif val is None:
                    row[field] = ""
                else:
                    row[field] = val
            writer.writerow(row)
    print(f"\n已导出 CSV: {CSV_FILE} ({len(students)} 行)")


def compute_stats(students, sync_summary):
    """计算统计摘要。"""
    total = len(students)

    # 各期分布
    semester_dist = {}
    for s in students:
        sem = s.get("学期") or "(未知)"
        semester_dist[sem] = semester_dist.get(sem, 0) + 1

    # 从 sync_summary 提取增量信息
    groups_delta = []
    total_added = 0
    total_removed = 0
    for g in sync_summary.get("groups", []):
        added_cnt   = len(g.get("added", []))
        removed_cnt = len(g.get("removed", []))
        total_added   += added_cnt
        total_removed += removed_cnt
        groups_delta.append({
            "name":        g.get("name", ""),
            "memberCount": g.get("memberCount", 0),
            "added":       added_cnt,
            "removed":     removed_cnt,
        })

    private_chats = sync_summary.get("privateChats", {})

    summary = {
        "updateTime":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "syncTime":       sync_summary.get("syncTime", ""),
        "totalStudents":  total,
        "semesterDist":   semester_dist,
        "groupsDelta": {
            "totalAdded":   total_added,
            "totalRemoved": total_removed,
            "groups":       groups_delta,
        },
        "privateChats": private_chats,
    }
    return summary


def print_summary(summary):
    """打印结构化摘要（便于 Claude 读取）。"""
    print(f"\n{'='*60}")
    print("📊 学员数据更新摘要")
    print(f"{'='*60}")
    print(f"更新时间: {summary['updateTime']}")
    print(f"微信同步时间: {summary['syncTime'] or '未知'}")
    print(f"\n总学员数: {summary['totalStudents']}")
    print("\n各期分布:")
    dist = summary["semesterDist"]
    for sem in sorted(dist.keys(), key=lambda x: (x == "(未知)", x)):
        print(f"  {sem}: {dist[sem]}")

    gd = summary["groupsDelta"]
    if gd["groups"]:
        print(f"\n群成员变化（本次同步）:")
        for g in gd["groups"]:
            print(f"  {g['name']}: {g['memberCount']}人 (+{g['added']} / -{g['removed']})")
        print(f"  合计: +{gd['totalAdded']} / -{gd['totalRemoved']}")

    pc = summary["privateChats"]
    if pc:
        print(f"\n私聊: {pc.get('withMessages',0)}/{pc.get('fetched',0)}人有新消息, "
              f"共 {pc.get('totalNewMessages',0)} 条新消息")

    print(f"\n输出文件:")
    print(f"  JSON: {STUDENT_FILE}")
    print(f"  CSV:  {CSV_FILE}")
    print(f"{'='*60}")

    # 最后输出 JSON（Claude 可解析）
    print("\n--- SUMMARY_JSON_BEGIN ---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("--- SUMMARY_JSON_END ---")


def main():
    print(f"学员数据更新 pipeline 开始")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 读取微信同步摘要 + 手动修正
    sync_summary = load_sync_summary()
    globally_locked, per_wxid_overrides = load_manual_overrides()

    # 2. 运行 pipeline
    run_pipeline()

    # 3. 加载结果
    if not os.path.exists(STUDENT_FILE):
        print(f"[ERROR] {STUDENT_FILE} 不存在，pipeline 可能失败")
        sys.exit(1)
    with open(STUDENT_FILE, encoding="utf-8") as f:
        students = json.load(f)

    # 3b. 应用个人修正（per_wxid_overrides，不受全局锁影响）
    if per_wxid_overrides:
        for s in students:
            wxid = s.get("wxid", "")
            if wxid in per_wxid_overrides:
                s.update(per_wxid_overrides[wxid])
        with open(STUDENT_FILE, "w", encoding="utf-8") as f:
            json.dump(students, f, ensure_ascii=False, indent=2)

    # globally_locked 字段在飞书同步时由调用方跳过，此处仅传递给摘要

    # 4. 导出 CSV
    export_csv(students)

    # 5. 统计 + 摘要
    summary = compute_stats(students, sync_summary)

    # 保存摘要 JSON
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print_summary(summary)


if __name__ == "__main__":
    main()
