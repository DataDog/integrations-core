from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from contextlib import contextmanager
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
    parser.add_argument('output_dir')
    parser.add_argument('--python', default='3')
    parser.add_argument('--no-run', action='store_true')
    parser.add_argument('-a', '--build-arg', dest='build_args', nargs='+')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    image = args.image
    image_path = HERE / 'images' / image
    if not image_path.is_dir():
        abort(f'Image does not exist: {image_path}')

    windows_image = image.startswith('windows-')
    image_name = f'datadog/agent-int-builder-{image}:latest'
    with temporary_directory() as temp_dir:
        build_context_dir = shutil.copytree(image_path, temp_dir, dirs_exist_ok=True)

        # Copy utilities shared by multiple images
        for entry in image_path.parent.iterdir():
            if entry.is_file():
                shutil.copy2(entry, build_context_dir)

        build_command = ['docker', 'build', str(build_context_dir), '-t', image_name]

        # For some reason this is not supported for Windows images
        if args.verbose and not windows_image:
            build_command.extend(['--progress', 'plain'])

        if args.build_args is not None:
            for build_arg in args.build_args:
                build_command.extend(['--build-arg', build_arg])

        check_process(build_command)

    if not args.no_run:
        with temporary_directory() as temp_dir:
            mount_dir = temp_dir / 'mnt'
            mount_dir.mkdir()
            internal_mount_dir = 'C:\\mnt' if windows_image else '/home'

            dependency_file = mount_dir / 'requirements.in'
            dependency_file.write_text('\n'.join(chain.from_iterable(read_dependencies().values())))
            shutil.copy(HERE.parent / '.deps' / 'build_dependencies.txt', mount_dir)
            shutil.copytree(HERE / 'scripts', mount_dir / 'scripts')
            shutil.copytree(HERE / 'patches', mount_dir / 'patches')

            check_process([
                'docker', 'run', '--rm',
                '-v', f'{mount_dir}:{internal_mount_dir}',
                image_name, '--python', args.python,
            ])

            output_dir = Path(args.output_dir)
            if output_dir.is_dir():
                shutil.rmtree(output_dir)

            # Move wheels to the output directory
            wheels_dir = mount_dir / 'wheels'
            shutil.move(wheels_dir, output_dir / 'wheels')

            # Move the final requirements file to the output directory
            final_requirements = mount_dir / 'frozen.txt'
            shutil.move(final_requirements, output_dir)


def main():
    if sys.platform == 'darwin':
        build_macos()
    else:
        build_image()


if __name__ == '__main__':
    main()
