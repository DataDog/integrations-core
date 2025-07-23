from __future__ import annotations

import email
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Iterator
from zipfile import ZipFile

from wheel.cli.pack import pack
from wheel.cli.unpack import unpack

UNNORMALIZED_PROJECT_NAME_CHARS = re.compile(r'[-_.]+')


def normalize_project_name(name: str) -> str:
    # https://peps.python.org/pep-0503/#normalized-names
    return UNNORMALIZED_PROJECT_NAME_CHARS.sub('-', name).lower()


def extract_metadata(wheel: Path) -> email.Message:
    with ZipFile(str(wheel)) as zip_archive:
        for path in zip_archive.namelist():
            root = path.split('/', 1)[0]
            if root.endswith('.dist-info'):
                dist_info_dir = root
                break
        else:
            message = f'Could not find the `.dist-info` directory in wheel: {wheel.name}'
            raise RuntimeError(message)

        try:
            with zip_archive.open(f'{dist_info_dir}/METADATA') as zip_file:
                metadata_file_contents = zip_file.read().decode('utf-8')
        except KeyError:
            message = f'Could not find a `METADATA` file in the `{dist_info_dir}` directory'
            raise RuntimeError(message) from None

    return email.message_from_string(metadata_file_contents)



def iter_wheels(source_dir: str) -> Iterator[Path]:
    for entry in sorted(Path(source_dir).iterdir(), key=lambda entry: entry.name.casefold()):
        if entry.suffix == '.whl' and entry.is_file():
            yield entry

def remove_test_files(wheel_path: Path) -> None:
    '''
    Unpack the wheel, remove excluded test files, then repack it to rebuild RECORD correctly.
    '''
    # First, check whether the wheel contains any files that should be excluded. If not, leave it untouched.
    with ZipFile(wheel_path, 'r') as zf:
        excluded_members = [name for name in zf.namelist() if is_excluded_from_wheel(name)]

    if not excluded_members:
        # Nothing to strip, so skip rewriting the wheel
        return False

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)

        # Unpack the wheel into temp dir
        unpack(wheel_path, dest=td_path)
        unpacked_dir = next(td_path.iterdir())

        # Remove excluded files/folders
        for root, dirs, files in os.walk(td, topdown=False):
            for d in list(dirs):
                full_dir = Path(root) / d
                rel = full_dir.relative_to(unpacked_dir).as_posix()
                if is_excluded_from_wheel(rel):
                    shutil.rmtree(full_dir)
                    dirs.remove(d)
            for f in files:
                rel = Path(root).joinpath(f).relative_to(unpacked_dir).as_posix()
                if is_excluded_from_wheel(rel):
                    os.remove(Path(root) / f)

        print(f'Tests removed from {wheel_path.name}')

        # Repack to same directory, regenerating RECORD
        pack(unpacked_dir, dest_dir=wheel_path.parent, build_number=None)

    return True


def is_excluded_from_wheel(path: str) -> bool:
    '''
    These files are excluded from the wheel in the agent build:
    https://github.com/DataDog/datadog-agent/blob/main/omnibus/config/software/datadog-agent-integrations-py3.rb
    In order to have more accurate results, this files are excluded when computing the size of the dependencies while
    the wheels still include them.
    '''
    excluded_test_paths = [
        os.path.normpath(path)
        for path in [
            'idlelib/idle_test',
            'bs4/tests',
            'Cryptodome/SelfTest',
            'gssapi/tests',
            'keystoneauth1/tests',
            'lazy_loader/tests',
            'openstack/tests',
            'os_service_types/tests',
            'pbr/tests',
            'pkg_resources/tests',
            'pip/_vendor/colorama/tests',
            'psutil/tests',
            'requests_unixsocket/tests',
            'securesystemslib/_vendor/ed25519/test_data',
            'setuptools/_distutils/compilers/C/tests',
            'setuptools/_vendor/packaging/tests',
            'setuptools/_distutils/tests',
            'setuptools/tests',
            'simplejson/tests',
            'stevedore/tests',
            'supervisor/tests',
            'test',  # cm-client
            'vertica_python/tests',
            'websocket/tests',
            'win32com/test',
        ]
    ]

    type_annot_libraries = [
        'krb5',
        'Cryptodome',
        'ddtrace',
        'pyVmomi',
        'gssapi',
    ]
    rel_path = Path(path).as_posix()

    # Test folders
    for test_folder in excluded_test_paths:
        if rel_path == test_folder or rel_path.startswith(test_folder + os.sep):
            return True

    # Python type annotations
    path_parts = Path(rel_path).parts
    if path_parts:
        dependency_name = path_parts[0]
        if dependency_name in type_annot_libraries:
            if path.endswith('.pyi') or os.path.basename(path) == 'py.typed':
                return True

    return False