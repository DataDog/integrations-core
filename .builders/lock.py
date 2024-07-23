from __future__ import annotations

import argparse
import json
import re
from functools import cache
from hashlib import sha256
from pathlib import Path

from google.cloud import storage
from packaging.version import Version

BUCKET_NAME = 'deps-agent-int-datadoghq-com'
STORAGE_URL = 'https://agent-int-packages.datadoghq.com'
BUILDER_DIR = Path(__file__).parent
REPO_DIR = BUILDER_DIR.parent
RESOLUTION_DIR = REPO_DIR / '.deps'
LOCK_FILE_DIR = RESOLUTION_DIR / 'resolved'
DIRECT_DEP_FILE = REPO_DIR / 'agent_requirements.in'
CONSTANTS_FILE = REPO_DIR / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'
TARGET_TAG_PATTERNS = {
    'linux-x86_64': 'manylinux.*_x86_64|linux_x86_64',
    'linux-aarch64': 'manylinux.*_aarch64|linux_aarch64',
    'windows-x86_64': 'win_amd64',
    'macos-x86_64': 'macosx.*_(x86_64|intel|universal2)',
}


@cache
def default_python_version() -> str:
    contents = CONSTANTS_FILE.read_text(encoding='utf-8')
    match = re.search(r'^PYTHON_VERSION = [\'"](.+)[\'"]$', contents, re.MULTILINE)
    if not match:
        raise RuntimeError(f'Could not find PYTHON_VERSION in {CONSTANTS_FILE}')

    return match.group(1)


def is_compatible_wheel(
    target_name: str,
    target_python_major: str,
    interpreter: str,
    abi: str,
    platform: str,
) -> bool:
    if interpreter.startswith('cp'):
        target_python = '2.7' if target_python_major == '2' else default_python_version()
        expected_tag = f'cp{target_python_major}' if abi == 'abi3' else f'cp{target_python}'.replace('.', '')
        if expected_tag not in interpreter:
            return False
    elif f'py{target_python_major}' not in interpreter:
        return False

    if platform != 'any':
        target_tag_pattern = TARGET_TAG_PATTERNS[target_name]
        if not re.search(target_tag_pattern, platform):
            return False

    return True


def generate_lock_file(requirements_file: Path, lock_file: Path) -> None:
    target, _, python_version = lock_file.stem.rpartition('_')
    python_major = python_version[-1]

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
                wheel_name = blob.name.split('/')[-1]
                if not wheel_name.endswith('.whl'):
                    continue

                # https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
                _proj_name, proj_version, *build, interpreter, abi, platform = wheel_name[:-4].split('-')
                if Version(proj_version) != project_version:
                    continue

                if not is_compatible_wheel(target, python_major, interpreter, abi, platform):
                    continue

                build_number = int(build[0]) if build else -1
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
            raise RuntimeError(f'Could not find any wheels for target {target}: {project}=={version}')

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
