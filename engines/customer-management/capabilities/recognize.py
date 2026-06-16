#!/usr/bin/env python3
"""
recognize.py — 认（确定性规则，0-LLM）。§2② + §6。

把 `extract_students.py` + `enrich_students.py` 的**确定性部分**合并成一份：
认出"规矩死"的信息——群成员/wxid/手机号/地址（规则）、其他名称拼装、
学期与复训推断（文本+群成员），并把结果落 all_student.json（飞书字段对齐）。

边界（§3）：本模块 0-LLM。**学员画像 / 自我介绍**这类需要"读懂"的内容
**不在这里**——交给 analyze 的 profile 卡（LLM）。原 enrich_students.py 的
自我介绍正则抽取属"自我介绍部分"，按 §3 归入 analyze/profile，本模块不再做；
已填的自我介绍由本模块的 merge-preserve（PRESERVE_IF_OLD_HAS）保留不动。
原 enrich_students.py 的**学期推断**是确定性规则，保留并入本模块（落盘前补空学期）。

用法（迁移后从 engine 根跑）:
    python3 -m capabilities.recognize
"""

import json
import os
import re
import glob
import sys
from pathlib import Path

# engine 根（capabilities/ → up 1）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

BASE_DIR = str(config.BASE_DIR)
DATA_DIR = str(config.DATA_DIR)
DASHBOARD_PATH = str(config.DASHBOARD_PATH)
OUTPUT_PATH = str(config.STUDENT_FILE)
STAFF_EXCLUDE_PATH = str(config.STAFF_EXCLUDE_FILE)

GROUP_ID_MAP = {
    "54388823635@chatroom": "四期-AI实战训练营-无所畏惧！",
    "56738408970@chatroom": "AI产品训练营核心交流群",
    "57069021254@chatroom": "4.5期-AI实战训练营！",
}

GROUP_NAME_TO_SEMESTER = {
    "四期-AI实战训练营-无所畏惧！": "4期",
    "4.5期-AI实战训练营！": "4.5期",
    "AI产品训练营核心交流群": "AI产品训练营",
}

# 好友名单产物（sync_groups.js dump）→ 飞书"添加微信"标签映射。
WECHAT_TAG_BY_ROSTER = {
    "assistant": "小助理",
    "zh2": "张和2号",
}

ROW_SOURCE_ROLES = {"zh2"}

PHONE_RE = re.compile(r'(?<!\d)(1[3-9]\d{9})(?!\d)')
ADDRESS_KEYWORDS = re.compile(r'[省市区路街道小区号]')
ADDRESS_STRONG = re.compile(r'(省.{1,10}市|市.{1,10}区|区.{1,10}路|路.{1,6}号|街道|小区)')
ADDRESS_EXCLUDE = re.compile(r'http|www|\.com|微信|群|请|感谢|账号|登录|飞书|学习|课程|老师')

SEMESTER_ORDER = {'1期': 1, '2期': 2, '3期': 3, '4期': 4, '4.5期': 4.5, '5期': 5}

# 当前正在开课的期数，只有这些期数才可能作为复训值
CURRENT_SEMESTER = '4.5期'
CURRENT_SEMESTER_ORDER = SEMESTER_ORDER[CURRENT_SEMESTER]

# 学期归一（用于消息文本里的"4期/四期/4.5期"推断）
SEMESTER_NORMALIZE = {
    '1': '1期', '2': '2期', '3': '3期', '4': '4期', '4.5': '4.5期', '5': '5期',
    '一': '1期', '二': '2期', '三': '3期', '四': '4期', '五': '5期',
}


def try_decode_hex(content):
    """Try to decode hex-encoded content."""
    try:
        decoded = bytes.fromhex(content).decode('utf-8')
        return decoded
    except Exception:
        return content


def extract_all_semesters_from_text(text):
    """Extract ALL semester labels from text (for 复训 inference)."""
    if not text:
        return []
    return [m.group(0) for m in re.finditer(r'(\d+\.?\d*)期', text)]


def extract_phone_from_text(text):
    """Extract phone number from display name / group nickname."""
    if not text:
        return ""
    m = PHONE_RE.search(text)
    return m.group(0) if m else ""


