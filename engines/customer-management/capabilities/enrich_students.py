#!/usr/bin/env python3
"""
Enrich all_student.json with:
1. 自我介绍 - from private chat messages
2. 学期 fix - infer missing semester from private chat content

注: 旧 xlsx 自我介绍/客户画像 源 (refer/*.xlsx) 已于 2026-06-15 删除。
    已填的自我介绍保留在 all_student.json (fill-only-if-empty 持久化);
    未来自我介绍/客户画像走 LLM analyze (cards/profile.md)。
"""

import json, os, re, glob

BASE_DIR = "/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/student_manage"
DATA_DIR = "/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/raw/chat"
STUDENT_FILE = os.path.join(BASE_DIR, "all_student.json")
STAFF_EXCLUDE_PATH = os.path.join(BASE_DIR, "staff_exclude.json")

# Self-intro detection patterns (applied to student's own messages, isSelf=0)
INTRO_RE = re.compile(
    r'(自我介绍|大家好[，,。].*我|我叫|我的名字|'
    r'我目前|我现在.*[工作职业岗位]|我在.*[公司做负责]|'
    r'我是.*[产品运营设计开发工程师经理总监]|'
    r'我做.*[产品运营项目]|我负责|我的背景|背景[：:]|'
    r'坐标[：:是在]|来自.*工作|工作[年].*经验|'
    r'[0-9]+年.*产品|产品.*[0-9]+年)',
    re.DOTALL
)

# Semester detection
SEMESTER_RE = re.compile(r'[第]?(\d+\.?\d*)期')

SEMESTER_NORMALIZE = {
    '1': '1期', '2': '2期', '3': '3期', '4': '4期', '4.5': '4.5期', '5': '5期',
    '一': '1期', '二': '2期', '三': '3期', '四': '4期', '五': '5期',
}

def normalize_semester(val):
    val = val.strip()
    m = re.match(r'^(\d+\.?\d*)期$', val)
    if m: return val
    return SEMESTER_NORMALIZE.get(val, val + '期')


def load_staff_exclude():
    if not os.path.exists(STAFF_EXCLUDE_PATH):
        return set()
    with open(STAFF_EXCLUDE_PATH) as f:
        return {s['wxid'] for s in json.load(f).get('staff', [])}


def try_decode_hex(content):
    try:
        return bytes.fromhex(content).decode('utf-8')
    except:
        return content


def decode_content(content):
    if not content or not isinstance(content, str):
        return ''
    if re.match(r'^[0-9a-fA-F]+$', content) and len(content) % 2 == 0 and len(content) > 20:
        return try_decode_hex(content)
    return content


def extract_intro_from_messages(msgs, wxid):
    """
    Extract best self-introduction from message list.
    Prefers longer messages with intro keywords sent by the student.
    Also collects all intro-like snippets.
    """
    candidates = []

    for msg in msgs:
        if msg.get('isSelf', 1):  # skip messages sent by 张和/staff
            continue
        content = decode_content(msg.get('content', ''))
        if not content or len(content) < 20:
            continue
        if content.startswith('[') and content.endswith(']'):
            continue
        # Skip system messages
        if msg.get('type') in ('10000', 10000):
            continue

        # Strong intro signal: longer message with keywords
        if len(content) >= 30 and INTRO_RE.search(content):
            candidates.append((len(content), content.strip()))

    if not candidates:
        return ''

    # Return the longest/most informative intro
    candidates.sort(reverse=True)
    # Deduplicate and cap at 3 snippets
    seen = set()
    results = []
    for _, text in candidates:
        key = text[:50]
        if key not in seen:
            seen.add(key)
            results.append(text)
        if len(results) >= 3:
            break

    return '\n---\n'.join(results)


def infer_semester_from_messages(msgs, current_semester):
    """
    Try to infer semester from chat messages.
    Look for student messages mentioning which period they're in.
    """
    if current_semester:
        return current_semester

    semester_counts = {}

    # Patterns suggesting which期 the student belongs to
    student_semester_re = re.compile(
        r'(我.*[是参加购买报名].*?([一二三四五1-5]|4\.5)期|'
        r'([一二三四五1-5]|4\.5)期.*[学员学习]|'
        r'[第]?([一二三四五1-5]|4\.5)期.*[的复训])',
        re.IGNORECASE
    )

    for msg in msgs:
        if msg.get('isSelf', 1):
            continue
        content = decode_content(msg.get('content', ''))
        if not content:
            continue

        m = student_semester_re.search(content)
        if m:
            # Extract the digit/character
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


