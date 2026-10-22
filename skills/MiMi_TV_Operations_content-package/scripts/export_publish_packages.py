#!/usr/bin/env python3
"""Export item copy to the existing assistant_zh/platform-publish Markdown contract.

Local files only. No browser, credentials, upload or submission capability.
Existing packages are preserved unless --replace is explicitly supplied.
"""
import argparse
import json
from pathlib import Path


def quoted(value):
    return json.dumps(value, ensure_ascii=False)


def block(name, value):
    return name + ': |\n' + '\n'.join('  ' + line for line in value.split('\n')) + '\n'


def platform_body(c, platform):
    """默认正文；有该平台改写的结尾互动段时，替换最后一段。"""
    cta = c.get('body_cta', '').strip()
    override = c.get('platform_overrides', {}).get(platform, {}).get('body_cta', '').strip()
    body = c['body']
    if cta and override and body.endswith(cta):
        return body[:-len(cta)] + override
    return body


def render(item):
    c = item['copy']
    body, title, tags = c['body'], c['post_title'], c['keywords']
    dy_body, bili_body = platform_body(c, 'douyin'), platform_body(c, 'bilibili')
    xhs_plan = item.get('publication_plans', {}).get('xiaohongshu', {})
    xhs_actions = xhs_plan.get('optional_platform_actions', {})
    if not isinstance(xhs_actions, dict):
        raise ValueError('xiaohongshu.optional_platform_actions 必须是对象')
    quote_choice = xhs_actions.get('quote_source_note')
    if quote_choice is True:
        authorization = xhs_actions.get('quote_source_note_authorization', '').strip()
        if not authorization:
            raise ValueError('引用原笔记须记录本条明确授权；不能从来源字段自动导出')
        quote_note = '本条明确要求关联原笔记；先核对原笔记作者、标题与授权依据。'
    elif quote_choice is False:
        quote_note = '本条已明确不关联原笔记。'
    elif quote_choice is None:
        quote_note = '未指定关联原笔记；不执行引用。'
    else:
        raise ValueError('quote_source_note 必须是 true 或 false')
    if '链接' in c.get('body_cta', ''):
        quote_note += '\n正文提到「点击链接」：发布时必须在笔记上挂对应游戏小工具链接并读回确认；挂不上就改正文，不发带「点击链接」的文案。'
    if str(xhs_plan.get('execution_status', '')).startswith('paused-by-owner'):
        quote_note += '\n本条发布处理已暂停，不能沿用旧授权提交。'
    # Input prose is checked by this Skill's copy checker; never concatenate source/tags.
    common = (
        'account: mimi_tv\nform: video\n'
        f"video: {quoted(item['video']['file'])}\n"
        f"cover: {quoted(item['cover']['file'])}\n"
        'published: draft\n'
    )
    source = ('\n## 来源核对资料（不进正文）\n\n' + c['source_credit']
              + '\n\n' + item['source']['url'] + '\n')
    fact_sources = c.get('fact_sources', [])
    if fact_sources:
        source += '\n## 正文知识核对资料（不进正文）\n\n'
        source += '\n'.join(
            '- ' + entry['title'] + '：' + entry['url']
            for entry in fact_sources
        ) + '\n\n知识按来源转述；不复制原文段落或插图，不代表原文章转载授权。\n'
    pinned = c.get('pinned_comment', '').strip()
    if pinned:
        # 发布后由账号自己发出并置顶；不进正文，发评论按当次授权执行。
        source += '\n## 置顶评论（发布后由账号发出，不进正文）\n\n' + pinned + '\n'
    tags_used = c.get('strategy_tags')
    if tags_used:
        source += '\n策略标签（内部）：' + '、'.join(tags_used) + '\n'
    notes = ('\n## 内部审核备注（不发布）\n\n'
             '由 item.json 导出；draft 仅表示本地发布包，不表示平台已保存草稿。'
             '排期读取 item.json 的建议值，执行前确认有效性和提交授权。'
             '平台必填来源字段及封面裁切仍需平台预览；来源资料不构成引用原笔记的指令。\n')
    xhs = ('---\nplatform: xiaohongshu\n' + common
           + f'title: {quoted(title)}\n'
           + block('abstract', body) + block('description', body)
           + 'keywords:\n' + ''.join('  - ' + quoted(t) + '\n' for t in tags)
           + '---\n\n## 标题候选\n\n- ✅ ' + title
           + '\n\n## 正文\n\n' + body + '\n' + source
           + '\n## 小红书可选关联\n\n' + quote_note + '\n' + notes)
    dy = ('---\nplatform: douyin\n' + common
          + f'caption: {quoted(title)}\n'
          + 'tags: ' + quoted(tags[:5]) + '\n'
          + f"cover_portrait: {quoted(item['cover']['file'])}\n"
          + 'declaration: 内容为转载信息\n---\n\n## 文案 caption\n\n' + title
          + '\n\n## 正文\n\n' + dy_body + '\n'
          + '\n## 自主声明\n\n内容为转载信息 → 取材站外\n' + source + notes)
    landscape = item['cover'].get('platform_variants', {}).get('4:3')
    if landscape:
        dy = dy.replace('declaration: 内容为转载信息', 'cover_landscape: ' + quoted(landscape) + '\ndeclaration: 内容为转载信息')
    # No invented category: CLI submission stays blocked until a verified tid exists.
    bili_overrides = c.get('platform_formatting', {}).get('bilibili', {})
    tid = bili_overrides.get('tid')
    source_url = bili_overrides.get('source_field_value', item['source']['url'])
    bili = ('---\nplatform: bilibili\n' + common
            + f'title: {quoted(title)}\n'
            + 'tid: ' + (str(tid) if tid is not None else 'null') + '\n'
            + 'tags: ' + quoted(','.join(tags)) + '\n'
            + 'copyright: 2\nsource: ' + quoted(source_url)
            + '\n---\n\n## 简介 desc\n\n' + bili_body + '\n' + source + notes)
    brief = ('# Core Brief\n\n## 来源\n\n'
             + f"- 源稿：item.json（{item['item_id']}）\n- 内容形态：video\n"
             + '- 目标平台：小红书、抖音、Bilibili\n\n## 一句话核心判断\n\n'
             + body.split('\n')[0] + '\n\n## 标题种子\n\n- ' + title
             + '\n\n## 封面标题种子\n\n- ' + item['cover']['cover_title']
             + '\n\n## 发布页正文素材\n\n' + body
             + '\n\n## 关键词候选池\n\n' + '；'.join(tags)
             + '\n\n## 禁用内容\n\n不虚构原创、官方身份、授权或功效。'
             + '来源与剪辑说明不进正文。\n\n## 同步依据\n\n'
             + '项目 AGENTS.md：同一作品多平台默认同步已确认内容，仅适配平台限制。\n')
    return {'core_brief.md': brief, 'publish_mimi_xhs.md': xhs,
            'publish_mimi_douyin.md': dy, 'publish_mimi_bilibili.md': bili}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('items', nargs='+', type=Path)
    parser.add_argument('--replace', action='store_true', help='Replace existing local exports')
    args = parser.parse_args()
    for path in args.items:
        item = json.loads(path.read_text())
        for name, text in render(item).items():
            target = path.parent / name
            if target.exists() and not args.replace:
                print('preserved', target)
                continue
            target.write_text(text, encoding='utf-8')
            print('exported', target)


if __name__ == '__main__':
    main()
