"""Content-hash the inputs that determine each builder container image.

The `Resolve Dependencies and Build Wheels` workflow uses these hashes to
decide whether to rebuild a builder image from scratch, or pull the existing
one by digest from .deps/image_digests.json. The pinned hashes live in
.deps/builder_inputs.toml and are rewritten by .builders/upload.py whenever
dependency resolution publishes new artifacts.

A "target" is one of the builder image names we maintain — one per
(OS, CPU architecture) pair that the Agent ships Python wheels for.
The names match the subdirectories of .builders/images/, for example:
`linux-x86_64`, `linux-aarch64`, `windows-x86_64`.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).parent
PINNED_FILE = HERE.parent / '.deps' / 'builder_inputs.toml'

# Files and directories whose contents determine a builder image. A change to
# any of these should force a rebuild. Paths are relative to .builders/ and
# are shared across all targets; per-target inputs live under images/<target>/.
COMMON_INPUTS = [
    'build.py',
    'deps/build_dependencies.txt',
    'scripts',
    'patches',
    'images/helpers.ps1',
    'images/install-from-source.sh',
    'images/runner_dependencies.txt',
]


def _iter_files(root: Path):
    if root.is_file():
        yield root
    elif root.is_dir():
        for path in root.rglob('*'):
            if path.is_file():
                yield path


def compute(target: str) -> str:
    """Hash the working-tree inputs for `target` and return hex sha256."""
    target_dir = HERE / 'images' / target
    if not target_dir.is_dir():
        raise FileNotFoundError(f'Unknown builder target: {target} (expected {target_dir})')

    paths: set[Path] = set()
    for rel in COMMON_INPUTS:
        paths.update(_iter_files(HERE / rel))
    paths.update(_iter_files(target_dir))

    # Sort by the relative POSIX path string, not by Path objects: WindowsPath
    # sorting is case-insensitive and uses backslashes, which produces a
    # different iteration order (and therefore a different hash) than on
    # POSIX systems for the same input set.
    sorted_paths = sorted(paths, key=lambda p: p.relative_to(HERE).as_posix())

    digest = sha256()
    for path in sorted_paths:
        rel_path = path.relative_to(HERE).as_posix().encode('utf-8')
        digest.update(rel_path + b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def pinned(target: str) -> str:
    """Return the hash pinned for `target` in builder_inputs.toml, or empty if absent."""
    if not PINNED_FILE.is_file():
        print(f'{PINNED_FILE} not found; treating as unpinned', file=sys.stderr)
        return ''
    with PINNED_FILE.open('rb') as f:
        data = tomllib.load(f)
    return data.get('inputs', {}).get(target, '')


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            'Gate rebuilds of the builder container images. The resolve-build-deps '
            'workflow compares the working-tree hash against the pinned hash to '
            'decide whether to rebuild from scratch or pull the existing image.'
        ),
        epilog=(
            'A "target" is a builder image name matching a subdirectory of '
            '.builders/images/ (e.g. linux-x86_64, linux-aarch64, windows-x86_64).\n\n'
            'Examples:\n'
            '  python .builders/inputs_hash.py compute linux-x86_64\n'
            '  python .builders/inputs_hash.py pinned  linux-x86_64\n'
            '  diff <(… compute linux-x86_64) <(… pinned linux-x86_64)'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    compute_parser = subparsers.add_parser(
        'compute',
        help='Hash the working-tree inputs for a target.',
        description=(
            'Answers "would the current tree produce a different image than '
            'the one we have pinned?". Run this against the checked-out tree '
            'and compare to `pinned` — a mismatch means the image needs a rebuild.'
        ),
        epilog=(
            'Examples:\n'
            '  python .builders/inputs_hash.py compute linux-x86_64\n'
            '  python .builders/inputs_hash.py compute windows-x86_64'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    compute_parser.add_argument('target', help='Builder image name (e.g. linux-x86_64).')

    pinned_parser = subparsers.add_parser(
        'pinned',
        help='Print the hash pinned for a target in .deps/builder_inputs.toml.',
        description=(
            'Answers "which inputs produced the image we are pulling today?". '
            'Returns an empty string when the file or entry is missing, so a '
            'naive string compare with `compute` correctly flags first-run and '
            'never-built targets as needing a rebuild.'
        ),
        epilog=(
            'Examples:\n'
            '  python .builders/inputs_hash.py pinned linux-x86_64\n'
            '  python .builders/inputs_hash.py pinned windows-x86_64'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pinned_parser.add_argument('target', help='Builder image name (e.g. linux-x86_64).')

    args = parser.parse_args()
    if args.command == 'compute':
        sys.stdout.write(compute(args.target))
    elif args.command == 'pinned':
        sys.stdout.write(pinned(args.target))


if __name__ == '__main__':
    main()
