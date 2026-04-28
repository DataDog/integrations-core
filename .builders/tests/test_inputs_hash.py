"""Tests for inputs_hash.py: hashing, pinning, status, verify-resolution, and coverage."""
from pathlib import Path
from unittest import mock

import pytest

import inputs_hash

HERE = Path(__file__).parent.parent  # .builders/
REPO_ROOT = HERE.parent


def _write_pin(tmp_path: Path, resolution_hash: str, image_hashes: dict[str, str]) -> Path:
    """Write a builder_inputs.toml fixture with the given hashes."""
    pin = tmp_path / 'builder_inputs.toml'
    lines = [
        f'[{inputs_hash.SECTION_RESOLUTION}]',
        f'{inputs_hash.HASH_KEY} = "{resolution_hash}"',
        '',
        f'[{inputs_hash.SECTION_IMAGES}]',
    ]
    for target in sorted(image_hashes):
        lines.append(f'{target} = "{image_hashes[target]}"')
    pin.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return pin


# ---------------------------------------------------------------------------
# hash_paths
# ---------------------------------------------------------------------------

def test_hash_paths_stable_across_filesystem_order(tmp_path: Path) -> None:
    """Hash depends only on relative path + content, not filesystem iteration order.

    Two directories with the same set of files (same relative path, same
    content) must produce the same hash regardless of the order the underlying
    filesystem returns them. Guards against a refactor that drops the internal
    sorted() call.
    """
    dir_a = tmp_path / 'a'
    dir_b = tmp_path / 'b'
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / 'x.txt').write_bytes(b'xxx')
    (dir_a / 'y.txt').write_bytes(b'yyy')
    (dir_b / 'y.txt').write_bytes(b'yyy')
    (dir_b / 'x.txt').write_bytes(b'xxx')

    assert inputs_hash.hash_paths(dir_a, ['*.txt']) == inputs_hash.hash_paths(dir_b, ['*.txt'])


def test_hash_paths_different_content_different_hash(tmp_path: Path) -> None:
    """Changing a file's bytes produces a different hash."""
    f = tmp_path / 'f.txt'
    f.write_bytes(b'v1')
    h1 = inputs_hash.hash_paths(tmp_path, ['f.txt'])
    f.write_bytes(b'v2')
    h2 = inputs_hash.hash_paths(tmp_path, ['f.txt'])
    assert h1 != h2


def test_hash_paths_raises_on_empty_pattern(tmp_path: Path) -> None:
    """An empty glob match raises — the pattern lists are static, so empty means drift."""
    with pytest.raises(RuntimeError, match='matched no files'):
        inputs_hash.hash_paths(tmp_path, ['no_match_*.txt'])


def test_hash_paths_raises_when_only_ignored_files_match(tmp_path: Path) -> None:
    """A pattern matching a directory whose contents are entirely ignored raises.

    Without this guard, the hash would silently narrow to sha256(empty) when a
    pattern's expanded matches all live under filtered names like __pycache__
    or dotfile directories.
    """
    pkg = tmp_path / 'pkg'
    pkg.mkdir()
    (pkg / '__pycache__').mkdir()
    (pkg / '__pycache__' / 'm.pyc').write_bytes(b'x')
    with pytest.raises(RuntimeError, match='no hashable files'):
        inputs_hash.hash_paths(tmp_path, ['pkg'])


# ---------------------------------------------------------------------------
# compute_target / pinned_target
# ---------------------------------------------------------------------------

def test_compute_target_raises_for_unknown_target() -> None:
    """An unknown target name is a usage error and must raise."""
    with pytest.raises(FileNotFoundError, match='Unknown builder target'):
        inputs_hash.compute_target('nonexistent-target')


def test_compute_target_returns_hex_string() -> None:
    """compute_target returns a 64-character hex sha256 for a valid target."""
    h = inputs_hash.compute_target('linux-x86_64')
    assert len(h) == 64
    assert all(c in '0123456789abcdef' for c in h)


