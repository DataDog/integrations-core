from __future__ import annotations

import argparse
import csv
import io
import os
import re
import shutil
import sys
import tempfile
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath
from typing import NamedTuple
from zipfile import ZipFile

from utils import iter_wheels, wheel_supports_macos


MACOS_DDTRACE_LIBDDWAF_PATTERN = 'ddtrace/appsec/_ddwaf/libddwaf/*/lib/libddwaf.dylib'

# The Agent ships OpenSSL in `embedded/lib`. Linux wheels load that copy instead of each bundling their own,
# which would add ~7.5 MiB per wheel that uses OpenSSL.
AGENT_OPENSSL_SONAMES = frozenset({'libssl.so.3', 'libcrypto.so.3'})
# Major and minor version of the OpenSSL the Agent ships (the `openssl` archive in datadog-agent's
# `deps/repos.MODULE.bazel`). Wheels requiring newer OpenSSL symbols would fail to load in the Agent.
AGENT_OPENSSL_VERSION = (3, 5)
# The Agent installs wheels in `embedded/lib/pythonX.Y/site-packages`, two directories below `embedded/lib`.
AGENT_LIB_DIR_FROM_SITE_PACKAGES = '../..'
OPENSSL_SYMBOL_VERSION_PATTERN = re.compile(r'OPENSSL_(\d+)\.(\d+)\.\d+')


def find_patterns_in_wheel(wheel: Path, patterns: list[str]) -> list[str]:
    """Returns all found files inside `wheel` that match the given glob-style pattern"""
    with ZipFile(wheel) as zf:
        names = zf.namelist()

    return [name for name in names for pat in patterns if fnmatch(name, pat)]


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
        return '-'.join([self.name, self.version, self.python_tag, self.abi_tag, self.platform_tag]) + '.whl'


def _strip_macos_ddtrace_libddwaf(wheel: Path) -> list[str]:
    if WheelName.parse(wheel.name).name != 'ddtrace':
        return []

    removed = find_patterns_in_wheel(wheel, [MACOS_DDTRACE_LIBDDWAF_PATTERN])

    if not removed:
        return []

    removed_set = set(removed)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=wheel.parent, suffix='.whl', delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        with ZipFile(wheel) as source, ZipFile(temp_path, 'w') as destination:
            for info in source.infolist():
                if info.filename in removed_set:
                    continue

                contents = source.read(info)
                if info.filename.endswith('.dist-info/RECORD'):
                    record = io.StringIO(contents.decode('utf-8'), newline='')
                    updated_record = io.StringIO(newline='')
                    writer = csv.writer(updated_record, lineterminator='\n')
                    writer.writerows(row for row in csv.reader(record) if not row or row[0] not in removed_set)
                    contents = updated_record.getvalue().encode('utf-8')

                destination.writestr(info, contents)

        shutil.copymode(wheel, temp_path)
        os.replace(temp_path, wheel)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    return removed


def _find_record_references(wheel: Path, pattern: str) -> list[str]:
    with ZipFile(wheel) as archive:
        references: list[str] = []
        for record_path in (name for name in archive.namelist() if name.endswith('.dist-info/RECORD')):
            with archive.open(record_path) as record_file:
                record = io.TextIOWrapper(record_file, encoding='utf-8')
                references.extend(row[0] for row in csv.reader(record) if row and fnmatch(row[0], pattern))
    return references


def check_unacceptable_files(
    wheel: Path,
    invalid_file_patterns: list[str],
):
    """Check if a wheel contains any unacceptable files and exit if found."""
    unacceptable_files = find_patterns_in_wheel(wheel, invalid_file_patterns)
    if unacceptable_files:
        print(
            f"Found copies of unacceptable files in external wheel '{wheel.name}'",
            f'(matching {invalid_file_patterns}): ',
            unacceptable_files,
        )
        sys.exit(1)


def agent_lib_dir_rpath(path_in_wheel: str) -> str:
    """Return an `$ORIGIN`-relative RPATH entry that points from `path_in_wheel` to the Agent's `embedded/lib`."""
    depth = len(PurePosixPath(path_in_wheel).parent.parts)
    return '/'.join(['$ORIGIN', *['..'] * depth, AGENT_LIB_DIR_FROM_SITE_PACKAGES])