def load_member_details():
    """Load detailed member info from all three group files."""
    member_details = {}

    member_files = [
        "members_54388823635_chatroom.json",
        "members_56738408970_chatroom.json",
        "members_57069021254_chatroom.json",
    ]

    for filename in member_files:
        path = os.path.join(DATA_DIR, filename)
        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        for m in data.get('members', []):
            wxid = m.get('wxid', '')
            if not wxid:
                continue

            if wxid not in member_details:
                member_details[wxid] = {
                    'wxid': wxid,
                    '昵称': m.get('昵称', ''),
                    '备注名': m.get('备注名', ''),
                    '微信号': m.get('微信号', ''),
                    '群昵称_list': [],
                    '显示名称': m.get('显示名称', ''),
                }
            else:
                if not member_details[wxid]['昵称'] and m.get('昵称'):
                    member_details[wxid]['昵称'] = m['昵称']
                if not member_details[wxid]['备注名'] and m.get('备注名'):
                    member_details[wxid]['备注名'] = m['备注名']
                if not member_details[wxid]['微信号'] and m.get('微信号'):
                    member_details[wxid]['微信号'] = m['微信号']
                if not member_details[wxid]['显示名称'] and m.get('显示名称'):
                    member_details[wxid]['显示名称'] = m['显示名称']

            group_nickname = m.get('群昵称', '')
            if group_nickname and group_nickname not in member_details[wxid]['群昵称_list']:
                member_details[wxid]['群昵称_list'].append(group_nickname)

    return member_details


