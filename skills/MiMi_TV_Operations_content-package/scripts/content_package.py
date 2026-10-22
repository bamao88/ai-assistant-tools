#!/usr/bin/env python3
"""MiMi account helpers for MiMi_TV_Operations_content-package: novelty audit and local review bundle."""
import argparse
import csv
import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse

BLOCKED_PUBLICATIONS = {'published', 'scheduled', 'draft-uploaded'}
ACTIVE_ITEMS = {'draft', 'review', 'ready'}
# Tools live together in this Skill; --project selects the content library.
CHECKER_SCRIPTS = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def resolve(root, value):
    p = Path(value).expanduser()
    return (p if p.is_absolute() else root / p).resolve()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def url_key(raw):
    u = urlparse(raw.strip())
    host = (u.hostname or '').lower().removeprefix('www.').removeprefix('m.')
    if host in {'youtube.com', 'youtu.be', 'youtube-nocookie.com'}:
        parts = u.path.strip('/').split('/')
        video = (parts[0] if host == 'youtu.be' else
                 parse_qs(u.query).get('v', [''])[0] if u.path == '/watch' else
                 parts[1] if len(parts) == 2 and parts[0] in {'shorts', 'embed', 'live'} else '')
        if video:
            return 'youtube:' + video
    return urlunparse((u.scheme.lower(), host, u.path.rstrip('/'), '', u.query, ''))


def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def identity(item, materials, root):
    source = item.get('source') or {}
    keys = set()
    material_id = source.get('material_id')
    if material_id:
        keys.add('material:' + material_id)
    material = materials.get(material_id, {})
    for url in [source.get('url'), material.get('source_url')]:
        if url:
            keys.add('url:' + url_key(url))
    for field, prefix in [('local_file', 'path:'), ('sha256', 'file-sha:')]:
        if source.get(field):
            value = str(resolve(root, source[field])) if field == 'local_file' else source[field].lower()
            keys.add(prefix + value)
    if material.get('source_path'):
        keys.add('path:' + str(resolve(root, material['source_path'])))
    if (item.get('video') or {}).get('sha256'):
        keys.add('file-sha:' + item['video']['sha256'].lower())
    return keys


def load_selection(root, path):
    selection = read_json(path)
    if not selection.get('batch_id') or type(selection.get('requested_count')) is not int or selection['requested_count'] < 1:
        raise ValueError('selection 需要 batch_id 和正整数 requested_count')
    loaded = []
    for number, entry in enumerate(selection['items'], 1):
        p = resolve(root, entry['item_json']) if 'item_json' in entry else None
        d = read_json(p) if p else entry
        identifier = d.get('item_id') or d.get('candidate_id') or f'candidate-{number}'
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', identifier):
            raise ValueError('item/candidate ID 不可用作安全目录名')
        loaded.append((identifier, p, d))
    return selection, loaded


