#!/usr/bin/env python3
"""Contract tests with synthetic history and locally generated media; no platform operations."""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import content_package as package


def source(video='fresh000001'):
    return {'kind': 'external', 'platform': 'youtube', 'channel': 'Synthetic fixture',
            'original_title': 'Synthetic fixture for tests only', 'url': 'https://www.youtube.com/watch?v=' + video,
            'usage_basis': 'synthetic contract fixture only', 'rights_status': 'test-fixture-no-publication'}


def candidate(identifier='candidate-new', video='fresh000001'):
    return {'candidate_id': identifier, 'content_type': 'external_passive_video', 'source': source(video)}


def table(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class Novelty(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = {'item_id': 'item-old', 'content_type': 'external_passive_video', 'status': 'ready',
                    'source': source('already0001'), 'video': {'sha256': 'clip-hash'}}
        self.old['source'].update(sha256='original-hash', material_id='material-old', local_file='/old/path.mp4')
        p = self.root / 'content/items/old/item.json'
        p.parent.mkdir(parents=True)
        package.write_json(p, self.old)
        table(self.root / 'materials/index.csv', ['id', 'source_url', 'source_path'],
              [{'id': 'material-old', 'source_url': self.old['source']['url'], 'source_path': '/moved/path.mp4'}])
        self.publications('published')

    def publications(self, status):
        table(self.root / 'content/publications.csv', ['id', 'item_id', 'platform_account_id', 'status'],
              [{'id': 'pub-old', 'item_id': 'item-old', 'platform_account_id': 'xhs', 'status': status}])

    def audit(self, candidates, count=None):
        loaded = [(d.get('candidate_id', d.get('item_id')), None, d) for d in candidates]
        return package.audit(self.root, {'batch_id': 'contract', 'requested_count': count or len(candidates)}, loaded)

    def test_new_source_same_animal_is_valid(self):
        self.assertTrue(self.audit([candidate()])['passed'])

    def test_alias_url_and_new_timecode_still_duplicate(self):
        for url in ['https://youtu.be/already0001?t=500', 'https://m.youtube.com/watch?v=already0001&list=PL',
                    'https://www.youtube.com/shorts/already0001', 'https://www.youtube.com/embed/already0001']:
            d = candidate(); d['source']['url'] = url
            d['segment'] = {'start_seconds': 500, 'end_seconds': 530}
            self.assertFalse(self.audit([d])['passed'])

    def test_different_link_same_source_or_old_export_hash(self):
        for digest in ['original-hash', 'clip-hash']:
            d = candidate(); d['source']['sha256'] = digest
            self.assertFalse(self.audit([d])['passed'])

    def test_moved_file_and_material_alias_match(self):
        for changes in [{'local_file': '/moved/path.mp4'}, {'material_id': 'material-old'}]:
            d = candidate(); d['source'].update(changes)
            self.assertFalse(self.audit([d])['passed'])

    def test_scheduled_and_planned_do_not_pass(self):
        for status in ['scheduled', 'draft-uploaded', 'planned']:
            self.publications(status)
            d = candidate(video='already0001')
            self.assertFalse(self.audit([d])['passed'])

    def test_cancelled_archived_without_other_publication_can_be_reconsidered(self):
        self.publications('cancelled')
        self.old['status'] = 'archived'
        package.write_json(self.root / 'content/items/old/item.json', self.old)
        self.assertTrue(self.audit([candidate(video='already0001')])['passed'])

    def test_batch_duplicates_and_shortfall(self):
        report = self.audit([candidate('one'), candidate('two')], count=7)
        self.assertEqual(report['eligible_count'], 1)
        self.assertEqual(report['shortfall'], 6)
        self.assertFalse(report['passed'])

    def test_source_boundary_and_missing_author(self):
        for d in [candidate(), candidate()]:
            d['source']['channel'] = ''
            self.assertFalse(self.audit([d])['passed'])
        d = candidate(); d['source']['platform'] = 'xiaohongshu'
        self.assertFalse(self.audit([d])['passed'])

    def test_in_production_blocks_but_self_does_not(self):
        self.publications('failed')
        self.assertFalse(self.audit([candidate(video='already0001')])['passed'])
        self.assertTrue(self.audit([self.old])['passed'])

    def test_published_self_always_blocks(self):
        self.assertFalse(self.audit([self.old])['passed'])


class TitlePrefix(unittest.TestCase):
    def errors_for(self, title):
        import check_copy_package as checker
        item = {'item_id': 'item-001', 'status': 'draft', 'content_type': 'external_passive_video', 'object': '蚱蜢',
                'source': source(), 'segment': {'mode': 'clip', 'start_seconds': 0, 'end_seconds': 1, 'continuous': True},
                'copy': {'post_title': title, 'title_strategy_id': 'object-search', 'benchmark_refs': ['BO-001'],
                         'body': '蚱蜢在浅色画面里跳动、停留，再换个方向。\n\n点开全屏就可以给猫咪看，手机能直接播放。',
                         'keywords': ['猫', '猫咪电视', '猫咪动画片', '猫咪日常', '蚱蜢', '昆虫', '猫猫看电视'],
                         'source_credit': '素材来源：YouTube，本条为片段剪辑。'}}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'item.json'
            package.write_json(path, item)
            return [e for e in checker.validate(path) if 'post_title' in e]

    def test_fixed_prefix_required(self):
        self.assertEqual(self.errors_for('给猫看的动画片| 蚱蜢跳跳停停'), [])
        for bad in ('给猫咪看的蚱蜢动画片', '给猫看的动画片｜ 蚱蜢跳跳停停', '给猫看的动画片|蚱蜢跳跳停停',
                    '给猫看的动画片|  蚱蜢跳跳停停', '给猫看的动画片| '):
            self.assertTrue(self.errors_for(bad), bad)


class EngagementHook(unittest.TestCase):
    def test_pinned_comment_and_strategy_tags(self):
        import check_copy_package as checker
        good = '你想让哪种小动物也变成游戏？评论区留名字。'
        self.assertEqual(checker.validate_engagement({'pinned_comment': good, 'strategy_tags': ['E1']}), [])
        self.assertEqual(checker.validate_engagement({}), [])
        for bad in ({'pinned_comment': '点赞够100人我就做游戏'}, {'pinned_comment': '看 https://a.cn'},
                    {'pinned_comment': '想看哪个？想玩哪个？'}, {'pinned_comment': '所有猫都爱'},
                    {'pinned_comment': '字' * 121}, {'pinned_comment': ' '}, {'strategy_tags': ['E9']},
                    {'strategy_tags': ['E1', 'E1']}, {'strategy_tags': []}):
            self.assertTrue(checker.validate_engagement(bad), bad)

    def test_platform_override_rules(self):
        import check_copy_package as checker
        base = {'body': '正文第一段。\n\n链接版结尾', 'body_cta': '链接版结尾'}
        ok = dict(base, platform_overrides={'douyin': {'body_cta': '网页版也快上线\n\n想让蚱蜢也变成游戏吗？告诉我'}})
        self.assertEqual(checker.validate_body_cta(ok), [])
        for bad in ({'douyin': {'body_cta': '点赞够100个我就做'}}, {'weibo': {'body_cta': '好'}},
                    {'bilibili': {'body_cta': ''}}, {'douyin': {'body_cta': '见 https://a.cn'}}):
            self.assertTrue(checker.validate_body_cta(dict(base, platform_overrides=bad)), bad)
        self.assertTrue(checker.validate_body_cta({'platform_overrides': {'douyin': {'body_cta': '好'}}}))

    def errors_for_body(self, body, cta=None):
        import check_copy_package as checker
        copy = {'post_title': '给猫看的动画片| 蚱蜢跳跳停停', 'title_strategy_id': 'object-search',
                'benchmark_refs': ['BO-001'], 'body': body,
                'keywords': ['猫', '猫咪电视', '猫咪动画片', '猫咪日常', '蚱蜢', '昆虫', '猫猫看电视'],
                'source_credit': '素材来源：YouTube，本条为片段剪辑。'}
        if cta is not None:
            copy['body_cta'] = cta
        item = {'item_id': 'item-001', 'status': 'draft', 'content_type': 'external_passive_video', 'object': '蚱蜢',
                'source': source(), 'segment': {'mode': 'clip', 'start_seconds': 0, 'end_seconds': 1, 'continuous': True},
                'copy': copy}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'item.json'
            package.write_json(path, item)
            return [e for e in checker.validate(path) if '游戏' in e or 'body_cta' in e]

    def test_game_wording_only_allowed_in_closing_paragraph(self):
        main = '蚱蜢在浅色画面里跳动、停留，再换个方向。\n\n点开全屏就可以给猫咪看，手机能直接播放。'
        cta = '小老鼠已经有游戏版了，想让蚱蜢也变成游戏吗？评论区告诉我。'
        self.assertEqual(self.errors_for_body(main + '\n\n' + cta, cta), [])
        # 没有声明为 body_cta 的游戏字样，仍被拒绝；放在中间段也一样。
        self.assertTrue(self.errors_for_body(main + '\n\n' + cta))
        self.assertTrue(self.errors_for_body(cta + '\n\n' + main, cta))
        # 结尾段自身的规则：门槛、两个问题、超长。
        for bad in ('点赞够100个我就做游戏。', '想玩哪个游戏？想看哪个游戏？', '游戏' * 40):
            self.assertTrue(self.errors_for_body(main + '\n\n' + bad, bad), bad)


class LocalProduction(unittest.TestCase):
    def test_actual_clip_bundle_and_tamper_rejection(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            table(root / 'materials/index.csv', ['id', 'source_url', 'source_path'], [])
            table(root / 'content/publications.csv', ['id', 'item_id', 'platform_account_id', 'status'], [])
            item_dir = root / 'content/items/item-001-fixture'
            item_dir.mkdir(parents=True)
            origin = root / 'synthetic-source.mp4'
            package.run(['ffmpeg', '-v', 'error', '-nostdin', '-f', 'lavfi', '-i', 'color=c=yellow:s=160x120:r=10:d=2',
                         '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                         '-c:a', 'aac', '-shortest', str(origin)])
            Image.new('RGB', (1080, 1440), '#ffdd44').save(item_dir / 'cover.png')
            (item_dir / 'prompt.txt').write_text('Synthetic fixture only; no visual acceptance claim.')
            d = {'schema_version': 1, 'item_id': 'item-001', 'status': 'draft', 'content_type': 'external_passive_video',
                 'object': '蚱蜢', 'source': source(), 'segment': {'mode': 'clip', 'start_seconds': 0.2, 'end_seconds': 1.2, 'continuous': True},
                 'video': {'file': 'video.mp4'},
                 'cover': {'file': 'cover.png', 'sha256': package.sha(item_dir / 'cover.png'), 'category_label': '猫咪动画片',
                           'cover_title': '测试封面', 'channel_number': 1, 'template_version': 'synthetic-fixture',
                           'background': {'mode': 'ai_processed', 'asset': 'cover.png', 'reference_assets': ['cover.png'],
                                          'prompt_log': 'prompt.txt', 'generator': 'synthetic test fixture'}},
                 'copy': {'post_title': '给猫看的动画片| 蚱蜢跳跳停停', 'title_strategy_id': 'object-search', 'benchmark_refs': ['BO-001'],
                          'body': '蚱蜢在浅色画面里跳动、停留，再换个方向。\n\n点开全屏就可以给猫咪看，手机能直接播放，平板或电视画面更大。\n\n请把设备放稳、音量调低，并在旁边照看。每只猫反应不同，不感兴趣就让它离开。',
                          'keywords': ['猫', '猫咪电视', '猫咪动画片', '猫咪日常', '蚱蜢', '昆虫', '猫猫看电视'],
                          'source_credit': '素材来源：YouTube @Synthetic fixture《Synthetic fixture for tests only》，本条为片段剪辑。'},
                 'checks': {'product_acceptance': 'not-performed; synthetic contract fixture only'}}
            d['source'].update(local_file=str(origin), sha256=package.sha(origin))
            path = item_dir / 'item.json'
            package.write_json(path, d)
            selection = root / 'selection.json'
            package.write_json(selection, {'batch_id': 'synthetic-contract', 'requested_count': 7,
                                           'items': [{'item_json': str(path.relative_to(root))}]})
            tools = Path(__file__).resolve().parent
            project = Path(os.environ.get('MIMI_TV_OPERATIONS_ROOT', '/Volumes/ExtSSD2601/MiMi_TV_Operations'))
            cli_options = ['--project', str(root), '--selection', str(selection)]
            # The content fixture has no project Skill or global account Skills.
            # Loading must follow the production helper's source checkout.
            isolated_home = root / 'isolated-home'
            isolated_home.mkdir()
            def execute(command, *options, entry=tools / 'content_package.py'):
                return subprocess.run([sys.executable, str(entry), *cli_options, command, *options], capture_output=True, text=True,
                                      env={**os.environ, 'HOME': str(isolated_home)})
            # Reuse the existing video-clip engine; no account-specific cutter.
            engine = Path('/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-clip')
            output = item_dir / 'video.mp4'
            ledger = item_dir / 'cut-manifest.json'
            package.run([sys.executable, str(engine / 'atoms/rough_cut.py'), '--source', str(origin),
                         '--keeps', '0.2,1.2', '--time-basis', 'source', '--out', str(output), '--manifest', str(ledger)])
            package.run([sys.executable, str(engine / 'atoms/align_check.py'), '--body', str(output), '--manifest', str(ledger)])
            metadata = package.probe(output)
            stream = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
            audio = next(s for s in metadata['streams'] if s['codec_type'] == 'audio')
            d['video'].update(sha256=package.sha(output), duration_seconds=float(metadata['format']['duration']),
                              width=stream['width'], height=stream['height'], video_codec=stream['codec_name'], audio_codec=audio['codec_name'])
            package.write_json(path, d)
            self.assertAlmostEqual(d['video']['duration_seconds'], 1, delta=0.15)
            self.assertEqual(d['video']['audio_codec'], 'aac')
            # A valid item can progress while a larger batch still lacks sources.
            chosen = package.read_json(selection); chosen['requested_count'] = 1; package.write_json(selection, chosen)
            # Export through the same Skill implementation used by validation.
            exporter = tools / 'export_publish_packages.py'
            package.run([sys.executable, str(exporter), str(path)])
            legacy_package = package.module(project / 'scripts/content_package.py', 'legacy_package')
            legacy_exporter = package.module(project / 'scripts/export_publish_packages.py', 'legacy_exporter')
            current_exporter = package.module(exporter, 'current_exporter')
            self.assertEqual(legacy_exporter.render(d), current_exporter.render(d))
            self.assertEqual(legacy_package.audit(root, chosen, package.load_selection(root, selection)[1]),
                             package.audit(root, chosen, package.load_selection(root, selection)[1]))
            current_audit = execute('audit')
            legacy_audit = execute('audit', entry=project / 'scripts/content_package.py')
            self.assertEqual((current_audit.returncode, current_audit.stdout, current_audit.stderr),
                             (legacy_audit.returncode, legacy_audit.stdout, legacy_audit.stderr))
            current_exports = subprocess.run([sys.executable, str(exporter), str(path), '--replace'],
                                             capture_output=True, text=True)
            legacy_exports = subprocess.run([sys.executable, str(project / 'scripts/export_publish_packages.py'), str(path), '--replace'],
                                            capture_output=True, text=True)
            self.assertEqual((current_exports.returncode, current_exports.stdout, current_exports.stderr),
                             (legacy_exports.returncode, legacy_exports.stdout, legacy_exports.stderr))
            out = root / 'delivery'
            result = execute('bundle', '--out', str(out))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = package.read_json(out / 'manifest.json')
            self.assertEqual(manifest['status'], 'review')
            self.assertEqual(manifest['publication_permission'], 'no-publishing')
            with zipfile.ZipFile(out / 'package.zip') as z:
                self.assertIn('items/item-001/video.mp4', z.namelist())
                self.assertIn('items/item-001/publish_mimi_xhs.md', z.namelist())
                self.assertNotIn('synthetic-source.mp4', z.namelist())
                unpack = root / 'unpacked'; z.extractall(unpack)
            for filename, digest in manifest['files'].items():
                self.assertEqual(package.sha(unpack / filename), digest)
            result = execute('bundle', '--out', str(out))
            self.assertNotEqual(result.returncode, 0, 'must not overwrite delivery')
            (item_dir / 'publish_mimi_xhs.md').write_text('tampered export')
            result = execute('bundle', '--out', str(root / 'bad-delivery'))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'bad-delivery').exists())
            d = package.read_json(path)
            d['copy'].update(body_style='cat-fact',
                             body='这是一条用于检查字段结构的测试正文。\n\n此文本只检查知识类型是否能独立保留资料链接与段落，不是事实核验或供账号发布的正式文案。',
                             fact_sources=[{'title': 'Synthetic reference only', 'url': 'https://example.org/fixture'}],
                             keywords=['猫咪电视', '猫咪动画片', '猫咪日常', '蚱蜢', '昆虫', '猫咪行为', '猫咪冷知识'])
            package.write_json(path, d)
            package.run([sys.executable, str(exporter), str(path), '--replace'])
            result = execute('bundle', '--out', str(root / 'fact-delivery'))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            d['copy']['fact_sources'] = []
            package.write_json(path, d)
            package.run([sys.executable, str(exporter), str(path), '--replace'])
            result = execute('bundle', '--out', str(root / 'missing-facts'))
            self.assertNotEqual(result.returncode, 0, 'knowledge prose requires independent references')
            self.assertFalse((root / 'missing-facts').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
