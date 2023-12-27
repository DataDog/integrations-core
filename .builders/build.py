from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from functools import cache
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

from packaging.requirements import InvalidRequirement, Requirement

HERE = Path(__file__).parent
REQUIREMENTS_FILE = HERE.parent / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data' / 'agent_requirements.in'

if sys.platform == 'win32':

    def join_command_args(args: list[str]) -> str:
        return subprocess.list2cmdline(args)

else:
    import shlex

    def join_command_args(args: list[str]) -> str:
        return shlex.join(args)


def abort(message, *, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)


def check_process(*args, **kwargs) -> subprocess.CompletedProcess:
    print(f'Running: {join_command_args(args[0])}', file=sys.stderr)
    process = subprocess.run(*args, **kwargs)
    if process.returncode:
        sys.exit(process.returncode)

    return process


@cache
def default_python_version() -> str:
    constants_path = HERE.parent / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'
    contents = constants_path.read_text(encoding='utf-8')
    match = re.search(r'^PYTHON_VERSION = [\'"](.+)[\'"]$', contents, re.MULTILINE)
    if not match:
        abort(f'Could not find PYTHON_VERSION in {constants_path}')

    return match.group(1)


@contextmanager
def temporary_directory() -> Generator[Path, None, None]:
    with TemporaryDirectory() as directory:
        yield Path(directory).resolve()


def read_dependencies() -> dict[str, list[str]]:
    dependencies: dict[str, list[str]] = {}
    for i, line in enumerate(REQUIREMENTS_FILE.read_text(encoding='utf-8').splitlines()):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            abort(f'Invalid requirement {REQUIREMENTS_FILE}#{i + 1}: {line}')

        dependencies.setdefault(requirement.name, []).append(line)

    return dependencies


def build_macos():
    sys.exit('macOS is not supported')


def build_image():
    parser = argparse.ArgumentParser(prog='builder', allow_abbrev=False)
    parser.add_argument('image')
    parser.add_argument('--python')
    parser.add_argument('--no-run', action='store_true')
    args = parser.parse_args()

    image = args.image
    python_version = args.python or default_python_version()
    python_tag = python_version.replace('.', '')

    image_path = HERE / 'images' / image
    if not image_path.is_dir():
        abort(f'Image does not exist: {image_path}')

    image_name = f'datadog/agent-int-builder-{image}:{python_version}'
    check_process(
        ['docker', 'build', str(image_path), '-t', image_name, '--build-arg', f'PYTHON_MAJOR={python_tag}'],
    )

    if not args.no_run:
        with temporary_directory() as temp_dir:
            mount_dir = temp_dir / 'mnt'
            mount_dir.mkdir()

            dependency_file = mount_dir / 'requirements.in'
            dependency_file.write_text('\n'.join(chain.from_iterable(read_dependencies().values())))
            shutil.copy(HERE / '..' / '.deps' / 'build_dependencies.txt', mount_dir)
            shutil.copy(HERE / 'scripts' / 'build_dependencies.sh', mount_dir)

            check_process(['docker', 'run', '--rm', '-v', f'{mount_dir}:/home', image_name])


def main():
    if sys.platform == 'darwin':
        build_macos()
    else:
        build_image()


if __name__ == '__main__':
    main()
