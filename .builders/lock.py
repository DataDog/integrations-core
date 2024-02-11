from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from google.cloud import storage
from packaging.version import Version

BUCKET_NAME = 'dd-agent-int-deps'
STORAGE_URL = f'https://storage.googleapis.com/{BUCKET_NAME}'
BUILDER_DIR = Path(__file__).parent
REPO_DIR = BUILDER_DIR.parent
RESOLUTION_DIR = REPO_DIR / '.deps'
LOCK_FILE_DIR = RESOLUTION_DIR / 'resolved'
DIRECT_DEP_FILE = REPO_DIR / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data' / 'agent_requirements.in'


def generate_lock_file(requirements_file: Path, lock_file: Path) -> None:
    dependencies: dict[str, str] = {}
    with requirements_file.open(encoding='utf-8') as f:
        for line in f.readlines():
            line = line.strip()
            if not line:
                continue

            name, version = line.split('==')
            dependencies[name] = version

    lock_file_lines = []

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    for project, version in sorted(dependencies.items()):
        project_version = Version(version)
        for artifact_type in ('built', 'external'):
            candidates = {}
            for blob in bucket.list_blobs(prefix=f'{artifact_type}/{project}/'):
                if not blob.name.endswith('.whl'):
                    continue

                wheel_name = blob.name.split('/')[-1]
                parts = wheel_name[:-4].split('-')
                if Version(parts[1]) != project_version:
                    continue

                build_number = int(parts[2]) if len(parts) == 6 else -1
                candidates[build_number] = blob

            if not candidates:
                continue

            selected = candidates[max(candidates)]
            selected.reload()
            sha256_digest = selected.metadata['sha256']
            index_url = f'{STORAGE_URL}/{selected.name}'
            lock_file_lines.append(f'{project} @ {index_url}#sha256={sha256_digest}')

            break
        else:
            raise RuntimeError(f'Could not find any wheels: {project}=={version}')

    lock_file_lines.append('')
    lock_file.write_text('\n'.join(lock_file_lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(prog='builder', allow_abbrev=False)
    parser.add_argument('targets_dir')
    args = parser.parse_args()

    LOCK_FILE_DIR.mkdir(parents=True, exist_ok=True)
    with RESOLUTION_DIR.joinpath('metadata.json').open('w', encoding='utf-8') as f:
        contents = json.dumps(
            {
                'sha256': sha256(DIRECT_DEP_FILE.read_bytes()).hexdigest(),
            },
            indent=2,
            sort_keys=True,
        )
        f.write(f'{contents}\n')

    image_digests = {}
    for target in Path(args.targets_dir).iterdir():
        for python_version in target.iterdir():
            if python_version.name.startswith('py'):
                generate_lock_file(
                    python_version / 'frozen.txt', LOCK_FILE_DIR / f'{target.name}_{python_version.name}.txt'
                )

        if (image_digest_file := target / 'image_digest').is_file():
            image_digests[target.name] = image_digest_file.read_text(encoding='utf-8').strip()

    with RESOLUTION_DIR.joinpath('image_digests.json').open('w', encoding='utf-8') as f:
        contents = json.dumps(image_digests, indent=2, sort_keys=True)
        f.write(f'{contents}\n')


if __name__ == '__main__':
    main()
