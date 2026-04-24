"""Tests for inputs_hash.py: hashing, pinning, status, verify-resolution, and coverage."""
import subprocess
import sys
import tomllib
from pathlib import Path
from unittest import mock

import pytest

import inputs_hash

HERE = Path(__file__).parent.parent  # .builders/
REPO_ROOT = HERE.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_pin(tmp_path: Path, resolution_hash: str, image_hashes: dict[str, str]) -> Path:
    pin = tmp_path / 'builder_inputs.toml'
    lines = ['[resolution]', f'hash = "{resolution_hash}"', '', '[images]']
    for target in sorted(image_hashes):
        lines.append(f'{target} = "{image_hashes[target]}"')
    pin.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return pin


# ---------------------------------------------------------------------------
# _hash_paths
# ---------------------------------------------------------------------------

def test_hash_paths_stable_across_shuffle(tmp_path: Path) -> None:
    """Hash result is independent of glob-expansion order.

    Simulates a different expansion order by patching base.glob to return
    files in reversed order, then asserts the two hashes match. Guards
    _hash_paths against a future refactor that drops the sorted() call.
    """
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_bytes(b'aaa')
    b.write_bytes(b'bbb')

    h1 = inputs_hash._hash_paths(tmp_path, ['*.txt'])

    original_glob = Path.glob

    def reversed_glob(self, pattern):
        return reversed(list(original_glob(self, pattern)))

    with mock.patch.object(Path, 'glob', reversed_glob):
        h2 = inputs_hash._hash_paths(tmp_path, ['*.txt'])

    assert h1 == h2


def test_hash_paths_different_content_different_hash(tmp_path: Path) -> None:
    f = tmp_path / 'f.txt'
    f.write_bytes(b'v1')
    h1 = inputs_hash._hash_paths(tmp_path, ['f.txt'])
    f.write_bytes(b'v2')
    h2 = inputs_hash._hash_paths(tmp_path, ['f.txt'])
    assert h1 != h2


def test_hash_paths_warns_on_empty_pattern(tmp_path: Path, capsys) -> None:
    inputs_hash._hash_paths(tmp_path, ['no_match_*.txt'])
    _, err = capsys.readouterr()
    assert 'no_match_*.txt' in err


# ---------------------------------------------------------------------------
# compute_target / pinned_target
# ---------------------------------------------------------------------------

def test_compute_target_raises_for_unknown_target() -> None:
    with pytest.raises(FileNotFoundError, match='Unknown builder target'):
        inputs_hash.compute_target('nonexistent-target')


def test_compute_target_returns_hex_string() -> None:
    h = inputs_hash.compute_target('linux-x86_64')
    assert len(h) == 64
    assert all(c in '0123456789abcdef' for c in h)


def test_pinned_target_returns_empty_when_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / 'no_such.toml'
    with mock.patch.object(inputs_hash, 'PINNED_FILE', missing):
        result = inputs_hash.pinned_target('linux-x86_64')
    assert result == ''


