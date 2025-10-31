from __future__ import annotations

import argparse
import email
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from functools import cache
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypedDict
from zipfile import ZipFile

import pathspec
import urllib3
from dotenv import dotenv_values
from utils import iter_wheels

INDEX_BASE_URL = 'https://agent-int-packages.datadoghq.com'
CUSTOM_EXTERNAL_INDEX = f'{INDEX_BASE_URL}/external'
CUSTOM_BUILT_INDEX = f'{INDEX_BASE_URL}/built'
UNNORMALIZED_PROJECT_NAME_CHARS = re.compile(r'[-_.]+')

class WheelSizes(TypedDict):
    compressed: int
    uncompressed: int

if sys.platform == 'win32':
    PY3_PATH = Path('C:\\py3\\Scripts\\python.exe')
    PY2_PATH = Path('C:\\py2\\Scripts\\python.exe')
    MOUNT_DIR = Path('C:\\mnt')
    ENV_FILE = Path('C:\\.env')

    def join_command_args(args: list[str]) -> str:
        return subprocess.list2cmdline(args)

    def path_to_uri(path: str) -> str:
        return f'file:///{os.path.abspath(path).replace(" ", "%20").replace(os.sep, "/")}'

else:
    import shlex

    PY3_PATH = Path(os.environ.get('DD_PY3_BUILDENV_PATH', '/py3/bin/python'))
    PY2_PATH = Path(os.environ.get('DD_PY2_BUILDENV_PATH', '/py2/bin/python'))
    MOUNT_DIR = Path(os.environ.get('DD_MOUNT_DIR', '/home'))
    ENV_FILE = Path(os.environ.get('DD_ENV_FILE', '/.env'))

    def join_command_args(args: list[str]) -> str:
        return shlex.join(args)

    def path_to_uri(path: str) -> str:
        return f'file://{os.path.abspath(path).replace(" ", "%20")}'


def abort(message, *, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)


def check_process(*args, **kwargs) -> subprocess.CompletedProcess:
    print(f'Running: {args[0] if isinstance(args[0], str) else join_command_args(args[0])}', file=sys.stderr)
    process = subprocess.run(*args, **kwargs)
    if process.returncode:
        sys.exit(process.returncode)

    return process


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


def normalize_project_name(name: str) -> str:
    # https://peps.python.org/pep-0503/#normalized-names
    return UNNORMALIZED_PROJECT_NAME_CHARS.sub('-', name).lower()


@cache
def get_wheel_hashes(project) -> dict[str, str]:
    retry_wait = 2
    while True:
        try:
            response = urllib3.request(
                'GET',
                f'https://pypi.org/simple/{project}',
                headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            )
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

    data = response.json()
    return {
        file['filename']: file['hashes']['sha256']
        for file in data['files']
        if file['filename'].endswith('.whl') and 'sha256' in file['hashes']
    }


def wheel_was_built(wheel: Path) -> bool:
    project_metadata = extract_metadata(wheel)
    project_name = normalize_project_name(project_metadata['Name'])
    wheel_hashes = get_wheel_hashes(project_name)
    if wheel.name not in wheel_hashes:
        return True

    file_hash = sha256(wheel.read_bytes()).hexdigest()
    return file_hash != wheel_hashes[wheel.name]


# def remove_test_files(wheel_path: Path) -> bool:
#     '''
#     Unpack the wheel, remove excluded test files, then repack it to rebuild RECORD correctly.
#     '''
#     # First, check whether the wheel contains any files that should be excluded. If not, leave it untouched.
#     with ZipFile(wheel_path, 'r') as zf:
#         excluded_members = [name for name in zf.namelist() if is_excluded_from_wheel(name)]

#     if not excluded_members:
#         # Nothing to strip, so skip rewriting the wheel
#         return False
#     with TemporaryDirectory() as td:
#         td_path = Path(td)