def build_student_index(students):
    by_nick, by_wxid, by_alt = {}, {}, {}
    for s in students:
        if s['微信昵称']: by_nick[s['微信昵称']] = s
        if s['wxid']: by_wxid[s['wxid']] = s
        m = re.search(r'微信号:([^\s|]+)', s['其他名称'])
        if m: by_alt[m.group(1)] = s
        m2 = re.search(r'备注:([^\s|]+)', s['其他名称'])
        if m2: by_alt[m2.group(1)] = s
    return by_nick, by_wxid, by_alt


def find_student(raw_name, by_nick, by_wxid, by_alt, students):
    if raw_name in by_nick: return by_nick[raw_name]
    if raw_name in by_wxid: return by_wxid[raw_name]
    if raw_name in by_alt: return by_alt[raw_name]
    parts = [p.strip() for p in raw_name.split('/') if p.strip()]
    for p in parts:
        if p in by_nick: return by_nick[p]
        if p in by_wxid: return by_wxid[p]
        if p in by_alt: return by_alt[p]
        for s in students:
            if p and (p in s['微信昵称'] or p in s['wxid'] or p in s['其他名称']):
                return s
    paren = re.match(r'^(.+?)[\(（](.+?)[\)）]$', raw_name)
    if paren:
        outside, inside = paren.group(1).strip(), paren.group(2).strip()
        wid = re.search(r'微信号[:\s：]+(\S+)', inside)
        if wid:
            k = wid.group(1)
            if k in by_wxid: return by_wxid[k]
            if k in by_alt: return by_alt[k]
        for c in [outside, inside]:
            if c in by_nick: return by_nick[c]
            if c in by_wxid: return by_wxid[c]
            if c in by_alt: return by_alt[c]
            for s in students:
                if c and (c in s['微信昵称'] or c in s['wxid'] or c in s['其他名称']):
                    return s
    return None


def main():
    print("Loading data...")
    with open(STUDENT_FILE) as f:
        students = json.load(f)

    staff_exclude = load_staff_exclude()

    # Add 自我介绍 field if not present
    for s in students:
        if '自我介绍' not in s:
            s['自我介绍'] = ''

    # Build message file index: wxid -> filepath
    print("Indexing message files...")
    msg_index = {}
    for fpath in glob.glob(os.path.join(DATA_DIR, "messages_user_*.json")):
        try:
            with open(fpath) as f:
                d = json.load(f)
            uid = d.get('userId', '')
            if uid:
                msg_index[uid] = fpath
        except:
            pass
    print(f"  {len(msg_index)} message files indexed")

    # Scan private messages for intros and semester
    print("Scanning private messages...")
    intro_found = 0
    semester_inferred = 0

    for s in students:
        wxid = s['wxid']
        if wxid not in msg_index:
            continue
        try:
            with open(msg_index[wxid]) as f:
                d = json.load(f)
        except:
            continue

        msgs = d.get('messages', [])
        if not msgs:
            continue

        # Extract self-introduction
        if not s['自我介绍']:
            intro = extract_intro_from_messages(msgs, wxid)
            if intro:
                s['自我介绍'] = intro
                intro_found += 1

        # Infer semester if missing
        if not s['学期']:
            inferred = infer_semester_from_messages(msgs, s['学期'])
            if inferred:
                s['学期'] = inferred
                semester_inferred += 1

    print(f"  自我介绍 extracted from messages: {intro_found}")
    print(f"  学期 inferred from messages: {semester_inferred}")

    # Final stats
    total_intro = sum(1 for s in students if s['自我介绍'])
    total_semester = sum(1 for s in students if s['学期'])
    print(f"\nFinal stats:")
    print(f"  有自我介绍: {total_intro}/{len(students)}")
    print(f"  有学期字段: {total_semester}/{len(students)}")

    sem_dist = {}
    for s in students:
        k = s['学期'] or '(空)'
        sem_dist[k] = sem_dist.get(k, 0) + 1
    print("  学期分布:", dict(sorted(sem_dist.items())))

    with open(STUDENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(students, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {STUDENT_FILE}")


if __name__ == '__main__':
    main()
