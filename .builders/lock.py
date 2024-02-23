from __future__ import annotations

import argparse
import json
import re
from functools import cache
from hashlib import sha256
from pathlib import Path

from google.cloud import storage
import packaging.tags
from packaging.version import Version

BUCKET_NAME = 'dd-agent-int-deps'
STORAGE_URL = f'https://storage.googleapis.com/{BUCKET_NAME}'
BUILDER_DIR = Path(__file__).parent
REPO_DIR = BUILDER_DIR.parent
RESOLUTION_DIR = REPO_DIR / '.deps'
LOCK_FILE_DIR = RESOLUTION_DIR / 'resolved'
DIRECT_DEP_FILE = REPO_DIR / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data' / 'agent_requirements.in'
CONSTANTS_FILE = REPO_DIR / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'


@cache
def macosx_platform_tags():
    tags = ['macosx', 'macosx_10_6_intel']
    for version in ['10_7', '10_9', '10_10', '10_12', '10_15', '11_0']:
        tags.extend([f'macosx_{version}_x86_64', f'macosx_{version}_universal2'])

    return tags


TARGET_PLATFORMS = {
    'linux-x86_64': ['linux_x86_64', 'manylinux1_x86_64', 'manylinux_2_12_x86_64', 'manylinux2010_x86_64'],
    'linux-aarch64': ['linux_aarch64', 'manylinux_2_17_aarch64', 'manylinux2014_aarch64'],
    'windows-x86_64': ['win_amd64'],
    'macos-x86_64': macosx_platform_tags(),
}


@cache
def default_python_version() -> str:
    contents = CONSTANTS_FILE.read_text(encoding='utf-8')
    match = re.search(r'^PYTHON_VERSION = [\'"](.+)[\'"]$', contents, re.MULTILINE)
    if not match:
        raise RuntimeError(f'Could not find PYTHON_VERSION in {CONSTANTS_FILE}')

    return [int(x) for x in match.group(1).split('.')]


@cache
def tags_for_platform(platform, target_python_major):
    python_version = [2, 7] if target_python_major == '2' else default_python_version()
    abis = ['cp27m', 'cp27mu'] if target_python_major == '2' else [f'cp{"".join(map(str, python_version))}']
    platforms = TARGET_PLATFORMS[platform]
    return {
        *packaging.tags.compatible_tags(python_version, platforms=platforms),
        *packaging.tags.cpython_tags(python_version, abis=abis, platforms=platforms),
    }


def find_candidates_for_project(wheel_names, project, project_version, target, python_major):
    """Filter the given `wheel_names` to match a given package-version pair for a
    platform defined by the `target` and a Python major version
    """
    candidates = {}
    for wheel_name in wheel_names:
        if not wheel_name.endswith('.whl'):
            continue

        # A wheel filename is {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl.
        # https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
        _proj_name, proj_version, *build, interpreter, abi, platform = wheel_name[:-4].split('-')
        if Version(proj_version) != project_version:
            continue

        # This is able to generate a set of tags out of a compressed tag set
        # https://peps.python.org/pep-0425/#compressed-tag-sets
        tagset = packaging.tags.parse_tag(f'{interpreter}-{abi}-{platform}')

        # Check for compatibility by checking if the wheel's tags match any of the expected tags for this platform
        if tagset.isdisjoint(tags_for_platform(target, python_major)):
            continue

        build_number = int(build[0]) if build else -1
        candidates[build_number] = wheel_name

    return candidates


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
            candidates = find_candidates_for_project(
                (blob.name.split('/')[-1] for blob in bucket.list_blobs(prefix=f'{artifact_type}/{project}/')),
                project,
                project_version,
                target,
                python_major,
            )
            if not candidates:
                continue

            selected = bucket.get_blob(f'{artifact_type}/{project}/{candidates[max(candidates)]}')
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
