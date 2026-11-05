"""Upload a built ZIP using the CurseForge authors API."""
import argparse
import json
import os
from pathlib import Path
import requests


def upload_error(response, token):
    # Include the server's validation reason without echoing credentials or
    # allowing response newlines to become GitHub Actions log commands.
    detail = response.text.replace(token, '[redacted]') if token else response.text
    detail = ' '.join(detail.split())[:1500]
    return (f'CurseForge upload failed: HTTP {response.status_code}. '
            f'Server response: {detail or "(empty)"}. Check the project before retrying.')


def configuration():
    project = os.environ.get('CF_PROJECT_ID', '')
    token = os.environ.get('CF_API_TOKEN', '')
    versions = json.loads(os.environ.get('CF_GAME_VERSIONS', '[]') or '[]')
    if not project.isdecimal() or not token:
        raise ValueError('Configure CF_PROJECT_ID and CF_API_TOKEN')
    if not isinstance(versions, list) or not versions or any(type(v) is not int or v <= 0 for v in versions):
        raise ValueError('CF_GAME_VERSIONS must be a JSON array of CurseForge game-version IDs')
    return project, token, versions


def validate_versions(token, versions):
    response = requests.get('https://wow.curseforge.com/api/game/versions',
                            headers={'X-Api-Token': token}, timeout=60,
                            allow_redirects=False)
    if response.status_code != 200:
        raise ValueError(upload_error(response, token))
    available = response.json()
    invalid = set(versions) - {item['id'] for item in available}
    if invalid:
        candidates = [item for item in available
                      if 'forever' in item.get('name', '').lower()
                      or item.get('name', '').startswith('1.60.')]
        details = json.dumps(candidates)
        raise ValueError(f'Unknown CurseForge game-version IDs: {sorted(invalid)}. '
                         f'Forever candidates from CurseForge: {details}. '
                         'Set CF_GAME_VERSIONS_Forever to the matching id in brackets.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, nargs='?')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--release-type', choices=['alpha', 'beta', 'release'], default='beta')
    args = parser.parse_args()
    project, token, versions = configuration()
    if args.check:
        try:
            validate_versions(token, versions)
        except ValueError as error:
            raise SystemExit(str(error)) from None
        print('CurseForge configuration and game-version IDs are valid')
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
            raise SystemExit(upload_error(response, token))
        print(f'Uploaded CurseForge file ID: {response.json()["id"]}')