def audit(root, selection, loaded):
    materials = {r['id']: r for r in csv_rows(root / 'materials/index.csv')}
    publications = csv_rows(root / 'content/publications.csv')
    history = {}
    for p in sorted((root / 'content/items').glob('*/item.json')):
        d = read_json(p)
        if d['item_id'] in history:
            raise ValueError('作品 ID 不唯一：' + d['item_id'])
        history[d['item_id']] = d
    pub_by_item = {}
    for pub in publications:
        if pub['status'] not in BLOCKED_PUBLICATIONS | {'planned', 'failed', 'cancelled'}:
            raise ValueError('未知发布状态，先核查：' + pub['id'])
        pub_by_item.setdefault(pub['item_id'], []).append(pub)
        if pub['status'] in BLOCKED_PUBLICATIONS | {'planned'} and pub['item_id'] not in history:
            raise ValueError('发布记录缺少可追溯 item，需先补齐来源：' + pub['id'])
    selected_ids = {identifier for identifier, _, _ in loaded}
    results, seen = [], []
    for identifier, _, d in loaded:
        errors, matches = [], []
        source = d.get('source') or {}
        if d.get('content_type') != 'external_passive_video':
            errors.append('非当前外部被动视频类型；产品素材不得自动进入此流程')
        for field in ['platform', 'kind', 'channel', 'original_title', 'url', 'usage_basis', 'rights_status']:
            if not source.get(field):
                errors.append('缺少 source.' + field)
        if source.get('kind') != 'external':
            errors.append('只接收外部来源')
        material_id = source.get('material_id')
        if material_id and material_id not in materials:
            errors.append('素材 ID 未登记，须先核对真实来源')
        material_kind = materials.get(material_id, {}).get('kind', '')
        if material_kind and material_kind not in {'external-video', 'external-video-candidate'}:
            errors.append('素材台账并非外部视频来源，不能用 source.kind 重标为可用')
        parsed = urlparse(source.get('url', ''))
        youtube = url_key(source.get('url', '')).startswith('youtube:')
        exception = source.get('exception_approval') or {}
        if not (source.get('platform', '').lower() == 'youtube' and youtube):
            if not (exception.get('approved_by') == 'project_owner' and exception.get('approved_at') and exception.get('scope')):
                errors.append('非 YouTube 来源须有本条负责人单项批准')
        if parsed.scheme not in {'https', 'http'} or not parsed.hostname:
            errors.append('来源 URL 不完整')
        if d.get('status') == 'archived':
            errors.append('本 item 已归档撤回，不能进入新交付')
        keys = identity(d, materials, root)
        for old_id, old in history.items():
            overlap = keys & identity(old, materials, root)
            same_id = old_id == identifier
            pubs = [p for p in pub_by_item.get(old_id, []) if p['status'] in BLOCKED_PUBLICATIONS | {'planned'}]
            reserved = old_id not in selected_ids and old.get('status') in ACTIVE_ITEMS
            if (same_id or overlap) and (pubs or reserved):
                matches.append({'matched_item_id': old_id,
                                'reason': 'previous-publication-or-platform-plan' if pubs else 'already-in-production',
                                'identity': sorted(overlap) if overlap else ['item_id:' + old_id],
                                'publications': [{k: p[k] for k in ['id', 'platform_account_id', 'status']} for p in pubs]})
        for other_id, other_keys in seen:
            if keys & other_keys or other_id == identifier:
                matches.append({'matched_item_id': other_id, 'reason': 'duplicate-in-this-selection',
                                'identity': sorted(keys & other_keys), 'publications': []})
        seen.append((identifier, keys))
        if matches:
            errors.append('存在已用、已排期、在制或本批重复内容；不能计为新增')
        results.append({'item_id': identifier, 'eligible': not errors, 'errors': errors, 'matches': matches})
    eligible = sum(r['eligible'] for r in results)
    return {'batch_id': selection['batch_id'], 'verification_level': 'logic/contract with recorded publication evidence',
            'requested_count': selection['requested_count'], 'candidate_count': len(results),
            'eligible_count': eligible, 'shortfall': max(0, selection['requested_count'] - eligible),
            'passed': bool(results) and all(r['eligible'] for r in results) and eligible >= selection['requested_count'],
            'items': results, 'limitations': ['不是自动视觉查重；原链接或哈希不同仍须人工对照内容',
                                            '定时状态按现有证据排除，不推断已经公开',
                                            '未核验原作者商业授权，不代表视觉/有声审看或平台 E2E']}


def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]))


def source_file(root, d):
    source = d['source']
    p = resolve(root, source['local_file'])
    if not source.get('sha256') or sha(p) != source['sha256']:
        raise ValueError('原片真实哈希与来源记录不符：' + str(p))
    return p


