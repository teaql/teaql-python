#!/usr/bin/env python3
"""Download and verify exactly the packages qualified before public promotion."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--language', choices=['python', 'typescript', 'dotnet'], required=True)
    parser.add_argument('--repository', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[a-z0-9.-]+', args.tag)
    assert re.fullmatch(r'[a-f0-9]{64}', args.manifest_sha256)
    assert subprocess.check_output(['git', 'cat-file', '-t', args.tag], text=True).strip() == 'tag'
    signature = subprocess.run(['git', 'verify-tag', '--raw', args.tag], capture_output=True, text=True)
    assert signature.returncode == 0
    assert '[GNUPG:] VALIDSIG D195CDD10288573D650193DA6B9F1F8BE00BD595 ' in signature.stderr
    commit = subprocess.check_output(['git', 'rev-parse', args.tag + '^{commit}'], text=True).strip()
    assert commit == subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'refs/remotes/origin/main'], check=True)
    metadata = Path('qualification-metadata')
    metadata.mkdir()
    subprocess.run(['gh', 'release', 'download', args.tag, '--repo', args.repository,
                    '--pattern', 'logging-qualification.json', '--dir', str(metadata)], check=True)
    raw = (metadata / 'logging-qualification.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == args.manifest_sha256
    manifest = json.loads(raw)
    assert manifest['schema'] == 'teaql.logging-release.qualified-packages/v1'
    assert manifest['repository'] == args.repository and manifest['language'] == args.language
    assert manifest['sourceCommit'] == commit
    qualification = manifest['internalQualification']
    assert qualification['passed'] is True and qualification['rounds'] == 2
    assert re.fullmatch(r'[a-f0-9]{64}', qualification['modelSHA256'])
    assert re.fullmatch(r'[a-f0-9]{40}', qualification['generatorCommit'])
    assert re.fullmatch(r'[a-f0-9]{64}', qualification['receiptSHA256'])
    packages = Path('qualified-packages')
    packages.mkdir()
    expected = set()
    suffix = {'python': '.whl', 'typescript': '.tgz', 'dotnet': '.nupkg'}[args.language]
    for artifact in manifest['artifacts']:
        name = artifact['file']
        assert re.fullmatch(r'[A-Za-z0-9_.-]+', name) and name.endswith(suffix)
        assert name not in expected
        expected.add(name)
        subprocess.run(['gh', 'release', 'download', args.tag, '--repo', args.repository,
                        '--pattern', name, '--dir', str(packages)], check=True)
        path = packages / name
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == artifact['bytes'] and hashlib.sha256(data).hexdigest() == artifact['sha256']
    assert expected and {p.name for p in packages.iterdir()} == expected
    print('Verified signed source tag and', len(expected), 'internally qualified package(s); no rebuild performed')


if __name__ == '__main__':
    main()
