"""Upload a built ZIP using the CurseForge authors API."""
import argparse
import json
import os
from pathlib import Path
import requests


def configuration():
    project = os.environ.get('CF_PROJECT_ID', '')
    token = os.environ.get('CF_API_TOKEN', '')
    versions = json.loads(os.environ.get('CF_GAME_VERSIONS', '[]') or '[]')
    if not project.isdecimal() or not token:
        raise ValueError('Configure CF_PROJECT_ID and CF_API_TOKEN')
    if not isinstance(versions, list) or not versions or any(type(v) is not int or v <= 0 for v in versions):
        raise ValueError('CF_GAME_VERSIONS must be a JSON array of CurseForge game-version IDs')
    return project, token, versions


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, nargs='?')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--release-type', choices=['alpha', 'beta', 'release'], default='beta')
    args = parser.parse_args()
    project, token, versions = configuration()
    if args.check:
        print('CurseForge configuration is present')
    else:
        if not args.archive:
            parser.error('archive is required unless --check is used')
        metadata = dict(changelog='Addon packaging fixes and Discord emote synchronization.',
                        changelogType='text', displayName=args.archive.stem,
                        gameVersions=versions, releaseType=args.release_type)
        with args.archive.open('rb') as archive:
            response = requests.post(f'https://wow.curseforge.com/api/projects/{project}/upload-file',
                                     headers={'X-Api-Token': token},
                                     data={'metadata': json.dumps(metadata)},
                                     files={'file': (args.archive.name, archive, 'application/zip')},
                                     timeout=180, allow_redirects=False)
        if response.status_code != 200:
            raise SystemExit(f'CurseForge upload failed: HTTP {response.status_code}. Check the project before retrying.')
        print(f'Uploaded CurseForge file ID: {response.json()["id"]}')