def asset(item_path, raw):
    if Path(raw).is_absolute() or '..' in Path(raw).parts:
        raise ValueError('最终媒体须使用 item 内的相对路径：' + raw)
    p = resolve(item_path.parent, raw)
    if not p.is_relative_to(item_path.parent):
        raise ValueError('最终媒体必须位于 item 内：' + raw)
    return p


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def verify_item(root, p, d):
    source = source_file(root, d)
    for kind in ['video', 'cover']:
        record = d[kind]
        file = asset(p, record['file'])
        if not record.get('sha256') or sha(file) != record['sha256']:
            raise ValueError(kind + ' 哈希不符：' + str(file))
    video = asset(p, d['video']['file'])
    metadata = probe(video)
    stream = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
    if (stream['width'], stream['height']) != (d['video']['width'], d['video']['height']):
        raise ValueError('成片尺寸与 item 不符')
    if abs(float(metadata['format']['duration']) - d['video']['duration_seconds']) > 0.15:
        raise ValueError('成片时长与 item 不符')
    expected_duration = d['segment']['end_seconds'] - d['segment']['start_seconds']
    if abs(float(metadata['format']['duration']) - expected_duration) > 0.25:
        raise ValueError('成片时长与选段不符')
    original = probe(source)
    if not 0 <= d['segment']['start_seconds'] < d['segment']['end_seconds'] <= float(original['format']['duration']) + 0.05:
        raise ValueError('选段超出原片时长')
    original_stream = next(s for s in original['streams'] if s['codec_type'] == 'video')
    if (stream['width'], stream['height']) != (original_stream['width'], original_stream['height']):
        raise ValueError('成片改变原片画幅尺寸，须另行核对制作要求')
    if any(s['codec_type'] == 'audio' for s in original['streams']) != any(s['codec_type'] == 'audio' for s in metadata['streams']):
        raise ValueError('成片原声轨道缺失或新增')
    run(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(video), '-map', '0:v', '-map', '0:a?', '-f', 'null', '-'])
    cover = module(CHECKER_SCRIPTS / 'check_cover_package.py', 'cover_check')
    copy = module(CHECKER_SCRIPTS / 'check_copy_package.py', 'copy_check')
    errors = cover.validate_manifest(p, False) + copy.validate(p)
    if errors:
        raise ValueError(d['item_id'] + ': ' + '; '.join(errors))
    exporter = module(CHECKER_SCRIPTS / 'export_publish_packages.py', 'mimi_export')
    exports = exporter.render(d)
    for name, expected in exports.items():
        if (p.parent / name).read_text(encoding='utf-8') != expected:
            raise ValueError('导出与 item 不一致：' + name)
    return exports