def test_pinned_target_returns_empty_when_file_missing(tmp_path: Path) -> None:
    """No pin file at all is treated as unpinned."""
    missing = tmp_path / 'no_such.toml'
    with mock.patch.object(inputs_hash, 'PINNED_FILE', missing):
        assert inputs_hash.pinned_target('linux-x86_64') == ''


def test_pinned_target_returns_empty_when_images_section_missing(tmp_path: Path) -> None:
    """A pin file with no [images] section is treated as unpinned for every target."""
    pin = tmp_path / 'pin.toml'
    pin.write_text(
        f'[{inputs_hash.SECTION_RESOLUTION}]\n{inputs_hash.HASH_KEY} = "x"\n',
        encoding='utf-8',
    )
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.pinned_target('linux-x86_64') == ''


def test_pinned_target_returns_empty_when_target_absent(tmp_path: Path) -> None:
    """A pin file with [images] but no entry for the target is treated as unpinned."""
    pin = _write_pin(tmp_path, 'abc', {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.pinned_target('linux-x86_64') == ''


def test_pinned_target_returns_value(tmp_path: Path) -> None:
    """A pinned target returns the hash exactly as stored."""
    pin = _write_pin(tmp_path, 'abc', {'linux-x86_64': 'deadbeef'})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.pinned_target('linux-x86_64') == 'deadbeef'


def test_pinned_target_raises_on_malformed_toml(tmp_path: Path) -> None:
    """A corrupt pin file raises rather than silently acting unpinned."""
    bad = tmp_path / 'bad.toml'
    bad.write_text('not valid [[toml', encoding='utf-8')
    with mock.patch.object(inputs_hash, 'PINNED_FILE', bad):
        with pytest.raises(RuntimeError, match='malformed'):
            inputs_hash.pinned_target('linux-x86_64')


# ---------------------------------------------------------------------------
# pinned_resolution
# ---------------------------------------------------------------------------

def test_pinned_resolution_returns_empty_when_missing(tmp_path: Path) -> None:
    """No pin file at all is treated as unpinned."""
    with mock.patch.object(inputs_hash, 'PINNED_FILE', tmp_path / 'missing.toml'):
        assert inputs_hash.pinned_resolution() == ''


def test_pinned_resolution_returns_empty_when_section_missing(tmp_path: Path) -> None:
    """A pin file with no [resolution] section is treated as unpinned (bootstrap case)."""
    pin = tmp_path / 'pin.toml'
    pin.write_text(
        f'[{inputs_hash.SECTION_IMAGES}]\nlinux-x86_64 = "abc"\n',
        encoding='utf-8',
    )
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.pinned_resolution() == ''


def test_pinned_resolution_returns_value(tmp_path: Path) -> None:
    """A populated [resolution].hash is returned exactly."""
    pin = _write_pin(tmp_path, 'myhash', {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.pinned_resolution() == 'myhash'


# ---------------------------------------------------------------------------
# verify_resolution
# ---------------------------------------------------------------------------

def test_verify_resolution_returns_true_when_fresh(tmp_path: Path) -> None:
    """A matching pin returns True (workflow will skip resolution)."""
    current = inputs_hash.compute_resolution()
    pin = _write_pin(tmp_path, current, {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.verify_resolution() is True


def test_verify_resolution_returns_false_when_stale(tmp_path: Path) -> None:
    """A mismatched pin returns False (workflow will rerun resolution)."""
    pin = _write_pin(tmp_path, 'stale_hash', {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.verify_resolution() is False


def test_verify_resolution_returns_false_with_bootstrap_message(tmp_path: Path, capsys) -> None:
    """A pin with no [resolution] section returns False and prints a bootstrap-specific hint.

    Distinct from the generic stale-pin message so authors don't chase a rebase fix
    during the initial rollout when master simply has not published a resolution pin yet.
    """
    pin = tmp_path / 'pin.toml'
    pin.write_text(
        f'[{inputs_hash.SECTION_IMAGES}]\nlinux-x86_64 = "abc"\n',
        encoding='utf-8',
    )
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        assert inputs_hash.verify_resolution() is False
    _, err = capsys.readouterr()
    assert 'has not yet published a pin' in err


# ---------------------------------------------------------------------------
# Bot-commit neutrality
# ---------------------------------------------------------------------------

def test_hashing_a_specific_file_ignores_unrelated_siblings(tmp_path: Path) -> None:
    """Hashing `agent_requirements.in` is unaffected by sibling files outside the pattern.

    Sanity check that hash_paths only sees files matched by the patterns it is
    given — siblings in the same tree (here, fake `.deps/` content shaped like
    what the bot commit writes) cannot smuggle their content into the hash. The
    real "no RESOLUTION_INPUTS pattern reaches .deps/" guarantee is enforced by
    test_resolution_inputs_do_not_glob_into_deps_directory.
    """
    def _build_tree(root: Path, bot_output_contents: str) -> None:
        deps = root / '.deps'
        resolved = deps / 'resolved'
        resolved.mkdir(parents=True)
        (resolved / 'linux-x86_64_3.13.txt').write_text(bot_output_contents, encoding='utf-8')
        (deps / 'builder_inputs.toml').write_text(
            f'[resolution]\nhash = "{bot_output_contents}"\n', encoding='utf-8',
        )
        (root / 'agent_requirements.in').write_text('requests==2.31.0\n', encoding='utf-8')

    tree_a = tmp_path / 'a'
    tree_b = tmp_path / 'b'
    _build_tree(tree_a, 'before')
    _build_tree(tree_b, 'after')

    patterns = ['agent_requirements.in']
    assert inputs_hash.hash_paths(tree_a, patterns) == inputs_hash.hash_paths(tree_b, patterns)


def test_resolution_inputs_do_not_glob_into_deps_directory() -> None:
    """No RESOLUTION_INPUTS or SHARED_INPUTS pattern expands to anything under .deps/.

    Belt-and-braces companion to test_bot_commit_paths_do_not_affect_resolution_hash:
    rather than construct a fixture tree, assert that the live glob expansion
    cannot reach .deps/. Asserting on expanded matches (not pattern strings)
    catches future entries like `**/*.toml` that wouldn't start with `.deps/`
    but would still pull `.deps/builder_inputs.toml` into the hash.
    """
    deps_dir = REPO_ROOT / '.deps'
    matched: set[Path] = set()
    for pattern in inputs_hash.RESOLUTION_INPUTS:
        matched.update(REPO_ROOT.glob(pattern))
    for pattern in inputs_hash.SHARED_INPUTS:
        matched.update(HERE.glob(pattern))

    offenders = [p for p in matched if p == deps_dir or deps_dir in p.parents]
    assert not offenders, (
        f'Patterns that glob into .deps/ will cause the bot commit to re-trigger the '
        f'resolution workflow: {sorted(str(p) for p in offenders)}'
    )


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def test_status_fresh(tmp_path: Path) -> None:
    """All hashes match → needs_resolution=false, rebuild_<target>=false."""
    current_res = inputs_hash.compute_resolution()
    current_tgt = inputs_hash.compute_target('linux-x86_64')
    pin = _write_pin(tmp_path, current_res, {'linux-x86_64': current_tgt})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        out = inputs_hash.status(['linux-x86_64'])
    assert out['needs_resolution'] == 'false'
    assert out['rebuild_linux_x86_64'] == 'false'


def test_status_stale_resolution(tmp_path: Path) -> None:
    """Resolution drift alone sets needs_resolution=true but leaves rebuild_ per target intact."""
    current_tgt = inputs_hash.compute_target('linux-x86_64')
    pin = _write_pin(tmp_path, 'stale_hash', {'linux-x86_64': current_tgt})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        out = inputs_hash.status(['linux-x86_64'])
    assert out['needs_resolution'] == 'true'
    assert out['rebuild_linux_x86_64'] == 'false'


def test_status_stale_target(tmp_path: Path) -> None:
    """Target drift alone sets rebuild_<target>=true without forcing resolution."""
    current_res = inputs_hash.compute_resolution()
    pin = _write_pin(tmp_path, current_res, {'linux-x86_64': 'stale_image_hash'})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        out = inputs_hash.status(['linux-x86_64'])
    assert out['needs_resolution'] == 'false'
    assert out['rebuild_linux_x86_64'] == 'true'


def test_status_keys_use_underscores(tmp_path: Path) -> None:
    """rebuild_<target> output keys replace hyphens with underscores for GitHub Actions."""
    pin = _write_pin(tmp_path, 'x', {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        out = inputs_hash.status(['linux-x86_64', 'linux-aarch64', 'windows-x86_64'])
    assert 'rebuild_linux_x86_64' in out
    assert 'rebuild_linux_aarch64' in out
    assert 'rebuild_windows_x86_64' in out


def test_status_emits_hashes_json(tmp_path: Path) -> None:
    """status emits a `hashes` JSON blob mapping target → current hash for downstream jobs."""
    import json

    pin = _write_pin(tmp_path, 'x', {})
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        out = inputs_hash.status(['linux-x86_64'])
    hashes = json.loads(out['hashes'])
    assert set(hashes) == {'linux-x86_64'}
    assert hashes['linux-x86_64'] == inputs_hash.compute_target('linux-x86_64')


# ---------------------------------------------------------------------------
# Coverage: every tracked .builders/ file is classified
# ---------------------------------------------------------------------------

# Relative POSIX paths under .builders/ that intentionally don't affect any
# hash. Matched by full relative path (not basename) so a future file at e.g.
# .builders/images/linux-x86_64/promote.py is not silently exempted.
# Each entry needs a comment explaining why.
EXPECTED_UNCOVERED = {
    # Runs in the separate dependency-wheel-promotion.yaml workflow, not here.
    'promote.py',
    # mypy configuration only; does not affect build or resolution output.
    'pyproject.toml',
    # Test infrastructure; not baked into any image or artifact.
    'test_dependencies.txt',
}


def _is_ignored_for_coverage(path: Path, builders_dir: Path) -> bool:
    """Mirror the skip semantics that compute_target/compute_resolution apply when walking files."""
    rel = path.relative_to(builders_dir)
    return any(inputs_hash.is_ignored(part) for part in rel.parts)


def _glob_set(base: Path, patterns: list[str]) -> set[Path]:
    """Expand patterns the same way production does: skip ignored parts (dotfiles, __pycache__).

    Mirrors `_iter_files`/`hash_paths` semantics in inputs_hash.py: when a glob
    match expands into a directory, files under it are filtered if any part of
    the path *relative to the matched directory* is ignored. A direct file
    match is yielded unconditionally, just like production.
    """
    result: set[Path] = set()
    for pattern in patterns:
        for p in base.glob(pattern):
            if p.is_file():
                result.add(p)
            elif p.is_dir():
                for f in p.rglob('*'):
                    if not f.is_file():
                        continue
                    rel_parts = f.relative_to(p).parts
                    if any(inputs_hash.is_ignored(part) for part in rel_parts):
                        continue
                    result.add(f)
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
    resolution_files_in_builders = {p for p in resolution_files_abs if p.is_relative_to(builders_dir)}

    covered = shared_files | per_target_files | resolution_files_in_builders

    uncovered = []
    for path in builders_dir.rglob('*'):
        if not path.is_file():
            continue
        if _is_ignored_for_coverage(path, builders_dir):
            continue
        rel = path.relative_to(builders_dir).as_posix()
        if rel.startswith('tests/'):
            continue
        if rel.startswith('venv/'):
            continue
        if path in covered:
            continue
        if rel in EXPECTED_UNCOVERED:
            continue
        uncovered.append(rel)

    assert not uncovered, (
        f'These files under .builders/ are not covered by any hash input list or '
        f'EXPECTED_UNCOVERED:\n  ' + '\n  '.join(sorted(uncovered)) +
        '\nAdd each file to SHARED_INPUTS, RESOLUTION_INPUTS, or EXPECTED_UNCOVERED '
        'with a comment explaining why.'
    )