def load_dashboard_groups():
    """Load group memberships (prefers dashboard.json; falls back to members_*.json)."""
    if os.path.exists(DASHBOARD_PATH):
        with open(DASHBOARD_PATH, encoding='utf-8') as f:
            data = json.load(f)
        wxid_groups = {}
        for m in data.get('members', []):
            wxid = m.get('wxid', '')
            groups = m.get('groups', [])
            wxid_groups[wxid] = groups
        print(f"[dashboard] 用 {DASHBOARD_PATH}: {len(wxid_groups)} wxids")
        return wxid_groups

    print(f"[dashboard] {DASHBOARD_PATH} 不存在,改从 members_*.json 派生")
    wxid_groups = {}
    for fpath in sorted(glob.glob(os.path.join(DATA_DIR, "members_*_chatroom.json"))):
        if fpath.endswith('.digest.md'):
            continue
        try:
            with open(fpath, encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [WARN] 跳过 {os.path.basename(fpath)}: {e}")
            continue
        gname = data.get('chatroomName', '')
        for m in data.get('members', []):
            wxid = m.get('wxid', '')
            if not wxid:
                continue
            if wxid not in wxid_groups:
                wxid_groups[wxid] = []
            if gname and gname not in wxid_groups[wxid]:
                wxid_groups[wxid].append(gname)
    print(f"  派生完成: {len(wxid_groups)} wxids")
    return wxid_groups


def load_friend_rosters():
    """Read friends_<role>.json rosters. Returns (tag_map, friend_details)."""
    tag_map = {}
    friend_details = {}
    for role, label in WECHAT_TAG_BY_ROSTER.items():
        path = os.path.join(DATA_DIR, f"friends_{role}.json")
        if not os.path.exists(path):
            print(f"[roster] friends_{role}.json 不存在,跳过 ({label})")
            continue
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [WARN] 读取 friends_{role}.json 失败: {e}")
            continue
        friends = data.get('friends', [])
        is_row_source = role in ROW_SOURCE_ROLES
        print(f"[roster] friends_{role}.json: {len(friends)} 好友 → 标签 {label}"
              f"{' (建行源)' if is_row_source else ' (仅标签)'}")
        for fr in friends:
            wxid = fr.get('wxid', '')
            if not wxid:
                continue
            tag_map.setdefault(wxid, set()).add(label)
            if is_row_source and wxid not in friend_details:
                friend_details[wxid] = {
                    '昵称': fr.get('昵称', ''),
                    '备注名': fr.get('备注名', ''),
                    '微信号': fr.get('微信号', ''),
                }
    return {w: sorted(s) for w, s in tag_map.items()}, friend_details


def build_other_names(member):
    """Build 其他名称 from 备注名, 微信号, 群昵称."""
    parts = []
    if member.get('备注名'):
        parts.append(f"备注:{member['备注名']}")
    if member.get('微信号'):
        parts.append(f"微信号:{member['微信号']}")
    group_nicks = member.get('群昵称_list', [])
    if group_nicks:
        parts.append(f"群昵称:{'/'.join(group_nicks)}")
    return ' | '.join(parts)


def infer_semester_and_fuxun(member, groups):
    """Infer semester and 复训 from name/remark/group nickname + group membership."""
    display = member.get('显示名称', '')
    remark = member.get('备注名', '')
    group_nicks = member.get('群昵称_list', [])

    all_sems = set()
    for text in [display, remark] + group_nicks:
        for sem in extract_all_semesters_from_text(text):
            all_sems.add(sem)

    group_sems = set()
    if '4.5期-AI实战训练营！' in groups:
        group_sems.add('4.5期')
    if '四期-AI实战训练营-无所畏惧！' in groups:
        group_sems.add('4期')

    if all_sems:
        sorted_text_sems = sorted(all_sems, key=lambda s: SEMESTER_ORDER.get(s, 99))
        semester = sorted_text_sems[0]
        sem_order = SEMESTER_ORDER.get(semester, 99)
        combined = all_sems | group_sems
        fuxun = sorted([s for s in combined
                        if SEMESTER_ORDER.get(s, 99) > sem_order
                        and SEMESTER_ORDER.get(s, 99) >= CURRENT_SEMESTER_ORDER],
                       key=lambda s: SEMESTER_ORDER.get(s, 99))
        return semester, fuxun

    if group_sems:
        sorted_gsems = sorted(group_sems, key=lambda s: SEMESTER_ORDER.get(s, 99))
        semester = sorted_gsems[0]
        sem_order = SEMESTER_ORDER.get(semester, 99)
        fuxun = sorted([s for s in group_sems
                        if SEMESTER_ORDER.get(s, 99) > sem_order
                        and SEMESTER_ORDER.get(s, 99) >= CURRENT_SEMESTER_ORDER],
                       key=lambda s: SEMESTER_ORDER.get(s, 99))
        return semester, fuxun

    if 'AI产品训练营核心交流群' in groups:
        return 'AI产品训练营', []

    return '', []


def load_staff_exclude():
    """Load staff wxids to exclude from student list."""
    if not os.path.exists(STAFF_EXCLUDE_PATH):
        return set()
    with open(STAFF_EXCLUDE_PATH, encoding='utf-8') as f:
        data = json.load(f)
    excluded = {s['wxid'] for s in data.get('staff', [])}
    print(f"Staff exclusion list loaded: {len(excluded)} wxids")
    return excluded


# --- 学期消息推断（原 enrich_students.py 的确定性部分）-----------------

def _decode_content(content):
    if not content or not isinstance(content, str):
        return ''
    if re.match(r'^[0-9a-fA-F]+$', content) and len(content) % 2 == 0 and len(content) > 20:
        return try_decode_hex(content)
    return content


def infer_semester_from_messages(msgs, current_semester):
    """Try to infer semester from student's own chat messages (deterministic)."""
    if current_semester:
        return current_semester

    semester_counts = {}
    student_semester_re = re.compile(
        r'(我.*[是参加购买报名].*?([一二三四五1-5]|4\.5)期|'
        r'([一二三四五1-5]|4\.5)期.*[学员学习]|'
        r'[第]?([一二三四五1-5]|4\.5)期.*[的复训])',
        re.IGNORECASE
    )

    for msg in msgs:
        if msg.get('isSelf', 1):
            continue
        content = _decode_content(msg.get('content', ''))
        if not content:
            continue
        m = student_semester_re.search(content)
        if m:
            for g in m.groups():
                if g and re.match(r'^([一二三四五1-5]|4\.5)$', str(g)):
                    norm_map = {'一':'1期','二':'2期','三':'3期','四':'4期','五':'5期',
                                '1':'1期','2':'2期','3':'3期','4':'4期','5':'5期','4.5':'4.5期'}
                    sem = norm_map.get(g)
                    if sem:
                        semester_counts[sem] = semester_counts.get(sem, 0) + 1

    if semester_counts:
        return max(semester_counts, key=semester_counts.get)
    return ''


_FRIEND_EVENT_PAT = ("你已添加了", "通过了你的朋友验证", "现在我们可以开始聊天", "现在可以开始聊天")


def friend_add_date(wxid):
    """加好友日期（确定性，0-LLM）：系统事件「你已添加了X / 通过好友验证」的时间，
    回退到最早一条消息的时间。返回 'YYYY-MM-DD' 或 None。

    病根复盘：这条信息以前一直找不到，是因为 analyze 入库把系统提示删了；
    本派生直接读原始消息（无损），与 analyze 的无损分层一致。见
    doc/plan/customer-management-media-visibility-plan.md 阶段4。
    """
    import datetime as _dt
    path = os.path.join(DATA_DIR, f"messages_user_{wxid}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    msgs = sorted((data.get("messages") or []), key=lambda m: m.get("createTime", 0))
    for m in msgs:
        c = _decode_content(m.get("content", "")) or ""
        if any(p in c for p in _FRIEND_EVENT_PAT):
            ts = m.get("createTime")
            if ts:
                return _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    for m in msgs:
        ts = m.get("createTime")
        if ts:
            return _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    return None


def main():
    print("Loading dashboard group data...")
    wxid_groups = load_dashboard_groups()

    staff_exclude = load_staff_exclude()

    print("Loading member details from group files...")
    member_details = load_member_details()

    print("Loading friend rosters (添加微信 tags)...")
    wechat_tag_map, friend_details = load_friend_rosters()

    all_wxids = set(wxid_groups.keys()) | set(friend_details.keys())
    print(f"Total unique wxids: {len(wxid_groups)} 群成员 + 张和2号好友并集后 {len(all_wxids)}")

    print("Building message file index...")
    msg_file_index = {}
    for fpath in glob.glob(os.path.join(DATA_DIR, "messages_user_*.json")):
        try:
            with open(fpath, encoding='utf-8') as f:
                data = json.load(f)
            uid = data.get('userId', '')
            if uid:
                msg_file_index[uid] = fpath
        except Exception:
            pass
    print(f"Message files indexed: {len(msg_file_index)}")

    students = []

    skipped_staff = 0
    for wxid in all_wxids:
        if wxid in staff_exclude:
            skipped_staff += 1
            continue

        groups = wxid_groups.get(wxid, [])

        member = member_details.get(wxid)
        if member is None:
            fd = friend_details.get(wxid, {})
            member = {
                'wxid': wxid,
                '昵称': fd.get('昵称', ''),
                '备注名': fd.get('备注名', ''),
                '微信号': fd.get('微信号', ''),
                '群昵称_list': [],
                '显示名称': fd.get('备注名') or fd.get('昵称') or '',
            }

        # Extract phone and address from private messages (deterministic)
        phones = []
        addresses = []
        msgs_for_semester = []
        if wxid in msg_file_index:
            fpath = msg_file_index[wxid]
            try:
                with open(fpath, encoding='utf-8') as f:
                    msg_data = json.load(f)
                msgs_for_semester = msg_data.get('messages', [])
                for msg in msgs_for_semester:
                    content = msg.get('content', '')
                    if not content or not isinstance(content, str):
                        continue
                    if content.startswith('[') and content.endswith(']'):
                        continue
                    if re.match(r'^[0-9a-fA-F]+$', content) and len(content) % 2 == 0:
                        content = try_decode_hex(content)
                    found_phones = PHONE_RE.findall(content)
                    phones.extend(found_phones)
                    lines = content.replace('，', '\n').replace(',', '\n').split('\n')
                    for line in lines:
                        line = line.strip()
                        if len(line) > 10 and ADDRESS_STRONG.search(line):
                            if not ADDRESS_EXCLUDE.search(line):
                                addresses.append(line)
            except Exception:
                pass

        seen_phones = []
        for p in phones:
            if p not in seen_phones:
                seen_phones.append(p)
        phones = seen_phones

        semester, fuxun = infer_semester_and_fuxun(member, groups)

        if not phones:
            for text in [member.get('显示名称', '')] + member.get('群昵称_list', []):
                p = extract_phone_from_text(text)
                if p:
                    phones.append(p)
                    break

        # 学期为空 → 从私聊消息确定性推断（原 enrich_students 学期推断并入）
        if not semester and msgs_for_semester:
            inferred = infer_semester_from_messages(msgs_for_semester, semester)
            if inferred:
                semester = inferred

        student = {
            "wxid": wxid,
            "微信昵称": member.get('昵称', ''),
            "其他名称": build_other_names(member),
            "手机号": phones[0] if phones else "",
            "收货地址": addresses[0] if addresses else "",
            "所在群": groups,
            "学期": semester,
            "渠道": "",
            "所属推广员": "",
            "购买商品": "",
            "累计消费次数": None,
            "累计有效消费金额": None,
            "最近消费时间": "",
            "复训": fuxun if fuxun else None,
            "添加微信": wechat_tag_map.get(wxid, []),
        }
        students.append(student)

    # merge-preserve：recognize 重跑不抹掉 LLM/历史填的 "soft" 字段（含自我介绍，§207）。
    PRESERVE_IF_OLD_HAS = {
        "自我介绍", "加入的目的", "offer情况",   # LLM (analyze/profile) only
        "购买商品", "渠道", "所属推广员",         # LLM / 人工
        "累计消费次数", "累计有效消费金额", "最近消费时间",
        "手机号", "收货地址",
    }
    if os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, encoding='utf-8') as f:
                old_students = json.load(f)
            old_by_wxid = {s["wxid"]: s for s in old_students if s.get("wxid")}
            preserved_counts = {f: 0 for f in PRESERVE_IF_OLD_HAS}
            for s in students:
                old = old_by_wxid.get(s["wxid"])
                if not old:
                    continue
                for f in PRESERVE_IF_OLD_HAS:
                    new_v = s.get(f)
                    old_v = old.get(f)
                    is_empty = new_v in (None, "", [])
                    if is_empty and old_v not in (None, "", []):
                        s[f] = old_v
                        preserved_counts[f] += 1
                new_fuxun = s.get("复训") or []
                if isinstance(new_fuxun, str):
                    new_fuxun = [new_fuxun] if new_fuxun else []
                old_fuxun = old.get("复训") or []
                if isinstance(old_fuxun, str):
                    old_fuxun = [old_fuxun] if old_fuxun else []
                merged = sorted(set([str(x) for x in new_fuxun + old_fuxun if x]))
                s["复训"] = merged if merged else None
                new_tags = s.get("添加微信") or []
                old_tags = old.get("添加微信") or []
                s["添加微信"] = sorted(set(new_tags) | set(old_tags))
            print(f"\n[merge-preserve] 从旧 all_student.json 保留:")
            for f, c in preserved_counts.items():
                if c > 0:
                    print(f"  {f}: {c} 条")
        except Exception as e:
            print(f"[WARN] merge 旧数据失败 (继续不 merge): {e}")

    semester_order = {"4.5期": 0, "4期": 1, "AI产品训练营": 2, "": 3}
    students.sort(key=lambda s: (semester_order.get(s['学期'], 9), s['微信昵称']))

    print(f"Skipped staff: {skipped_staff}")
    print(f"\nTotal students: {len(students)}")
    has_phone = sum(1 for s in students if s['手机号'])
    has_address = sum(1 for s in students if s['收货地址'])
    print(f"Students with phone: {has_phone}")
    print(f"Students with address: {has_address}")

    semester_counts = {}
    for s in students:
        sem = s['学期'] or '(未知)'
        semester_counts[sem] = semester_counts.get(sem, 0) + 1
    print("\nSemester distribution:")
    for sem, count in sorted(semester_counts.items()):
        print(f"  {sem}: {count}")

    tag_counts = {}
    for s in students:
        for tag in (s.get('添加微信') or ['(无标签)']):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    print("\n添加微信 distribution:")
    for tag, count in sorted(tag_counts.items()):
        print(f"  {tag}: {count}")

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(students, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
