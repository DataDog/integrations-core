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
import json
import sys
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent
PINNED_FILE = REPO_ROOT / '.deps' / 'builder_inputs.toml'

# TOML section/key names used in PINNED_FILE. Defined here so upload.py and
# tests don't drift from the reader.
SECTION_RESOLUTION = 'resolution'
SECTION_IMAGES = 'images'
HASH_KEY = 'hash'

# Glob patterns relative to .builders/ for inputs shared across all builder
# target images.
SHARED_INPUTS = [
    'build.py',
    'deps/build_dependencies.txt',
    'scripts/**/*',
    'patches/**/*',
    'images/helpers.ps1',
    'images/install-from-source.sh',
    'images/runner_dependencies.txt',
]

# Glob patterns relative to the repo root for inputs that affect resolution
# output (uv pip compile, builder images, wheels, lockfiles, published
# artifacts). Note: per-target image files are included wholesale, so a
# change to any single Dockerfile invalidates resolution for all targets.
# This is intentional — image contents determine what the resolved wheels
# can link against, so resolution is conservatively rerun on any image change.
RESOLUTION_INPUTS = [
    'agent_requirements.in',
    '.github/workflows/resolve-build-deps.yaml',
    '.builders/build.py',
    '.builders/upload.py',
    '.builders/inputs_hash.py',
    '.builders/targets.json',
    '.builders/deps/*.txt',
    '.builders/scripts/**/*',
    '.builders/patches/**/*',
    '.builders/images/**/*',
]

# A file under .builders/ is one of:
#   - covered: matched by a SHARED_INPUTS or RESOLUTION_INPUTS pattern and
#     not filtered by _is_ignored. Enters the hash. Changes flip the hash.
#   - ignored: filtered by _is_ignored (dotfiles, __pycache__) OR exempted
#     by IGNORED_DIRS / IGNORED_FILES below. Doesn't enter the hash.
#     Changes don't flip the hash and don't error.
#   - uncovered: anything else. status() raises rather than silently
#     publishing a hash with a coverage hole.

# Subtrees under .builders/ that are ignored regardless of contents. Matched
# by relative POSIX path prefix.
IGNORED_DIRS = (
    'tests/',  # test infrastructure; not baked into any image or artifact
    'venv/',   # local virtualenv if a contributor created one
)

# Specific files under .builders/ that are ignored. Matched by full relative
# POSIX path so a future file at e.g. images/linux-x86_64/promote.py is not
# silently exempted.
IGNORED_FILES = frozenset({
    # Runs in the separate dependency-wheel-promotion.yaml workflow, not here.
    'promote.py',
    # mypy configuration only; does not affect build or resolution output.
    'pyproject.toml',
    # Runs in CI to install pytest/etc; not baked into any image or artifact.
    'test_dependencies.txt',
})


def _is_ignored(name: str) -> bool:
    return name.startswith('.') or name == '__pycache__'


def _literal_prefix(pattern: str) -> Path:
    """Return the leading part of `pattern` before any glob wildcard.

    Used to scope ignored-name filtering to parts of a matched path that are
    descendants of what the pattern explicitly named, so a pattern like
    `.github/workflows/resolve-build-deps.yaml` is not itself filtered as a
    dotfile while incidental dotfiles/__pycache__ inside `scripts/**/*` are.
    """
    parts: list[str] = []
    for part in Path(pattern).parts:
        if any(c in part for c in '*?['):
            break
        parts.append(part)
    return Path(*parts) if parts else Path()


def _iter_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root
    elif root.is_dir():
        for path in root.rglob('*'):
            if path.is_file():
                yield path