def find_agent_openssl_dependents(wheel: Path) -> list[str]:
    """
    Return the ELF files in `wheel` that depend on the Agent's OpenSSL.

    Raises `RuntimeError` if any of them requires OpenSSL symbols newer than the Agent's OpenSSL provides.
    """
    from elftools.elf.dynamic import DynamicSection
    from elftools.elf.elffile import ELFFile
    from elftools.elf.gnuversions import GNUVerNeedSection

    dependents = []
    too_new = []
    with ZipFile(wheel) as zf:
        for name in zf.namelist():
            with zf.open(name) as f:
                if f.read(4) != b'\x7fELF':
                    continue

            elf = ELFFile(io.BytesIO(zf.read(name)))
            dynamic = elf.get_section_by_name('.dynamic')
            if not isinstance(dynamic, DynamicSection):
                continue
            # pyelftools sets `needed` dynamically on DT_NEEDED tags
            needed = {tag.needed for tag in dynamic.iter_tags('DT_NEEDED')}  # type: ignore[attr-defined]
            if AGENT_OPENSSL_SONAMES.isdisjoint(needed):
                continue

            dependents.append(name)
            version_requirements = elf.get_section_by_name('.gnu.version_r')
            if not isinstance(version_requirements, GNUVerNeedSection):
                continue

            for verneed, vernaux_iter in version_requirements.iter_versions():
                if verneed.name not in AGENT_OPENSSL_SONAMES:
                    continue
                for vernaux in vernaux_iter:
                    match = OPENSSL_SYMBOL_VERSION_PATTERN.fullmatch(vernaux.name)
                    if match and tuple(map(int, match.groups())) > AGENT_OPENSSL_VERSION:
                        too_new.append(f'{name}: {vernaux.name}')

    if too_new:
        raise RuntimeError(
            f"{wheel.name} requires OpenSSL symbols newer than the Agent's OpenSSL "
            f'{".".join(map(str, AGENT_OPENSSL_VERSION))}:\n' + '\n'.join(too_new)
        )

    return dependents


def link_agent_openssl(wheel: Path, patcher) -> list[str]:
    """
    Make every ELF file in `wheel` that depends on OpenSSL find the Agent's copy, by appending an RPATH entry that
    points at the Agent's `embedded/lib`. auditwheel must have been told not to graft OpenSSL into the wheel.

    Returns the in-wheel paths of the patched files.
    """
    from auditwheel.wheeltools import InWheelCtx

    dependents = find_agent_openssl_dependents(wheel)
    if not dependents:
        return []

    with InWheelCtx(str(wheel), str(wheel)) as ctx:
        for name in dependents:
            path = os.path.join(ctx.path, name)
            rpaths = [entry for entry in patcher.get_rpath(path).split(':') if entry]
            agent_rpath = agent_lib_dir_rpath(name)
            if agent_rpath not in rpaths:
                patcher.set_rpath(path, ':'.join([*rpaths, agent_rpath]))

    return dependents


