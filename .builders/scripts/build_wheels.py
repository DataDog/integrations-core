from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypedDict
from zipfile import ZipFile

from dotenv import dotenv_values
from utils import extract_metadata, normalize_project_name

INDEX_BASE_URL = 'https://agent-int-packages.datadoghq.com'
CUSTOM_EXTERNAL_INDEX = f'{INDEX_BASE_URL}/external'
CUSTOM_BUILT_INDEX = f'{INDEX_BASE_URL}/built'


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

    print("--------------------------------")
    print("[DEBUGGING INFO]")
    print("running on: ", sys.platform)
    print("architecture: ", platform.machine())
    print("sys.version: ", sys.version)
    print("python_path: ", python_path)
    subprocess.run([python_path, "--version"])
    print("Platform:", sys.platform)
    print("--------------------------------")
    with TemporaryDirectory() as d:
        staged_wheel_dir = Path(d).resolve()
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

        # Fetch or build wheels
        command_args = [
            str(python_path),
            '-m',
            'pip',
            'wheel',
            '-r',
            str(MOUNT_DIR / 'requirements.in'),
            '--wheel-dir',
            str(staged_wheel_dir),
            # Temporarily removing extra index urls. See below.
            # '--extra-index-url', CUSTOM_EXTERNAL_INDEX,
        ]
        # Temporarily disable extra index urls. There are broken wheels in the gcloud bucket
        # while working on removing tests from them. Adding extra indices causes undefined behavior
        # and can pull a broken image, preventing the building from running.
        # if args.use_built_index:
        #     command_args.extend(['--extra-index-url', CUSTOM_BUILT_INDEX])

        check_process(command_args, env=env_vars)

        # Repair wheels
        check_process(
            [
                sys.executable,
                '-u',
                str(MOUNT_DIR / 'scripts' / 'repair_wheels.py'),
                '--source-dir',
                str(staged_wheel_dir),
                '--built-dir',
                str(built_wheels_dir),
                '--external-dir',
                str(external_wheels_dir),
            ]
        )

    dependencies: dict[str, tuple[str, str]] = {}
    sizes: dict[str, WheelSizes] = {}

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