def _collect_paths(base: Path, patterns: list[str]) -> set[Path]:
    """Expand `patterns` under `base` to the set of files that would be hashed.

    Raises RuntimeError if a pattern matches no files, or if all matched files
    are filtered out as ignored (dotfiles, __pycache__). Either case means the
    pattern is no longer pulling content into the hash, so failing loud
    prevents the hash from silently narrowing.

    Filtering: parts of a matched path that come *after* the pattern's literal
    prefix are checked against `_is_ignored`. The literal prefix is exempt
    because the user named it explicitly (e.g. `.github/workflows/...` is a
    deliberate input even though `.github` looks like a dotfile).
    """
    paths: set[Path] = set()
    for pattern in patterns:
        matched = list(base.glob(pattern))
        if not matched:
            raise RuntimeError(f'pattern {pattern!r} matched no files under {base}')
        prefix_part_count = len(_literal_prefix(pattern).parts)

        def _filtered(path: Path) -> bool:
            rel_parts = path.relative_to(base).parts[prefix_part_count:]
            return any(_is_ignored(part) for part in rel_parts)

        pattern_paths: set[Path] = set()
        for p in matched:
            pattern_paths.update(f for f in _iter_files(p) if not _filtered(f))
        if not pattern_paths:
            raise RuntimeError(
                f'pattern {pattern!r} matched no hashable files under {base} '
                f'(all matches were filtered as ignored)'
            )
        paths.update(pattern_paths)
    return paths


def _uncovered(covered: set[Path]) -> list[str]:
    """Files under .builders/ that are neither covered nor ignored.

    A file is ignored if any part of its relative path is filtered by
    _is_ignored (dotfiles, __pycache__), OR it sits under IGNORED_DIRS, OR
    it matches IGNORED_FILES. Anything else not in `covered` is uncovered.

    The result is sorted relative POSIX paths so the JSON-encoded form is
    stable for downstream consumers and human inspection.
    """
    uncovered: list[str] = []
    for path in HERE.rglob('*'):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(HERE).parts
        if any(_is_ignored(part) for part in rel_parts):
            continue
        rel = path.relative_to(HERE).as_posix()
        if any(rel.startswith(prefix) for prefix in IGNORED_DIRS):
            continue
        if rel in IGNORED_FILES:
            continue
        if path in covered:
            continue
        uncovered.append(rel)
    return sorted(uncovered)


