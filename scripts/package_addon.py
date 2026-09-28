"""Build a CurseForge ZIP with an exact LizzieEmotes/LizzieEmotes.toc match."""
import argparse
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FLAVORS = ('Retail', 'Vanilla', 'TBC', 'Wrath', 'Cata', 'Mists')


def build(root=ROOT, flavor='Retail', version='local'):
    if flavor not in FLAVORS or not re.fullmatch(r'[A-Za-z0-9._-]+', version):
        raise ValueError('Invalid flavor or version')
    toc = root / ('LizzieEmotes.toc' if flavor == 'Retail' else f'LizzieEmotes_{flavor}.toc')
    text = toc.read_text(encoding='utf-8-sig')
    files = set()
    for line in text.splitlines():
        if line.strip() and not line.startswith('#'):
            path = root / line.strip().replace('\\', '/')
            if not path.is_file():
                raise ValueError(f'Missing TOC file: {path}')
            files.add(path)
    for folder in ('libs', 'UI', 'Emotes'):
        files.update(p for p in (root / folder).rglob('*') if p.is_file())
    text = re.sub(r'(?m)^## Version:.*$', f'## Version: {version}', text)
    output = root / 'dist' / f'LizzieEmotes-{version}-{flavor}.zip'
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('LizzieEmotes/LizzieEmotes.toc', text)
        for path in sorted(files):
            archive.write(path, 'LizzieEmotes/' + path.relative_to(root).as_posix())
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert all(n.startswith('LizzieEmotes/') for n in archive.namelist())
        assert [n for n in archive.namelist() if n.count('/') == 1 and n.endswith('.toc')] == ['LizzieEmotes/LizzieEmotes.toc']
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flavor', choices=FLAVORS, default='Retail')
    parser.add_argument('--version', default='local')
    args = parser.parse_args()
    print(build(flavor=args.flavor, version=args.version))