#         # Unpack the wheel into temp dir
#         unpack(wheel_path, dest=td_path)
#         unpacked_dir = next(td_path.iterdir())
#         # Remove excluded files/folders
#         for root, dirs, files in os.walk(td, topdown=False):
#             for d in list(dirs):
#                 full_dir = Path(root) / d
#                 rel = full_dir.relative_to(unpacked_dir).as_posix()
#                 if is_excluded_from_wheel(rel):
#                     shutil.rmtree(full_dir)
#                     dirs.remove(d)
#             for f in files:
#                 rel = Path(root).joinpath(f).relative_to(unpacked_dir).as_posix()
#                 if is_excluded_from_wheel(rel):
#                     os.remove(Path(root) / f)

#         print(f'Tests removed from {wheel_path.name}')

#         dest_dir = wheel_path.parent
#         before = {p.resolve() for p in dest_dir.glob("*.whl")}
#         # Repack to same directory, regenerating RECORD
#         pack(unpacked_dir, dest_dir=dest_dir, build_number=None)

#         # The wheel might not be platform-specific, so repacking restores its original name.
#         # We need to move the repacked wheel to wheel_path, which was changed to be platform-specific.
#         after = {p.resolve() for p in wheel_path.parent.glob("*.whl")}
#         new_files = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)

#         if new_files:
#             shutil.move(str(new_files[0]), str(wheel_path))


#     return True


# def is_excluded_from_wheel(path: str | Path) -> bool:
#     """
#     Return True if `path` (file or directory) should be excluded per files_to_remove.toml.
#     Matches:
#       - type annotation files: **/*.pyi, **/py.typed
#       - test directories listed with a trailing '/'
#     """
#     spec = _load_excluded_spec()
#     rel = Path(path).as_posix()

#     if spec.match_file(rel) or spec.match_file(rel + "/"):
#         return True

#     return False


def add_dependency(dependencies: dict[str, str], sizes: dict[str, WheelSizes], wheel: Path) -> None:
    project_metadata = extract_metadata(wheel)
    project_name = normalize_project_name(project_metadata['Name'])
    project_version = project_metadata['Version']
    dependencies[project_name] = project_version
    sizes[project_name] = {'version': project_version, **calculate_wheel_sizes(wheel)}

def calculate_wheel_sizes(wheel_path: Path) -> WheelSizes:
    compressed_size = wheel_path.stat(follow_symlinks=True).st_size
    with ZipFile(wheel_path) as zf:
        uncompressed_size = sum(zinfo.file_size for zinfo in zf.infolist())
    return {'compressed': compressed_size, 'uncompressed': uncompressed_size}


