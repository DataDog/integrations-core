from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from functools import cache
from hashlib import sha256
from pathlib import Path
from typing import Iterator, NamedTuple

import urllib3
from utils import extract_metadata, normalize_project_name


@cache
def get_wheel_hashes(project) -> dict[str, str]:
    retry_wait = 2
    while True:
        try:
            response = urllib3.request('GET', f'https://pypi.org/simple/{project}')
        except urllib3.exceptions.HTTPError as e:
            err_msg = f'Failed to fetch hashes for `{project}`: {e}'
        else:
            if response.status == 200:
                break

            err_msg = f'Failed to fetch hashes for `{project}`, status code: {response.status}'

        print(err_msg)
        print(f'Retrying in {retry_wait} seconds')
        time.sleep(retry_wait)
        retry_wait *= 2
        continue

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


class WheelName(NamedTuple):
    """Helper class to manipulate wheel names."""
    # Note: this implementation ignores build tags (it drops them on parsing)
    name: str
    version: str
    python_tag: str
    abi_tag: str
    platform_tag: str

    @classmethod
    def parse(cls, wheel_name: str):
        name, _ext = os.path.splitext(wheel_name)
        parts = name.split('-')
        if len(parts) == 6:
            parts.pop(2)
        return cls(*parts)

    def __str__(self):
        return '-'.join([
            self.name, self.version, self.python_tag, self.abi_tag, self.platform_tag
        ]) + '.whl'


def repair_linux(source_dir: str, built_dir: str, external_dir: str) -> None:
    from auditwheel.patcher import Patchelf
    from auditwheel.policy import WheelPolicies
    from auditwheel.repair import repair_wheel
    from auditwheel.wheel_abi import NonPlatformWheel

    exclusions = frozenset({
        # pymqi
        'libmqic_r.so',
    })

    # Hardcoded policy to the minimum we need to currently support
    policies = WheelPolicies()
    policy = policies.get_policy_by_name(os.environ['MANYLINUX_POLICY'])
    abis = [policy['name'], *policy['aliases']]
    # We edit the policy to remove zlib out of the whitelist to match the whitelisting policy we use
    # on the Omnibus health check in the Agent
    policy['lib_whitelist'].remove('libz.so.1')
    del policy['symbol_versions']['ZLIB']

    for wheel in iter_wheels(source_dir):
        print(f'--> {wheel.name}')
        if not wheel_was_built(wheel):
            print('Using existing wheel')
            shutil.move(wheel, external_dir)
            continue

        try:
            repair_wheel(
                policies,
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
            # Platform independent wheels: move and rename to make platform specific
            new_name = str(WheelName.parse(wheel.name)._replace(platform_tag=os.environ['MANYLINUX_POLICY']))
            shutil.move(wheel, Path(built_dir) / new_name)
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

        # Platform independent wheels: move and rename to make platform specific
        wheel_name = WheelName.parse(wheel.name)
        if wheel_name.platform_tag == 'any':
            dest = str(wheel_name._replace(platform_tag='win_amd64'))
            shutil.move(wheel, Path(built_dir) / dest)
            continue

        process = subprocess.run([
            sys.executable, '-m', 'delvewheel', 'repair', wheel,
            '--wheel-dir', built_dir,
            '--no-dll', os.pathsep.join(exclusions),
            '--no-diagnostic',
        ])
        if process.returncode:
            print('Repairing failed')
            sys.exit(process.returncode)


def repair_darwin(source_dir: str, built_dir: str, external_dir: str) -> None:
    from delocate import delocate_wheel
    exclusions = [re.compile(s) for s in [
        # pymqi
        r'pymqe\.cpython-\d+-darwin\.so',
        # confluent_kafka
        # We leave cyrus-sasl out of the wheel because of the complexity involved in bundling it portably.
        # This means the confluent-kafka wheel will have a runtime dependency on this library
        r'libsasl2.\d\.dylib',
        # Whitelisted libraries based on the health check default whitelist that we have on omnibus:
        # https://github.com/DataDog/omnibus-ruby/blob/044a81fa1b0f1c50fc7083cb45e7d8f90d96905b/lib/omnibus/health_check.rb#L133-L152
        # We use that instead of the more relaxed policy that delocate_wheel defaults to.
        r'libobjc\.A\.dylib',
        r'libSystem\.B\.dylib',
        # Symlink of the previous one
        r'libgcc_s\.1\.dylib',
        r'CoreFoundation',
        r'CoreServices',
        r'Tcl$',
        r'Cocoa$',
        r'Carbon$',
        r'IOKit$',
        r'Kerberos',
        r'Tk$',
        r'libutil\.dylib',
        r'libffi\.dylib',
        r'libncurses\.5\.4\.dylib',
        r'libiconv',
        r'libstdc\+\+\.6\.dylib',
        r'libc\+\+\.1\.dylib',
        r'^/System/Library/',
    ]]

    def copy_filt_func(libname):
        return not any(excl.search(libname) for excl in exclusions)

    for wheel in iter_wheels(source_dir):
        print(f'--> {wheel.name}')
        if not wheel_was_built(wheel):
            print('Using existing wheel')
            shutil.move(wheel, external_dir)
            continue

        # Platform independent wheels: move and rename to make platform specific
        wheel_name = WheelName.parse(wheel.name)
        if wheel_name.platform_tag == 'any':
            dest = str(wheel_name._replace(platform_tag='macosx_10_12_universal2'))
            shutil.move(wheel, Path(built_dir) / dest)
            continue

        copied_libs = delocate_wheel(
            str(wheel),
            os.path.join(built_dir, wheel.name),
            copy_filt_func=copy_filt_func,
        )
        print('Repaired wheel')
        if copied_libs:
            print('Libraries copied into the wheel:')
            print('\n'.join(copied_libs))
        else:
            print('No libraries were copied into the wheel.')


REPAIR_FUNCTIONS = {
    'linux': repair_linux,
    'win32': repair_windows,
    'darwin': repair_darwin,
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