def bundle(root, selection, loaded, report, out):
    if out.exists():
        raise ValueError('拒绝覆盖交付目录：' + str(out))
    verified = []
    for identifier, p, d in loaded:
        if p is None:
            raise ValueError('交付需要落盘 item_json：' + identifier)
        verified.append((p, d, verify_item(root, p, d)))
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.mimi-package-', dir=out.parent) as tmp:
        stage = Path(tmp) / 'bundle'
        stage.mkdir()
        cards, records = [], []
        esc = html.escape
        for p, d, exports in verified:
            target = stage / 'items' / d['item_id']
            target.mkdir(parents=True)
            # Canonical final files and their explicit variants only; never recursive work/archive copies.
            media = [d['video']['file'], d['cover']['file']]
            media += [v for k, v in d['cover'].get('platform_variants', {}).items()
                      if k in {'4:3', '16:9', '3:4'} and isinstance(v, str)]
            evidence = []
            bg = d['cover'].get('background', {})
            refs = [bg.get('asset'), bg.get('prompt_log')] + bg.get('reference_assets', [])
            for number, raw in enumerate(filter(None, refs)):
                ref = resolve(p.parent, raw)
                if not ref.is_file() or ref.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp', '.txt'}:
                    raise ValueError('封面证据缺失或格式不适用：' + raw)
                relative = Path('evidence') / (str(number) + ref.suffix.lower())
                (target / relative).parent.mkdir(exist_ok=True)
                shutil.copy2(ref, target / relative)
                evidence.append({'original_reference': raw, 'file': str(relative), 'sha256': sha(ref)})
            write_json(target / 'item.json', d)
            write_json(target / 'cover-evidence.json', evidence)
            for raw in media:
                dest = target / raw
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset(p, raw), dest)
            for name, content in exports.items():
                (target / name).write_text(content, encoding='utf-8')
            base = 'items/' + d['item_id'] + '/'
            body = ''.join('<p>' + esc(part) + '</p>' for part in d['copy']['body'].split('\n\n'))
            cards.append('<article><h2>' + esc(d['copy']['post_title']) + '</h2><img src="' + esc(base + d['cover']['file'], quote=True)
                         + '"><video controls preload="metadata" src="' + esc(base + d['video']['file'], quote=True) + '"></video>'
                         + '<p>封面：' + esc(d['cover']['cover_title']) + ' · 频道 ' + f"{d['cover']['channel_number']:02d}" + '</p>'
                         + body + '<p>话题：' + esc(' · '.join(d['copy']['keywords'])) + '</p><details><summary>来源与检查</summary><p>'
                         + esc(d['copy']['source_credit']) + '</p><a href="' + esc(d['source']['url'], quote=True)
                         + '">原视频</a><pre>' + esc(json.dumps(d.get('checks', {}), ensure_ascii=False, indent=2)) + '</pre></details></article>')
            records.append({'item_id': d['item_id'], 'status': 'review', 'checks': d.get('checks', {}), 'cover_evidence': evidence})
        manifest = {'batch_id': selection['batch_id'], 'status': 'review', 'publication_permission': 'no-publishing',
                    'item_count': len(records), 'requested_count': selection['requested_count'], 'items': records,
                    'verification': {'novelty_and_exports': 'logic/contract', 'files': 'real file hash/probe/full decode',
                                     'visual_and_audio_acceptance': 'see per-item checks; not granted by script',
                                     'platform_E2E': 'not-performed', 'product_acceptance': 'not-granted-by-script'}}
        write_json(stage / 'manifest.json', manifest)
        write_json(stage / 'novelty-audit.json', report)
        page = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>视频素材包审阅</title><style>body{font:17px system-ui;max-width:1000px;margin:24px auto;padding:16px;background:#fffdf4}article{margin:32px 0;padding:20px;border:1px solid #ddd}img{width:min(240px,100%);vertical-align:top}video{width:min(600px,100%)}pre{white-space:pre-wrap}p{line-height:1.7}</style><h1>' + esc(selection['batch_id']) + '</h1><p>本地待审素材包 · 未上传或发布；逐条验收范围见检查记录。</p><a href="package.zip" download>下载素材包</a>' + ''.join(cards)
        (stage / 'index.html').write_text(page, encoding='utf-8')
        files = sorted(f for f in stage.rglob('*') if f.is_file())
        manifest['files'] = {str(f.relative_to(stage)): sha(f) for f in files if f.name != 'manifest.json'}
        write_json(stage / 'manifest.json', manifest)
        with zipfile.ZipFile(stage / 'package.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(stage.rglob('*')):
                if file.is_file() and file.name != 'package.zip':
                    archive.write(file, str(file.relative_to(stage)))
        stage.rename(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['audit', 'bundle'])
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        root = args.project.expanduser().resolve()
        selection, loaded = load_selection(root, args.selection)
        report = audit(root, selection, loaded)
        if args.output:
            write_json(args.output, report)
        if args.command == 'audit':
            print(json.dumps(report, ensure_ascii=False, indent=2))
        if not report['passed']:
            if args.command != 'audit':
                print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2
        if args.command == 'bundle':
            if args.out is None:
                raise ValueError('bundle 需要 --out')
            bundle(root, selection, loaded, report, args.out.expanduser().resolve())
            print('Local review bundle:', args.out)
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError, StopIteration) as exc:
        print('未完成：', str(exc))
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stderr[-2000:])
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