def main():
    parser = argparse.ArgumentParser(prog='wheel-builder', allow_abbrev=False)
    parser.add_argument('--python', required=True)
    parser.add_argument('--use-built-index', action='store_true', default=False)
    args = parser.parse_args()

    python_version = args.python
    if python_version == '3':
        python_path = PY3_PATH
    elif python_version == '2':
        python_path = PY2_PATH
    else:
        abort(f'Invalid python version: {python_version}')

    wheels_dir = MOUNT_DIR / 'wheels'
    built_wheels_dir = wheels_dir / 'built'
    external_wheels_dir = wheels_dir / 'external'

    # Install build dependencies
    check_process([str(python_path), '-m', 'pip', 'install', '-r', str(MOUNT_DIR / 'build_dependencies.txt')])

    with TemporaryDirectory() as d:
        staged_wheel_dir = Path(d).resolve()
        staged_built_wheels_dir = staged_wheel_dir / 'built'
        staged_external_wheels_dir = staged_wheel_dir / 'external'

        # Create the directories
        staged_built_wheels_dir.mkdir(parents=True, exist_ok=True)
        staged_external_wheels_dir.mkdir(parents=True, exist_ok=True)

        env_vars = dict(os.environ)
        env_vars['PATH'] = f'{python_path.parent}{os.pathsep}{env_vars["PATH"]}'
        env_vars['PIP_WHEEL_DIR'] = str(staged_wheel_dir)
        env_vars['DD_BUILD_PYTHON_VERSION'] = python_version
        env_vars['DD_MOUNT_DIR'] = str(MOUNT_DIR)
        env_vars['DD_ENV_FILE'] = str(ENV_FILE)

        # Off is on, see: https://github.com/pypa/pip/issues/5735
        env_vars['PIP_NO_BUILD_ISOLATION'] = '0'

        # Spaces are used to separate multiple values which means paths themselves cannot contain spaces, see:
        # https://github.com/pypa/pip/issues/10114#issuecomment-1880125475
        env_vars['PIP_FIND_LINKS'] = path_to_uri(staged_wheel_dir)

        # Perform builder-specific logic if required
        if build_command := os.environ.get('DD_BUILD_COMMAND'):
            check_process(build_command, env=env_vars, shell=True)

        # Load environment variables
        if ENV_FILE.is_file():
            for key, value in dotenv_values(str(ENV_FILE)).items():
                if value is None:
                    env_vars.pop(key, None)
                else:
                    env_vars[key] = value

        if constraints_file := env_vars.get('PIP_CONSTRAINT'):
            env_vars['PIP_CONSTRAINT'] = path_to_uri(constraints_file)
        print("--------------------------------")
        print("Building wheels")
        print("--------------------------------")
        # Fetch or build wheels
        command_args = [
            str(python_path),
            '-m',
            'pip',
            'wheel',
            '--config-settings=build-backend=.builders/scripts/build_backend.py',
            '-r',
            str(MOUNT_DIR / 'requirements.in'),
            '--wheel-dir',
            str(staged_wheel_dir),
            '--extra-index-url',
            CUSTOM_EXTERNAL_INDEX,
        ]
        print("--------------------------------")
        print("Finished building wheels")
        print("--------------------------------")
        check_process(command_args, env=env_vars)

        # Classify wheels
        for wheel in iter_wheels(staged_wheel_dir):
            if wheel_was_built(wheel):
                shutil.move(wheel, staged_built_wheels_dir)
            else:
                shutil.move(wheel, staged_external_wheels_dir)

        # Repair wheels
        check_process(
            [
                sys.executable,
                '-u',
                str(MOUNT_DIR / 'scripts' / 'repair_wheels.py'),
                '--source-built-dir',
                str(staged_built_wheels_dir),
                '--source-external-dir',
                str(staged_external_wheels_dir),
                '--built-dir',
                str(built_wheels_dir),
                '--external-dir',
                str(external_wheels_dir),
            ]
        )

    dependencies: dict[str, tuple[str, str]] = {}
    sizes: dict[str, WheelSizes] = {}

    # # Handle wheels currently in the external directory and move them to the built directory if they were modified
    # for wheel in iter_wheels(external_wheels_dir):
    #     was_modified = remove_test_files(wheel)
    #     if was_modified:
    #         # A modified wheel is no longer external → move it to built directory
    #         new_path = built_wheels_dir / wheel.name
    #         wheel.rename(new_path)
    #         wheel = new_path
    #         print(f'Moved {wheel.name} to built directory')

    #     add_dependency(dependencies, sizes, wheel)

    # # Handle wheels already in the built directory
    # for wheel in iter_wheels(built_wheels_dir):
    #     remove_test_files(wheel)
    #    add_dependency(dependencies, sizes, wheel)

    for wheel_dir in wheels_dir.iterdir():
        for wheel in wheel_dir.iterdir():
            project_metadata = extract_metadata(wheel)
            project_name = normalize_project_name(project_metadata['Name'])
            project_version = project_metadata['Version']
            dependencies[project_name] = project_version
            sizes[project_name] = {'version': project_version, **calculate_wheel_sizes(wheel)}

    output_path = MOUNT_DIR / 'sizes.json'
    with output_path.open('w', encoding='utf-8') as fp:
        json.dump(sizes, fp, indent=2, sort_keys=True)

    final_requirements = MOUNT_DIR / 'frozen.txt'
    with final_requirements.open('w', encoding='utf-8') as f:
        for project_name, project_version in sorted(dependencies.items()):
            f.write(f'{project_name}=={project_version}\n')


if __name__ == '__main__':
    main()
