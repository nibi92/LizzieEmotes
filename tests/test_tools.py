import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

from PIL import Image
from scripts.package_addon import build, FLAVORS, ROOT
from scripts.sync_discord import convert, sync, fetch
from scripts.upload_curseforge import configuration, upload_error, validate_versions


def picture(animated=False):
    output = io.BytesIO()
    first = Image.new('RGBA', (32, 48), 'red')
    if animated:
        first.save(output, format='GIF', save_all=True,
                   append_images=[Image.new('RGBA', (32, 48), 'blue')], duration=[100, 200], loop=0)
    else:
        first.save(output, format='PNG')
    return output.getvalue()


class ToolsTest(unittest.TestCase):
    def test_invalid_version_lists_forever_candidates(self):
        from unittest.mock import Mock
        response = Mock(status_code=200)
        response.json.return_value = [dict(id=42, name='1.60.1', gameVersionTypeID=7)]
        with patch('scripts.upload_curseforge.requests.get', return_value=response):
            validate_versions('test', [42])
            with self.assertRaisesRegex(ValueError, '"id": 42'):
                validate_versions('test', [88568])

    def test_upload_error_shows_reason_and_redacts_token(self):
        from unittest.mock import Mock
        response = Mock(status_code=400, text='Invalid game version\nsecret-token\n::warning::example')
        message = upload_error(response, 'secret-token')
        self.assertIn('Invalid game version', message)
        self.assertNotIn('secret-token', message)
        self.assertNotIn('\n', message)

    def test_rate_limit_retry_and_cdn_does_not_receive_token(self):
        from unittest.mock import Mock
        limited = Mock(status_code=429)
        limited.json.return_value = {'retry_after': .1}
        success = Mock(status_code=200, content=b'image')
        with patch('scripts.sync_discord.requests.get', side_effect=[limited, success]) as get, \
                patch('scripts.sync_discord.time.sleep') as sleep:
            self.assertEqual(fetch('https://cdn.discordapp.com/emojis/123456.png'), b'image')
            self.assertNotIn('Authorization', get.call_args.kwargs['headers'])
            sleep.assert_called_once_with(.1)

    def test_curseforge_requires_real_version_ids(self):
        with patch.dict('os.environ', {'CF_PROJECT_ID': '1631926', 'CF_API_TOKEN': 'test',
                                      'CF_GAME_VERSIONS': '[]'}):
            with self.assertRaises(ValueError):
                configuration()
        with patch.dict('os.environ', {'CF_PROJECT_ID': '1631926', 'CF_API_TOKEN': 'test',
                                      'CF_GAME_VERSIONS': '[123]'}):
            self.assertEqual(configuration(), ('1631926', 'test', [123]))

    def test_animation_dimensions_and_timing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'emoji.tga'
            meta = convert(picture(True), path)
            self.assertGreater(meta['nFrames'], 1)
            self.assertAlmostEqual(meta['nFrames'] / meta['framerate'], .3, places=5)
            with Image.open(path) as image:
                self.assertEqual(image.size, (64, 512))
                self.assertEqual(image.getpixel((32, 32))[:3], (255, 0, 0))
                self.assertEqual(image.getpixel((32, (meta['nFrames'] - 1) * 64 + 32))[:3], (0, 0, 255))

    def test_sync_is_repeatable_and_keeps_originals(self):
        import json
        emojis = [dict(id='123456', name='hello'), dict(id='123457', name='hello', animated=True)]
        def fake_fetch(url, token=None):
            return json.dumps(emojis).encode() if '/guilds/' in url else picture('.gif' in url)
        with tempfile.TemporaryDirectory() as folder, patch('scripts.sync_discord.fetch', side_effect=fake_fetch):
            root = Path(folder)
            (root / 'Emotes.lua').write_text('original')
            sync('123456', 'test', root)
            first = (root / 'DiscordEmotes.lua').read_bytes()
            sync('123456', 'test', root)
            self.assertEqual(first, (root / 'DiscordEmotes.lua').read_bytes())
            self.assertEqual((root / 'Emotes.lua').read_text(), 'original')
            self.assertIn(b':discord_hello_123457:', first)
            self.assertIn(b'Interface\\\\AddOns\\\\LizzieEmotes', first)
            with patch('scripts.sync_discord.fetch', side_effect=RuntimeError('network')):
                with self.assertRaises(RuntimeError):
                    sync('123456', 'test', root)
            self.assertEqual(first, (root / 'DiscordEmotes.lua').read_bytes())
            images = {p.name: p.read_bytes() for p in (root / 'Emotes/discord').glob('*.tga')}
            with patch('scripts.sync_discord.fetch', side_effect=[json.dumps(emojis).encode(), picture(), RuntimeError('network')]):
                with self.assertRaises(RuntimeError):
                    sync('123456', 'test', root)
            self.assertEqual(first, (root / 'DiscordEmotes.lua').read_bytes())
            self.assertEqual(images, {p.name: p.read_bytes() for p in (root / 'Emotes/discord').glob('*.tga')})

    def test_every_flavor_packages_exact_root(self):
        for flavor in FLAVORS:
            with self.subTest(flavor=flavor), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                toc_name = 'LizzieEmotes.toc' if flavor == 'Retail' else f'LizzieEmotes_{flavor}.toc'
                text = (ROOT / toc_name).read_text()
                (root / toc_name).write_text(text)
                for line in text.splitlines():
                    if line.strip() and not line.startswith('#'):
                        relative = line.strip().replace('\\', '/')
                        self.assertTrue((ROOT / relative).is_file(), relative)
                        path = root / relative
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text('fixture')
                with zipfile.ZipFile(build(root, flavor, 'test')) as archive:
                    self.assertIn('LizzieEmotes/LizzieEmotes.toc', archive.namelist())
                    self.assertFalse(any('TwitchEmotes_' in name for name in archive.namelist()))
                    self.assertIn(b'## Version: test', archive.read('LizzieEmotes/LizzieEmotes.toc'))


if __name__ == '__main__':
    unittest.main()
