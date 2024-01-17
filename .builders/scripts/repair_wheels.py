from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from functools import cache
from hashlib import sha256
from pathlib import Path
from typing import Iterator

import urllib3
from utils import extract_metadata, normalize_project_name


@cache
def get_wheel_hashes(project) -> dict[str, str]:
    response = urllib3.request('GET', f'https://pypi.org/simple/{project}')
    if response.status != 200:
        print(f'Failed to fetch hashes for `{project}`, status code: {response.status}')
        sys.exit(1)

    html = response.data.decode('utf-8')
    hashes: dict[str, str] = {}
    for line in html.splitlines():
        match = re.search(r'<a href="(?:.+?/)?([^"]+)#sha256=([^"]+)"[^>]*>\1</a>', line)
        if match:
            file_name, file_hash = match.groups()
            if file_name.endswith('.whl'):
                hashes[file_name] = file_hash

    return hashes


def iter_wheels(source_dir: str) -> Iterator[Path]:
    for entry in sorted(Path(source_dir).iterdir(), key=lambda entry: entry.name.casefold()):
        if entry.suffix == '.whl' and entry.is_file():
            yield entry


def wheel_was_built(wheel: Path) -> bool:
    project_metadata = extract_metadata(wheel)
    project_name = normalize_project_name(project_metadata['Name'])
    wheel_hashes = get_wheel_hashes(project_name)
    if wheel.name not in wheel_hashes:
        return True

    file_hash = sha256(wheel.read_bytes()).hexdigest()
    return file_hash != wheel_hashes[wheel.name]


def repair_linux(source_dir: str, built_dir: str, external_dir: str) -> None:
    from auditwheel.patcher import Patchelf
    from auditwheel.policy import get_policy_by_name
    from auditwheel.repair import repair_wheel
    from auditwheel.wheel_abi import NonPlatformWheel

    exclusions = [
        # pymqi
        'libmqic_r.so',
        # confluent_kafka
        # We leave cyrus-sasl out of the wheel because of the complexity involved in bundling it portably.
        # This means the confluent-kafka wheel will have a runtime dependency on this library
        'libsasl2.so.3',
    ]

    # Hardcoded policy to the minimum we need to currently support
    policy = get_policy_by_name('manylinux2010_x86_64')
    abis = [policy['name'], *policy['aliases']]

    for wheel in iter_wheels(source_dir):
        print(f'--> {wheel.name}')
        if not wheel_was_built(wheel):
            print('Using existing wheel')
            shutil.move(wheel, external_dir)
            continue

        try:
            repair_wheel(
                str(wheel),
                abis=abis,
                lib_sdir='.libs',
                out_dir=built_dir,
                update_tags=True,
                patcher=Patchelf(),
                exclude=exclusions,
            )
        except NonPlatformWheel:
            print('Using non-platform wheel without repair')
            shutil.move(wheel, built_dir)
            continue
        else:
            print('Repaired wheel')


def repair_windows(source_dir: str, built_dir: str, external_dir: str) -> None:
    import subprocess

    exclusions = ['mqic.dll']

    for wheel in iter_wheels(source_dir):
        print(f'--> {wheel.name}')
        if not wheel_was_built(wheel):
            print('Using existing wheel')
            shutil.move(wheel, external_dir)
            continue

        process = subprocess.run([
            sys.executable, '-m', 'delvewheel', 'repair', wheel,
            '--wheel-dir', built_dir,
            '--no-dll', os.pathsep.join(exclusions),
        ])
        if process.returncode:
            print('Repairing failed')
            sys.exit(process.returncode)


REPAIR_FUNCTIONS = {
    'linux': repair_linux,
    'win32': repair_windows,
}


def main():
    if sys.platform not in REPAIR_FUNCTIONS:
        print(f'Repair not implemented for platform: {sys.platform}')
        sys.exit(1)

    argparser = argparse.ArgumentParser(
        description='Repair wheels found in a directory with the platform-specific tool'
    )
    argparser.add_argument('--source-dir', required=True)
    argparser.add_argument('--built-dir', required=True)
    argparser.add_argument('--external-dir', required=True)
    args = argparser.parse_args()

    print(f'Repairing wheels in: {args.source_dir}')
    print(f'Outputting built wheels to: {args.built_dir}')
    print(f'Outputting external wheels to: {args.external_dir}')
    REPAIR_FUNCTIONS[sys.platform](args.source_dir, args.built_dir, args.external_dir)


if __name__ == '__main__':
    main()