def _digest_paths(base: Path, paths: set[Path]) -> str:
    """SHA-256 the file set in a cross-OS-stable order.

    Sorting by relative POSIX path before hashing preserves cross-OS stability:
    WindowsPath sorting is case-insensitive and uses backslashes, which would
    produce a different hash than on POSIX systems for the same input set.
    """
    sorted_paths = sorted(paths, key=lambda p: p.relative_to(base).as_posix())
    digest = sha256()
    for path in sorted_paths:
        rel_path = path.relative_to(base).as_posix().encode('utf-8')
        digest.update(rel_path + b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def _hash_paths(base: Path, patterns: list[str]) -> str:
    """Hash all files matched by `patterns` (glob-expanded relative to `base`)."""
    return _digest_paths(base, _collect_paths(base, patterns))


def _compute_resolution() -> str:
    """Hash all resolution inputs relative to the repo root and return hex sha256."""
    return _hash_paths(REPO_ROOT, RESOLUTION_INPUTS)


@dataclass
class PinnedHashes:
    """In-memory representation of the builder_inputs.toml schema.

    Empty `resolution` (or empty `images` dict) indicates a missing section
    rather than an empty hash — the writer omits empty sections, and readers
    treat empty values as "unpinned".
    """
    resolution: str = ''
    images: dict[str, str] = field(default_factory=dict)


_BUILDER_INPUTS_HEADER = """\
# Content hashes of the inputs that determine the resolution pipeline and each
# builder image.
#
# The `Resolve Dependencies and Build Wheels` workflow uses these hashes to
# gate the full pipeline (resolution.hash) and to decide whether to rebuild a
# builder image from scratch or pull the existing one by digest (images.*).
# The `verify-deps-pin` workflow checks resolution.hash on merge-queue refs.
#
# This file is rewritten by .builders/upload.py whenever dependency resolution
# publishes new artifacts and should not be edited by hand.
# Hash inputs are defined in .builders/inputs_hash.py (SHARED_INPUTS,
# RESOLUTION_INPUTS).
"""


def write_pinned_hashes(path: Path, hashes: PinnedHashes) -> None:
    """Write `hashes` to `path` as builder_inputs.toml.

    Empty fields are omitted from the output. Parent directory is created if
    missing so callers don't need a prior mkdir step.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [_BUILDER_INPUTS_HEADER.rstrip('\n')]
    if hashes.resolution:
        lines.append(f'[{SECTION_RESOLUTION}]')
        lines.append(f'{HASH_KEY} = "{hashes.resolution}"')
        lines.append('')
    if hashes.images:
        lines.append(f'[{SECTION_IMAGES}]')
        for target in sorted(hashes.images):
            lines.append(f'{target} = "{hashes.images[target]}"')
    path.write_text('\n'.join(lines).rstrip('\n') + '\n', encoding='utf-8')


def _load_pinned_hashes() -> PinnedHashes:
    """Read PINNED_FILE and return a PinnedHashes; empty fields on missing/unset.

    Unknown TOML sections or keys are silently ignored — additions to the
    schema must update PinnedHashes, this reader, and write_pinned_hashes.
    """
    if not PINNED_FILE.is_file():
        print(f'{PINNED_FILE} not found; treating as unpinned', file=sys.stderr)
        return PinnedHashes()
    try:
        with PINNED_FILE.open('rb') as f:
            raw = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise RuntimeError(
            f'{PINNED_FILE} is malformed; it is regenerated by .builders/upload.py, '
            f'rerun resolve-build-deps if it is corrupted: {e}'
        ) from e
    return PinnedHashes(
        resolution=raw.get(SECTION_RESOLUTION, {}).get(HASH_KEY, ''),
        images=raw.get(SECTION_IMAGES, {}),
    )


def _pinned_target(target: str) -> str:
    """Return the hash pinned for `target` in builder_inputs.toml, or empty if absent."""
    images = _load_pinned_hashes().images
    if target not in images:
        print(f'{PINNED_FILE}: no entry for {target}; treating as unpinned', file=sys.stderr)
        return ''
    return images[target]


def _pinned_resolution() -> str:
    """Return the resolution hash pinned in builder_inputs.toml, or empty if absent."""
    pinned = _load_pinned_hashes().resolution
    if not pinned:
        print(f'{PINNED_FILE}: no [{SECTION_RESOLUTION}] hash; treating as unpinned', file=sys.stderr)
        return ''
    return pinned


def _check(label: str, current: str, pinned: str) -> bool:
    """Print current/pinned/fresh-or-STALE status to stderr and return whether they match."""
    fresh = current == pinned
    print(
        f'{label}: current={current}\n'
        f'{label}: pinned ={pinned}\n'
        f'{label}: {"fresh" if fresh else "STALE"}',
        file=sys.stderr,
    )
    return fresh


def _verify_resolution(current: str | None = None) -> str:
    """Return 'fresh', 'stale', or 'unpinned' for the working-tree resolution hash.

    'unpinned' means there is no `[resolution]` section yet — distinct from
    'stale' so callers can tell bootstrap apart from a real mismatch.
    `current` may be passed in by callers that have already computed it (e.g.
    status()) to avoid re-walking the input tree.
    """
    if current is None:
        current = _compute_resolution()
    pinned = _pinned_resolution()
    if not pinned:
        print(
            f'{PINNED_FILE}: no [{SECTION_RESOLUTION}] hash found; dependency resolution has '
            f'not yet published a pin. Expected during the initial rollout; once '
            f'resolve-build-deps publishes once on master, this check starts working '
            f'normally.',
            file=sys.stderr,
        )
        return 'unpinned'
    return 'fresh' if _check('resolution', current, pinned) else 'stale'


def status(targets_file: Path) -> dict[str, str]:
    """Compute gate outputs for the targets in `targets_file` and return them as $GITHUB_OUTPUT key=value pairs.

    `targets_file` is a JSON list of `{"platform", "arch", "runner_os"}` entries.
    The image directory name is derived as f"{platform}-{arch}" — the canonical
    target identifier under .builders/images/.

    Side effect: prints human-readable current/pinned/fresh-or-STALE lines for
    each hash to stderr.

    Any target that needs rebuilding also forces resolution: a new builder
    image can change which wheels link successfully (system libraries, build
    tools, manylinux selection), so re-resolving on target drift is the safe
    conservative default.

    Raises RuntimeError if any file under .builders/ is uncovered (neither
    matched by an input pattern nor ignored). This fails the gate loudly
    rather than silently publishing a hash with a coverage hole.

    Output keys: `needs_resolution` (bool string), `matrix_container` and
    `matrix_macos` (JSON lists of matrix entries, one per target, each with
    image/platform/arch/runner_os/hash/rebuild), `resolution_hash` (the
    working-tree resolution hash, passed downstream so upload.py can write
    it into the pin without recomputing).
    """
    target_rows = json.loads(targets_file.read_text(encoding='utf-8'))
    covered: set[Path] = set()

    resolution_paths = _collect_paths(REPO_ROOT, RESOLUTION_INPUTS)
    covered |= resolution_paths
    resolution_hash = _digest_paths(REPO_ROOT, resolution_paths)
    resolution_stale = _verify_resolution(resolution_hash) != 'fresh'
    outputs: dict[str, str] = {'resolution_hash': resolution_hash}
    container_rows: list[dict[str, str]] = []
    macos_rows: list[dict[str, str]] = []
    any_target_stale = False
    for row in target_rows:
        target = f"{row['platform']}-{row['arch']}"
        target_dir = HERE / 'images' / target
        if not target_dir.is_dir():
            raise FileNotFoundError(f'Unknown builder target: {target} (expected {target_dir})')
        target_patterns = SHARED_INPUTS + [f'images/{target}/**/*']
        if row['platform'] == 'macos':
            target_patterns.append('images/macos/**/*')
        target_paths = _collect_paths(HERE, target_patterns)
        covered |= target_paths
        current = _digest_paths(HERE, target_paths)
        fresh = _check(target, current, _pinned_target(target))
        entry = {**row, 'image': target, 'hash': current, 'rebuild': str(not fresh).lower()}
        (macos_rows if row['platform'] == 'macos' else container_rows).append(entry)
        any_target_stale = any_target_stale or not fresh
    outputs['needs_resolution'] = str(resolution_stale or any_target_stale).lower()
    outputs['matrix_container'] = json.dumps(container_rows, sort_keys=True)
    outputs['matrix_macos'] = json.dumps(macos_rows, sort_keys=True)
    uncovered = _uncovered(covered)
    if uncovered:
        raise RuntimeError(
            f'{len(uncovered)} uncovered file(s) under .builders/ '
            f'(not matched by any input pattern, not ignored): '
            f'{", ".join(uncovered)}. '
            'For of these files, please decide if you want it to affect the decision to rerun the resolution.'
        )
    return outputs


def _build_parser() -> argparse.ArgumentParser:
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
        help='Emit needs_resolution, matrix_container, matrix_macos, and resolution_hash to $GITHUB_OUTPUT.',
    )
    status_parser.add_argument('targets_file', type=Path, metavar='TARGETS_FILE')

    subparsers.add_parser(
        'verify-resolution',
        help='Exit 0 if resolution hash matches pinned; exit 1 on mismatch.',
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == 'status':
        for key, value in status(args.targets_file).items():
            sys.stdout.write(f'{key}={value}\n')
    elif args.command == 'verify-resolution':
        result = _verify_resolution()
        if result == 'stale':
            print(
                'Resolution pin is stale. Rebase your branch onto master to re-trigger '
                'dependency resolution and update the pin.',
                file=sys.stderr,
            )
            sys.exit(1)
        elif result == 'unpinned':
            sys.exit(1)


if __name__ == '__main__':
    main()