def repair_linux(source_built_dir: str, source_external_dir: str, built_dir: str, external_dir: str) -> None:
    from auditwheel.patcher import Patchelf
    from auditwheel.policy import WheelPolicies
    from auditwheel.repair import repair_wheel
    from auditwheel.wheel_abi import NonPlatformWheel

    exclusions = frozenset(
        {
            # pymqi
            'libmqic_r.so',
            # Loaded from the Agent's `embedded/lib`, see `link_agent_openssl`
            *AGENT_OPENSSL_SONAMES,
        }
    )

    external_invalid_file_patterns = [
        # We don't accept OpenSSL in external wheels
        '*.libs/libssl*.so.3',
        '*.libs/libcrypto*.so.3',
    ]

    # Hardcoded policy to the minimum we need to currently support
    policies = WheelPolicies()
    policy = policies.get_policy_by_name(os.environ['MANYLINUX_POLICY'])
    abis = [policy['name'], *policy['aliases']]
    # We edit the policy to remove zlib out of the whitelist to match the whitelisting policy we use
    # on the Omnibus health check in the Agent
    policy['lib_whitelist'].remove('libz.so.1')
    del policy['symbol_versions']['ZLIB']

    for wheel in iter_wheels(source_external_dir):
        print(f'--> {wheel.name}')
        print('Using existing wheel')

        check_unacceptable_files(
            wheel,
            invalid_file_patterns=external_invalid_file_patterns,
        )
        shutil.move(wheel, external_dir)
        continue

    patcher = Patchelf()
    for wheel in iter_wheels(source_built_dir):
        print(f'--> {wheel.name}')
        try:
            repaired_wheel = repair_wheel(
                policies,
                str(wheel),
                abis=abis,
                lib_sdir='.libs',
                out_dir=built_dir,
                update_tags=True,
                patcher=patcher,
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

        if repaired_wheel and (linked := link_agent_openssl(Path(repaired_wheel), patcher)):
            print("Linked to the Agent's OpenSSL:")
            print('\n'.join(linked))


def repair_windows(source_built_dir: str, source_external_dir: str, built_dir: str, external_dir: str) -> None:
    import subprocess

    exclusions = ['mqic.dll']

    external_invalid_file_patterns = [
        # We don't accept OpenSSL in external wheels
        '*.libs/libssl-3*.dll',
        '*.libs/libcrypto-3*.dll',
    ]

    for wheel in iter_wheels(source_external_dir):
        print(f'--> {wheel.name}')
        print('Using existing wheel')

        check_unacceptable_files(
            wheel,
            invalid_file_patterns=external_invalid_file_patterns,
        )
        shutil.move(wheel, external_dir)

    for wheel in iter_wheels(source_built_dir):
        print(f'--> {wheel.name}')
        # Platform independent wheels: move and rename to make platform specific
        wheel_name = WheelName.parse(wheel.name)
        if wheel_name.platform_tag == 'any':
            dest = str(wheel_name._replace(platform_tag='win_amd64'))
            shutil.move(wheel, Path(built_dir) / dest)
            continue

        process = subprocess.run(
            [
                sys.executable,
                '-m',
                'delvewheel',
                'repair',
                wheel,
                '--wheel-dir',
                built_dir,
                '--no-dll',
                os.pathsep.join(exclusions),
                '--no-diagnostic',
            ]
        )
        if process.returncode:
            print('Repairing failed')
            sys.exit(process.returncode)


def repair_darwin(source_built_dir: str, source_external_dir: str, built_dir: str, external_dir: str) -> None:
    from delocate import delocate_wheel
    from packaging.version import Version

    exclusions = [
        re.compile(s)
        for s in [
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
        ]
    ]

    def copy_filt_func(libname):
        return not any(excl.search(libname) for excl in exclusions)

    min_macos_version = Version(os.environ["MACOSX_DEPLOYMENT_TARGET"])
    macos_target = (min_macos_version.major, min_macos_version.minor)
    arch = os.uname().machine

    for wheel in iter_wheels(source_external_dir):
        print(f'--> {wheel.name}')
        wheel_name = WheelName.parse(wheel.name)
        if wheel_name.name == 'ddtrace' and find_patterns_in_wheel(wheel, [MACOS_DDTRACE_LIBDDWAF_PATTERN]):
            shutil.move(wheel, Path(source_built_dir) / wheel.name)
            continue
        # build_wheels.py already swapped incompatible wheels for compatible ones of the same release where one
        # exists. Built wheels get this check from delocate below; external wheels only get it here.
        if not wheel_supports_macos(wheel.name, macos_target, arch):
            raise RuntimeError(
                f'External wheel {wheel.name} does not support macOS {min_macos_version} on {arch} and no wheel '
                'of the same release that does could be downloaded; build it from source by adding it to '
                '`always_build` in images/macos/extra_build.sh'
            )
        print('Using existing wheel')
        shutil.move(wheel, external_dir)

    for wheel in iter_wheels(source_built_dir):
        print(f'--> {wheel.name}')
        # Platform independent wheels: move and rename to make platform specific
        wheel_name = WheelName.parse(wheel.name)
        if wheel_name.platform_tag == 'any':
            dest = str(
                wheel_name._replace(
                    platform_tag=f'macosx_{min_macos_version.major}_{min_macos_version.minor}_universal2'
                )
            )
            shutil.move(wheel, Path(built_dir) / dest)
            continue

        # Platform dependent wheels: prune excluded files, verify target architecture & macOS version
        removed_libddwaf = _strip_macos_ddtrace_libddwaf(wheel)
        if removed_libddwaf:
            print('Removed bundled libddwaf from Agent ddtrace wheel:')
            print('\n'.join(removed_libddwaf))

            # Verify on the stripped input rather than delocate's output: delocate renames the
            # output wheel to match the macOS version it scans off the binaries, so its final
            # name is not known here. It only ever copies libraries in, so an input that is
            # clean of libddwaf guarantees the output is too.
            remaining_libddwaf = find_patterns_in_wheel(wheel, [MACOS_DDTRACE_LIBDDWAF_PATTERN])
            stale_record_entries = _find_record_references(wheel, MACOS_DDTRACE_LIBDDWAF_PATTERN)
            if remaining_libddwaf or stale_record_entries:
                raise RuntimeError(f'Failed to remove bundled libddwaf from {wheel.name}')

        copied_libs = delocate_wheel(
            str(wheel),
            str(Path(built_dir) / wheel.name),
            copy_filt_func=copy_filt_func,
            require_archs=[os.uname().machine],
            require_target_macos_version=min_macos_version,
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
    argparser.add_argument('--source-built-dir', required=True)
    argparser.add_argument('--source-external-dir', required=True)
    argparser.add_argument('--built-dir', required=True)
    argparser.add_argument('--external-dir', required=True)
    args = argparser.parse_args()

    print(f'Repairing wheels in: {args.source_built_dir}')
    print(f'Outputting built wheels to: {args.built_dir}')
    print(f'Outputting external wheels to: {args.external_dir}')
    REPAIR_FUNCTIONS[sys.platform](args.source_built_dir, args.source_external_dir, args.built_dir, args.external_dir)


if __name__ == '__main__':
    main()
