#!/usr/bin/env python3
"""
从 Markdown 文件提取 frontmatter 并输出 JSON。
用法：python extract_frontmatter.py <markdown_file> [--save-dir /tmp]

输出 JSON 格式：
{
  "title": "...",
  "abstract": "...",
  "keywords": ["kw1", "kw2", ...],
  "body": "正文...",
  "markdown_for_cards": "# 标题\n\n正文...",
  "description": "摘要前200字...",
  "valid": true,
  "errors": []
}

加 --save-dir 时，自动保存临时文件并追加路径到 JSON：
  "files": {
    "title_file": "/tmp/xhs_la_title.txt",
    "body_file": "/tmp/xhs_la_body.txt",
    "desc_file": "/tmp/xhs_la_desc.txt",
    "cards_md_file": "/tmp/xhs_cards_src.md"
  }
"""

import sys
import os
import json
import re
import time


def extract(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    errors = []

    # --- 分离 frontmatter 和正文 ---
    lines = content.split('\n')
    fm_lines = []
    body_start = 0
    sep_count = 0

    for i, line in enumerate(lines):
        if line.strip() == '---':
            sep_count += 1
            if sep_count == 2:
                body_start = i + 1
                break
        elif sep_count == 1:
            fm_lines.append(line)

    if sep_count < 2:
        errors.append('frontmatter 格式错误：未找到两个 --- 分隔符')
        fm_text = ''
        body = content
    else:
        fm_text = '\n'.join(fm_lines)
        body = '\n'.join(lines[body_start:]).strip()

    # --- 提取 title ---
    title = ''
    m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', fm_text, re.MULTILINE)
    if m:
        title = m.group(1).strip().strip('"').strip("'")
    if not title:
        # fallback: 正文第一行 # 标题
        m2 = re.match(r'^#\s+(.+)', body)
        if m2:
            title = m2.group(1).strip()
    if not title:
        errors.append('title 为空')

    # --- 提取 abstract ---
    abstract = ''
    # 方式1: 多行 abstract: |（支持段间空行）
    # 匹配从 abstract: | 到下一个顶层 key（行首非空格字符+冒号）之间的所有内容
    m = re.search(r'^abstract:\s*\|\s*\n((?:(?:[ \t]+.*|[ \t]*)\n)*)', fm_text, re.MULTILINE)
    if m:
        raw = m.group(1)
        # 保留段间空行作为换行，去掉每行的缩进
        stripped_lines = []
        for line in raw.split('\n'):
            s = line.strip()
            stripped_lines.append(s)
        # 去尾部空行，拼接
        while stripped_lines and not stripped_lines[-1]:
            stripped_lines.pop()
        abstract = '\n'.join(stripped_lines)
    else:
        # 方式2: 单行 abstract: "xxx"
        m = re.search(r'^abstract:\s*["\']?(.+?)["\']?\s*$', fm_text, re.MULTILINE)
        if m:
            abstract = m.group(1).strip()

    if len(abstract) <= 20:
        errors.append(f'abstract 太短（{len(abstract)}字，需 >20）')

    # --- 提取 keywords ---
    keywords = []
    m = re.search(r'^keywords:\s*\n((?:[ \t]*-\s+.+\n?)+)', fm_text, re.MULTILINE)
    if m:
        raw_kw = m.group(1)
        for line in raw_kw.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                kw = line[2:].strip().strip('"').strip("'")
                # 关键词中的空格替换为无空格（小红书话题不支持空格）
                kw_clean = kw.replace(' ', '')
                keywords.append(kw_clean)

    if len(keywords) < 3:
        errors.append(f'keywords 不足（{len(keywords)}个，需 >=3）')

    # --- 正文验证 ---
    if len(body) <= 100:
        errors.append(f'body 太短（{len(body)}字，需 >100）')

    # --- 组装输出 ---
    # 将单换行转为双换行，确保 markdown 解析器能正确分段生成多个 <p>
    body_for_cards = re.sub(r'\n(?!\n)', '\n\n', body)
    # 清理可能出现的多余空行
    body_for_cards = re.sub(r'\n{3,}', '\n\n', body_for_cards)
    markdown_for_cards = f'# {title}\n\n{body_for_cards}' if title else body_for_cards
    description = abstract[:200] + ('...' if len(abstract) > 200 else '')

    if not markdown_for_cards.startswith('# '):
        errors.append('markdown_for_cards 不以 "# " 开头')

    # 占位检查
    for field_name, val in [('title', title), ('abstract', abstract)]:
        if any(bad in val for bad in ['占位', 'xxx', 'XXX', 'placeholder']):
            errors.append(f'{field_name} 包含占位内容')

    result = {
        'title': title,
        'abstract': abstract,
        'keywords': keywords,
        'keywords_original': [re.sub(r'^\s*-\s+', '', line).strip().strip('"').strip("'")
                              for line in (m.group(1) if m else '').split('\n')
                              if line.strip().startswith('-')] if m else [],
        'body': body,
        'markdown_for_cards': markdown_for_cards,
        'description': description,
        'valid': len(errors) == 0,
        'errors': errors,
    }

    return result


def save_temp_files(result, save_dir):
    """保存临时文件，返回文件路径 dict"""
    ts = int(time.time())
    os.makedirs(save_dir, exist_ok=True)

    files = {}

    # 标题
    p = os.path.join(save_dir, f'xhs_la_title_{ts}.txt')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(result['title'])
    files['title_file'] = p

    # body（long-article 占位用）
    p = os.path.join(save_dir, f'xhs_la_body_{ts}.txt')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('占位内容')  # long-article content-file 仅触发编辑器
    files['body_file'] = p

    # 描述
    p = os.path.join(save_dir, f'xhs_la_desc_{ts}.txt')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(result['description'])
    files['desc_file'] = p

    # 卡片用 markdown
    p = os.path.join(save_dir, f'xhs_cards_src_{ts}.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(result['markdown_for_cards'])
    files['cards_md_file'] = p

    return files


def main():
    if len(sys.argv) < 2:
        print('用法: python extract_frontmatter.py <markdown_file> [--save-dir /tmp]', file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    save_dir = None

    if '--save-dir' in sys.argv:
        idx = sys.argv.index('--save-dir')
        if idx + 1 < len(sys.argv):
            save_dir = sys.argv[idx + 1]

    if not os.path.isfile(filepath):
        print(json.dumps({'valid': False, 'errors': [f'文件不存在: {filepath}']},
                         ensure_ascii=False))
        sys.exit(1)

    result = extract(filepath)

    if save_dir and result['valid']:
        result['files'] = save_temp_files(result, save_dir)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
