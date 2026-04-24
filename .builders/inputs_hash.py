"""Content-hash builder image inputs and resolution inputs for change detection.

The `Resolve Dependencies and Build Wheels` workflow uses these hashes to
decide whether to rebuild a builder image from scratch or pull the existing
one by digest, and whether to run the full resolution pipeline at all.

A "target" is one of the builder image names we maintain — one per
(OS, CPU architecture) pair that the Agent ships Python wheels for.
The names match the subdirectories of .builders/images/, for example:
`linux-x86_64`, `linux-aarch64`, `windows-x86_64`.

SHARED_INPUTS and RESOLUTION_INPUTS are the source of truth for what counts
as a resolution input. See test_inputs_hash.py::test_no_uncovered_files for
enforcement that no file is accidentally excluded from coverage.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent
PINNED_FILE = REPO_ROOT / '.deps' / 'builder_inputs.toml'

# Glob patterns relative to .builders/ for inputs shared across all builder
# targets. A change to any matched file forces a rebuild of every target image.
# Per-target inputs live under images/<target>/ and are added automatically.
#
# Coverage enforcement: test_inputs_hash.py::test_no_uncovered_files walks
# .builders/ and asserts every tracked file is covered by SHARED_INPUTS, a
# per-target images/<target>/** glob, or RESOLUTION_INPUTS, or is in
# EXPECTED_UNCOVERED. Add new .builders/ files there before CI goes green.
SHARED_INPUTS = [
    'build.py',
    'deps/build_dependencies.txt',
    'scripts/**/*',
    'patches/**/*',
    'images/helpers.ps1',
    'images/install-from-source.sh',
    'images/runner_dependencies.txt',
]

# Glob patterns relative to the repo root for all inputs that affect the
# resolution pipeline output (uv pip compile, builder images, wheels,
# lockfiles, published artifacts).
#
# Coverage enforcement: same test as above.
RESOLUTION_INPUTS = [
    'agent_requirements.in',
    '.github/workflows/resolve-build-deps.yaml',
    '.builders/build.py',
    '.builders/upload.py',
    '.builders/deps/*.txt',
    '.builders/scripts/**/*',
    '.builders/patches/**/*',
    '.builders/images/**/*',
]


def _is_ignored(name: str) -> bool:
    if name == '.gitkeep':
        return False
    return name.startswith('.') or name == '__pycache__'


def _iter_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root
    elif root.is_dir():
        for path in root.rglob('*'):
            rel_parts = path.relative_to(root).parts
            if path.is_file() and not any(_is_ignored(part) for part in rel_parts):
                yield path


def _hash_paths(base: Path, patterns: list[str]) -> str:
    """Hash all files matched by `patterns` (glob-expanded relative to `base`).

    Sorting by relative POSIX path before hashing preserves cross-OS stability:
    WindowsPath sorting is case-insensitive and uses backslashes, which would
    produce a different hash than on POSIX systems for the same input set.
    """
    paths: set[Path] = set()
    for pattern in patterns:
        matched = list(base.glob(pattern))
        if not matched:
            print(f'warning: pattern {pattern!r} matched no files under {base}', file=sys.stderr)
        for p in matched:
            paths.update(_iter_files(p))

    sorted_paths = sorted(paths, key=lambda p: p.relative_to(base).as_posix())
    digest = sha256()
    for path in sorted_paths:
        rel_path = path.relative_to(base).as_posix().encode('utf-8')
        digest.update(rel_path + b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def compute_target(target: str) -> str:
    """Hash the working-tree inputs for `target` and return hex sha256."""
    target_dir = HERE / 'images' / target
    if not target_dir.is_dir():
        raise FileNotFoundError(f'Unknown builder target: {target} (expected {target_dir})')
    return _hash_paths(HERE, SHARED_INPUTS + [f'images/{target}/**/*'])


def pinned_target(target: str) -> str:
    """Return the hash pinned for `target` in builder_inputs.toml, or empty if absent."""
    if not PINNED_FILE.is_file():
        print(f'{PINNED_FILE} not found; treating as unpinned', file=sys.stderr)
        return ''
    try:
        with PINNED_FILE.open('rb') as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise RuntimeError(f'{PINNED_FILE} is malformed (it should not be edited by hand): {e}') from e
    images = data.get('images', {})
    if target not in images:
        print(f'{PINNED_FILE}: no entry for {target}; treating as unpinned', file=sys.stderr)
    return images.get(target, '')


def compute_resolution() -> str:
    """Hash all resolution inputs relative to the repo root and return hex sha256."""
    return _hash_paths(REPO_ROOT, RESOLUTION_INPUTS)


def pinned_resolution() -> str:
    """Return the resolution hash pinned in builder_inputs.toml, or empty if absent."""
    if not PINNED_FILE.is_file():
        print(f'{PINNED_FILE} not found; treating as unpinned', file=sys.stderr)
        return ''
    try:
        with PINNED_FILE.open('rb') as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise RuntimeError(f'{PINNED_FILE} is malformed (it should not be edited by hand): {e}') from e
    return data.get('resolution', {}).get('hash', '')


def verify_resolution() -> bool:
    """Return True if the working-tree resolution hash matches the pinned hash."""
    current = compute_resolution()
    pinned = pinned_resolution()
    _print_hash_status('resolution', current, pinned)
    return current == pinned


def _print_hash_status(label: str, current: str, pinned: str) -> None:
    print(f'{label}: current={current}', file=sys.stderr)
    print(f'{label}: pinned ={pinned}', file=sys.stderr)
    print(f'{label}: {"fresh" if current == pinned else "STALE"}', file=sys.stderr)


def status(targets: list[str]) -> dict[str, str]:
    """Compute needs_resolution and rebuild_<target> flags for all targets.

    Returns a dict mapping output key to 'true'/'false' string, suitable for
    writing to $GITHUB_OUTPUT.
    """
    resolution_current = compute_resolution()
    resolution_pinned = pinned_resolution()
    _print_hash_status('resolution', resolution_current, resolution_pinned)
    needs_resolution = resolution_current != resolution_pinned

    outputs: dict[str, str] = {'needs_resolution': str(needs_resolution).lower()}
    for target in targets:
        key = 'rebuild_' + target.replace('-', '_')
        current = compute_target(target)
        pinned = pinned_target(target)
        _print_hash_status(target, current, pinned)
        outputs[key] = str(current != pinned).lower()
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            'Hash the inputs that determine builder images and resolution output. '
            'Used by resolve-build-deps.yaml to gate the full pipeline and by '
            'verify-deps-pin.yaml to validate merged trees on queue refs.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    status_parser = subparsers.add_parser(
        'status',
        help='Emit needs_resolution and rebuild_<target> flags to stdout ($GITHUB_OUTPUT format).',
        description=(
            'Computes needs_resolution (resolution inputs changed) and '
            'rebuild_<target> (builder image inputs changed) for each named target. '
            'Writes key=value pairs to stdout for use with >> "$GITHUB_OUTPUT". '
            'Prints human-readable current/pinned/fresh-or-STALE lines to stderr. '
            'Exits 0 except on real errors.'
        ),
        epilog=(
            'Example:\n'
            '  python .builders/inputs_hash.py status '
            '--targets linux-x86_64 linux-aarch64 windows-x86_64 >> "$GITHUB_OUTPUT"'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    status_parser.add_argument(
        '--targets',
        nargs='+',
        required=True,
        metavar='TARGET',
        help='Builder image names (e.g. linux-x86_64).',
    )

    subparsers.add_parser(
        'verify-resolution',
        help='Exit 0 if resolution hash matches pinned; exit 1 on mismatch.',
        description=(
            'Used by verify-deps-pin.yaml on gh-readonly-queue/** refs to ensure '
            'the merged tree has a current resolution pin before merging. '
            'On mismatch, rebase your branch onto master to re-trigger resolution.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    args = parser.parse_args()
    if args.command == 'status':
        outputs = status(args.targets)
        for key, value in outputs.items():
            sys.stdout.write(f'{key}={value}\n')
    elif args.command == 'verify-resolution':
        if not verify_resolution():
            print(
                'Resolution pin is stale. Rebase your branch onto master to re-trigger '
                'dependency resolution and update the pin.',
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == '__main__':
    main()
