import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.add_emote import Publisher, prepare, render
from scripts.package_addon import build
from tests.test_tools import picture


class UploadTest(unittest.TestCase):
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
