import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.add_emote import Publisher, prepare, render, ImportFailure
from scripts.package_addon import build
from tests.test_tools import picture


class UploadTest(unittest.TestCase):
    def test_exact_names_and_edit_replaces_animation(self):
        import base64
        import json
        publisher = Publisher('owner/repo', 'main', 'test')
        entries = {}
        uploaded = {}
        def api(method, path, **kwargs):
            if path.startswith('/git/ref/'): return {'object': {'sha': 'head'}}
            if path == '/git/commits/head': return {'tree': {'sha': 'tree'}}
            if path == '/git/trees/tree':
                return {'tree': [{'path': 'UploadedEmotes.json', 'sha': 'manifest'}]}
            if path == '/git/blobs/manifest':
                return {'content': base64.b64encode(json.dumps(entries).encode()).decode()}
            if path == '/git/blobs':
                content = base64.b64decode(kwargs['json']['content'])
                ident = str(len(uploaded))
                uploaded[ident] = content
                return {'sha': ident}
            if path == '/git/trees':
                for item in kwargs['json']['tree']:
                    if item['path'] == 'UploadedEmotes.json':
                        entries.clear()
                        entries.update(json.loads(uploaded[item['sha']]))
                return {'sha': 'newtree'}
            return {'sha': 'new', 'html_url': 'https://github.com/owner/repo/commit/new'}
        with patch.object(publisher, 'api', side_effect=api):
            self.assertEqual(publisher.publish('PepeWave', picture(True))[1], 'PepeWave')
            self.assertIn('PepeWave', entries)
            lua = render(entries).decode()
            self.assertIn('["PepeWave"]', lua)
            self.assertNotIn(':uploaded_PepeWave:', lua)
            self.assertNotIn('trigger =', lua)
            with self.assertRaises(ValueError):
                publisher.publish('pepewave', picture())
            self.assertEqual(publisher.publish('pepewave', picture(), edit=True)[1], 'PepeWave')
            self.assertEqual(entries['PepeWave']['nFrames'], 1)
            self.assertNotIn('TwitchEmotes_animation_metadata[', render(entries).decode())
            with self.assertRaises(ValueError):
                publisher.publish('Missing', picture(), edit=True)
            entries['legacy'] = prepare('legacy', picture(True))[1]
            self.assertEqual(publisher.publish('legacy', picture(), edit=True)[1], ':uploaded_legacy:')
            asset = entries['PepeWave']['texture']
            self.assertEqual(publisher.publish('PepeWave', None, edit=True, new_name='HappyWave')[1], 'HappyWave')
            self.assertNotIn('PepeWave', entries)
            self.assertEqual(entries['HappyWave']['texture'], asset)
            self.assertIn('["HappyWave"]', render(entries).decode())
            self.assertEqual(publisher.publish('HappyWave', picture(True), edit=True, new_name='HAPPY')[1], 'HAPPY')
            self.assertGreater(entries['HAPPY']['nFrames'], 1)
            with self.assertRaises(ValueError):
                publisher.publish('HAPPY', None, edit=True, new_name='legacy')
            with self.assertRaises(ValueError):
                publisher.publish('HAPPY', None, edit=True, new_name='../bad')
            with self.assertRaises(ValueError):
                publisher.publish('HAPPY', None, edit=True)
            publisher.publish('PepeWave', picture())
            self.assertNotEqual(entries['PepeWave']['texture'], entries['HAPPY']['texture'])

    def test_github_errors_explain_failure_without_leaking_response(self):
        from unittest.mock import Mock
        import requests
        publisher = Publisher('owner/repo', 'main', 'secret-token')
        for status in (401, 403, 404, 409, 422, 429, 500):
            response = Mock(ok=False, status_code=status, text='secret-token')
            with patch.object(publisher.session, 'request', return_value=response):
                with self.assertRaises(ImportFailure) as caught:
                    publisher.api('POST', '/git/blobs')
                self.assertIn(str(status), str(caught.exception))
                self.assertNotIn('secret-token', str(caught.exception))
        with patch.object(publisher.session, 'request', side_effect=requests.Timeout('secret-token')):
            with self.assertRaises(ImportFailure) as caught:
                publisher.api('POST', '/git/blobs')
            self.assertNotIn('secret-token', str(caught.exception))

    def test_beta_workflow_inputs_and_empty_response(self):
        publisher = Publisher('owner/repo', 'main', 'test')
        with patch.object(publisher, 'api', return_value={}) as api:
            url = publisher.release_beta('Mists')
        self.assertIn('/actions/workflows/release.yml', url)
        api.assert_called_once_with('POST', '/actions/workflows/release.yml/dispatches', json={
            'ref': 'main', 'inputs': {'sync_discord': False, 'publish': True,
                                     'flavor': 'Mists', 'release_type': 'beta'}})
        with patch.object(publisher, 'api') as api:
            with self.assertRaises(ValueError):
                publisher.release_beta('bad')
            api.assert_not_called()
        with patch.object(publisher, 'api', return_value={}) as api:
            publisher.release('Retail')
            self.assertEqual(api.call_args.kwargs['json']['inputs']['release_type'], 'release')
        from unittest.mock import Mock
        with patch.object(publisher.session, 'request', return_value=Mock(ok=True, content=b'')):
            self.assertEqual(publisher.api('POST', '/test'), {})

    def test_validation_and_animation(self):
        for name in ('../bad', 'bad"', '', '1bad'):
            with self.assertRaises(ValueError):
                prepare(name, picture())
        texture, meta = prepare('Dance', picture(True))
        self.assertTrue(texture)
        self.assertGreater(meta['nFrames'], 1)
        lua = render({'dance': meta}).decode()
        self.assertIn(':uploaded_dance:', lua)
        self.assertIn('TwitchEmotes_animation_metadata[', lua)
        self.assertIn('TwitchEmotes_dropdown_options', lua)

    def test_atomic_commit_and_conflict_does_not_force(self):
        publisher = Publisher('owner/repo', 'main', 'test')
        calls = []
        def api(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path.startswith('/git/ref/'): return {'object': {'sha': 'head'}}
            if path == '/git/commits/head': return {'tree': {'sha': 'tree'}}
            if method == 'GET': return {'tree': []}
            if method == 'PATCH': raise RuntimeError('conflict')
            return {'sha': 'new', 'html_url': 'https://github.com/owner/repo/commit/new'}
        with patch.object(publisher, 'api', side_effect=api):
            with self.assertRaises(RuntimeError):
                publisher.publish('Wave', picture())
        self.assertEqual(calls[-1][2]['json'], {'sha': 'new', 'force': False})
        tree = next(c for c in calls if c[:2] == ('POST', '/git/trees'))
        self.assertEqual(len(tree[2]['json']['tree']), 3)

    def test_duplicate_does_not_write(self):
        import base64
        publisher = Publisher('owner/repo', 'main', 'test')
        with patch.object(publisher, 'api', side_effect=[
            {'object': {'sha': 'head'}}, {'tree': {'sha': 'tree'}},
            {'tree': [{'path': 'UploadedEmotes.json', 'sha': 'manifest'}]},
            {'content': base64.b64encode(b'{"wave": {}}').decode()},
        ]) as api:
            with self.assertRaises(ValueError):
                publisher.publish('WAVE', picture())
        self.assertTrue(all(c.args[0] == 'GET' for c in api.call_args_list))
