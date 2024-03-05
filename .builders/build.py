from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Generator, Optional

from packaging.requirements import InvalidRequirement, Requirement

if TYPE_CHECKING:
    from collections.abc import Iterable

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
        if kwargs.get('capture_output', False):
            print(process.stderr.decode('utf-8'), file=sys.stderr)

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
    parser = argparse.ArgumentParser(prog='builder', allow_abbrev=False)
    parser.add_argument('image')
    parser.add_argument('output_dir')
    parser.add_argument('--python', default='3')
    parser.add_argument('--builder-root', required=True,
                        help='Path to a folder where things will be installed during builder setup.')
    parser.add_argument('--skip-setup', default=False, action='store_true',
                        help='Skip builder setup, assuming it has already been set up.')
    args = parser.parse_args()

    image: str = args.image
    context_path = HERE / 'images' / image
    builder_root = Path(args.builder_root).absolute()
    builder_root.mkdir(exist_ok=True)

    with temporary_directory() as temp_dir:
        mount_dir = temp_dir / 'mnt'
        mount_dir.mkdir()

        build_context_dir = shutil.copytree(context_path, mount_dir / 'build_context', dirs_exist_ok=True)
        # Copy utilities shared by multiple images
        for entry in context_path.parent.iterdir():
            if entry.is_file():
                shutil.copy2(entry, build_context_dir)

        # Folders required by the build_wheels script
        wheels_dir = mount_dir / 'wheels'
        wheels_dir.mkdir()
        built_wheels_dir = wheels_dir / 'built'
        built_wheels_dir.mkdir()
        external_wheels_dir = wheels_dir / 'external'
        external_wheels_dir.mkdir()

        dependency_file = mount_dir / 'requirements.in'
        dependency_file.write_text('\n'.join(chain.from_iterable(read_dependencies().values())))
        shutil.copy(HERE / 'deps' / 'build_dependencies.txt', mount_dir)
        shutil.copytree(HERE / 'scripts', mount_dir / 'scripts')
        shutil.copytree(HERE / 'patches', mount_dir / 'patches')

        prefix_path = builder_root / 'prefix'
        env = {
            **os.environ,
            'DD_MOUNT_DIR': mount_dir,
            'DD_ENV_FILE': mount_dir / '.env',
            # Paths to pythons
            'DD_PY3_BUILDENV_PATH': builder_root / 'py3' / 'bin' / 'python',
            'DD_PY2_BUILDENV_PATH': builder_root / 'py2' / 'bin' / 'python',
            # Path where we'll install libraries that we build
            'DD_PREFIX_PATH': prefix_path,
            # Common compilation flags
            'LDFLAGS': f'-L{prefix_path}/lib',
            'CFLAGS': f'-I{prefix_path}/include -O2',
            # Build command for extra platform-specific build steps
            'DD_BUILD_COMMAND': f'bash {build_context_dir}/extra_build.sh'
        }

        if not args.skip_setup:
            check_process(
                ['bash', str(HERE / 'images' / image / 'builder_setup.sh')],
                env=env,
                cwd=builder_root,
            )

        check_process(
            [os.environ['DD_PYTHON3'], str(mount_dir / 'scripts' / 'build_wheels.py'), '--python', args.python],
            env=env,
            cwd=builder_root,
        )

        output_dir = Path(args.output_dir)
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        if output_dir.is_dir():
            shutil.rmtree(output_dir)

        # Move wheels to the output directory
        wheels_dir = mount_dir / 'wheels'
        shutil.move(wheels_dir, output_dir / 'wheels')

        # Move the final requirements file to the output directory
        final_requirements = mount_dir / 'frozen.txt'
        shutil.move(final_requirements, output_dir)


def hash_build_context(build_context: Path, build_arguments: Iterable[str]) -> str:
    """Compute a hash digest for a Docker build context"""
    result = hashlib.sha256()
    for root, _, files in os.walk(build_context):
        for fname in files:
            with open(os.path.join(root, fname), 'rb') as f:
                result.update(f.read())

    for arg in build_arguments:
        result.update(arg.encode('utf-8'))

    return result.hexdigest()


def is_windows_image(image_name: str) -> bool:
    return image_name.startswith('windows-')