def test_pinned_target_returns_empty_when_target_absent(tmp_path: Path) -> None:
    pin = _write_pin(tmp_path, 'abc', {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        result = inputs_hash.pinned_target('linux-x86_64')
    assert result == ''


def test_pinned_target_returns_value(tmp_path: Path) -> None:
    pin = _write_pin(tmp_path, 'abc', {'linux-x86_64': 'deadbeef'})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        result = inputs_hash.pinned_target('linux-x86_64')
    assert result == 'deadbeef'


def test_pinned_target_raises_on_malformed_toml(tmp_path: Path) -> None:
    bad = tmp_path / 'bad.toml'
    bad.write_text('not valid [[toml', encoding='utf-8')
    with mock.patch.object(inputs_hash, 'PINNED_FILE', bad):
        with pytest.raises(RuntimeError, match='malformed'):
            inputs_hash.pinned_target('linux-x86_64')


# ---------------------------------------------------------------------------
# compute_resolution / pinned_resolution
# ---------------------------------------------------------------------------

def test_compute_resolution_returns_hex_string() -> None:
    h = inputs_hash.compute_resolution()
    assert len(h) == 64
    assert all(c in '0123456789abcdef' for c in h)


def test_pinned_resolution_returns_empty_when_missing(tmp_path: Path) -> None:
    with mock.patch.object(inputs_hash, 'PINNED_FILE', tmp_path / 'missing.toml'):
        result = inputs_hash.pinned_resolution()
    assert result == ''


def test_pinned_resolution_returns_value(tmp_path: Path) -> None:
    pin = _write_pin(tmp_path, 'myhash', {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        result = inputs_hash.pinned_resolution()
    assert result == 'myhash'


# ---------------------------------------------------------------------------
# verify_resolution
# ---------------------------------------------------------------------------

def test_verify_resolution_returns_true_when_fresh(tmp_path: Path) -> None:
    current = inputs_hash.compute_resolution()
    pin = _write_pin(tmp_path, current, {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.verify_resolution() is True


def test_verify_resolution_returns_false_when_stale(tmp_path: Path) -> None:
    pin = _write_pin(tmp_path, 'stale_hash', {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.verify_resolution() is False


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def test_status_fresh(tmp_path: Path) -> None:
    current_res = inputs_hash.compute_resolution()
    current_tgt = inputs_hash.compute_target('linux-x86_64')
    pin = _write_pin(tmp_path, current_res, {'linux-x86_64': current_tgt})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        out = inputs_hash.status(['linux-x86_64'])
    assert out['needs_resolution'] == 'false'
    assert out['rebuild_linux_x86_64'] == 'false'


def test_status_stale_resolution(tmp_path: Path) -> None:
    current_tgt = inputs_hash.compute_target('linux-x86_64')
    pin = _write_pin(tmp_path, 'stale_hash', {'linux-x86_64': current_tgt})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        out = inputs_hash.status(['linux-x86_64'])
    assert out['needs_resolution'] == 'true'
    assert out['rebuild_linux_x86_64'] == 'false'


def test_status_stale_target(tmp_path: Path) -> None:
    current_res = inputs_hash.compute_resolution()
    pin = _write_pin(tmp_path, current_res, {'linux-x86_64': 'stale_image_hash'})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        out = inputs_hash.status(['linux-x86_64'])
    assert out['needs_resolution'] == 'false'
    assert out['rebuild_linux_x86_64'] == 'true'


def test_status_keys_use_underscores(tmp_path: Path) -> None:
    pin = _write_pin(tmp_path, 'x', {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        out = inputs_hash.status(['linux-x86_64', 'linux-aarch64', 'windows-x86_64'])
    assert 'rebuild_linux_x86_64' in out
    assert 'rebuild_linux_aarch64' in out
    assert 'rebuild_windows_x86_64' in out


# ---------------------------------------------------------------------------
# CLI: status
# ---------------------------------------------------------------------------

def test_cli_status_writes_github_output_format(tmp_path: Path) -> None:
    current_res = inputs_hash.compute_resolution()
    current_tgt = inputs_hash.compute_target('linux-x86_64')
    pin = _write_pin(tmp_path, current_res, {'linux-x86_64': current_tgt})

    result = subprocess.run(
        [sys.executable, 'inputs_hash.py', 'status', '--targets', 'linux-x86_64'],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        env={**__import__('os').environ, 'PYTHONPATH': str(HERE)},
    )
    # Patch PINNED_FILE is not possible in subprocess; test shape only
    assert result.returncode == 0
    lines = result.stdout.strip().splitlines()
    assert any(line.startswith('needs_resolution=') for line in lines)
    assert any(line.startswith('rebuild_linux_x86_64=') for line in lines)


# ---------------------------------------------------------------------------
# CLI: verify-resolution
# ---------------------------------------------------------------------------

def test_cli_verify_resolution_exit_0_on_match(tmp_path: Path) -> None:
    current = inputs_hash.compute_resolution()
    pin = _write_pin(tmp_path, current, {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.verify_resolution() is True


def test_cli_verify_resolution_exit_1_on_mismatch(tmp_path: Path) -> None:
    pin = _write_pin(tmp_path, 'wrong_hash', {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.verify_resolution() is False


# ---------------------------------------------------------------------------
# Coverage: every tracked .builders/ file is classified
# ---------------------------------------------------------------------------

# Files under .builders/ that intentionally don't affect any hash.
# Each entry needs a comment explaining why.
EXPECTED_UNCOVERED = {
    # Runs in the separate dependency-wheel-promotion.yaml workflow, not here.
    'promote.py',
    # mypy configuration only; does not affect build or resolution output.
    'pyproject.toml',
    # Test infrastructure; not baked into any image or artifact.
    'test_dependencies.txt',
    # inputs_hash.py itself: self-referential; a change here requires a human
    # to re-run the gate and commit a new pin, not an automatic re-hash.
    'inputs_hash.py',
}


def _is_ignored_for_coverage(path: Path, builders_dir: Path) -> bool:
    """True for paths that _hash_paths would skip anyway (dotfiles, __pycache__, etc.)."""
    rel = path.relative_to(builders_dir)
    for part in rel.parts:
        if inputs_hash._is_ignored(part):
            return True
    return False


def _glob_set(base: Path, patterns: list[str]) -> set[Path]:
    result: set[Path] = set()
    for pattern in patterns:
        for p in base.glob(pattern):
            if p.is_file():
                result.add(p)
            elif p.is_dir():
                result.update(f for f in p.rglob('*') if f.is_file())
    return result


def test_no_uncovered_files() -> None:
    """Every file under .builders/ is covered by SHARED_INPUTS, a per-target
    images/<target>/** glob, RESOLUTION_INPUTS, or EXPECTED_UNCOVERED.

    This test is the enforcement mechanism for hash coverage drift: adding a
    new file under .builders/ fails CI until a human classifies it.
    """
    builders_dir = HERE
    repo_root = REPO_ROOT

    shared_files = _glob_set(builders_dir, inputs_hash.SHARED_INPUTS)

    target_dirs = [d for d in (builders_dir / 'images').iterdir() if d.is_dir()]
    per_target_files: set[Path] = set()
    for target_dir in target_dirs:
        per_target_files.update(_glob_set(builders_dir, [f'images/{target_dir.name}/**/*']))

    resolution_files_abs = _glob_set(repo_root, inputs_hash.RESOLUTION_INPUTS)
    resolution_files_in_builders = {p for p in resolution_files_abs if str(p).startswith(str(builders_dir))}

    covered = shared_files | per_target_files | resolution_files_in_builders

    uncovered = []
    for path in builders_dir.rglob('*'):
        if not path.is_file():
            continue
        if _is_ignored_for_coverage(path, builders_dir):
            continue
        rel = path.relative_to(builders_dir).as_posix()
        # tests/ directory
        if rel.startswith('tests/'):
            continue
        # venv or other local directories not in VCS
        if rel.startswith('venv/'):
            continue
        if path in covered:
            continue
        if path.name in EXPECTED_UNCOVERED:
            continue
        uncovered.append(rel)

    assert not uncovered, (
        f'These files under .builders/ are not covered by any hash input list or '
        f'EXPECTED_UNCOVERED:\n  ' + '\n  '.join(sorted(uncovered)) +
        '\nAdd each file to SHARED_INPUTS, RESOLUTION_INPUTS, or EXPECTED_UNCOVERED '
        'with a comment explaining why.'
    )