def build_or_pull_image(
        image: str, digest: Optional[str] = None, build_args: Optional[str] = None, verbose: bool = False
) -> str:
    """Build or pull an image and return the full name including tag"""
    target_image = 'ghcr.io/datadog/agent-int-builder'
    image_path = HERE / 'images' / image
    if not image_path.is_dir():
        abort(f'Image does not exist: {image_path}')

    with temporary_directory() as temp_dir:
        build_context_dir = shutil.copytree(image_path, temp_dir, dirs_exist_ok=True)

        # Copy utilities shared by multiple images
        for entry in image_path.parent.iterdir():
            if entry.is_file():
                shutil.copy2(entry, build_context_dir)

        build_args = ['SOURCE_DATE_EPOCH=1580601600']
        if build_args is not None:
            build_args.extend(build_args)

        build_context_hash = hash_build_context(build_context_dir, build_args)
        image_name = f'{target_image}:{build_context_hash}'

        print(f'Hash for the build context: {build_context_hash}')

        if digest:
            try:
                # Try to pull the image first if args.digest was specified
                check_process(['docker', 'pull', f'{image_name}@{digest}'], check=True)
            except subprocess.CalledProcessError:
                # If pull fails, assume the image is not available in the registry and build it
                print('`docker pull` failed. Assuming the image is not in the registry, will build the image')
            else:
                # Pull succeeded, no need to build
                print('Pull succeeded')
                return image_name

        build_command = ['docker', 'build', str(build_context_dir), '-t', image_name]

        # For some reason this is not supported for Windows images
        if verbose and not is_windows_image(image):
            build_command.extend(['--progress', 'plain'])

        for build_arg in build_args:
            build_command.extend(['--build-arg', build_arg])

        check_process(build_command)

        # Add a tag identifying the platform
        check_process(['docker', 'tag', image_name, f'{target_image}:{image}'])

        return image_name


def build_in_docker():
    parser = argparse.ArgumentParser(prog='builder', allow_abbrev=False)
    parser.add_argument('image')
    parser.add_argument('output_dir')
    parser.add_argument('--digest')
    parser.add_argument('--python', default='3')
    parser.add_argument('--no-run', action='store_true')
    parser.add_argument('--outputs-file',
                        help='File to write information about the build in key=value format')
    parser.add_argument('-a', '--build-arg', dest='build_args', nargs='+')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    image_name = build_or_pull_image(args.image, args.digest, args.build_args, args.verbose)
    if args.outputs_file:
        with open(args.outputs_file, 'a') as f:
            print(f'builder_image={image_name}', file=f)

    if not args.no_run:
        with temporary_directory() as temp_dir:
            mount_dir = temp_dir / 'mnt'
            mount_dir.mkdir()
            internal_mount_dir = 'C:\\mnt' if is_windows_image(args.image) else '/home'

            dependency_file = mount_dir / 'requirements.in'
            dependency_file.write_text('\n'.join(chain.from_iterable(read_dependencies().values())))
            shutil.copy(HERE / 'deps' / 'build_dependencies.txt', mount_dir)
            shutil.copytree(HERE / 'scripts', mount_dir / 'scripts')
            shutil.copytree(HERE / 'patches', mount_dir / 'patches')

            # Create outputs on the host so they can be removed
            wheels_dir = mount_dir / 'wheels'
            wheels_dir.mkdir()
            built_wheels_dir = wheels_dir / 'built'
            built_wheels_dir.mkdir()
            external_wheels_dir = wheels_dir / 'external'
            external_wheels_dir.mkdir()
            final_requirements = mount_dir / 'frozen.txt'
            final_requirements.touch()

            check_process([
                'docker', 'run', '--rm',
                '-v', f'{mount_dir}:{internal_mount_dir}',
                # Anything created within directories mounted to the container cannot be removed by the host
                '-e', 'PYTHONDONTWRITEBYTECODE=1',
                image_name, '--python', args.python,
            ])

            output_dir = Path(args.output_dir)
            output_dir.parent.mkdir(parents=True, exist_ok=True)
            if output_dir.is_dir():
                shutil.rmtree(output_dir)

            # Move wheels to the output directory
            shutil.move(wheels_dir, output_dir / 'wheels')

            # Move the final requirements file to the output directory
            shutil.move(final_requirements, output_dir)


def main():
    if sys.platform == 'darwin':
        build_macos()
    else:
        build_in_docker()


if __name__ == '__main__':
    main()
