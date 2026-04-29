"""Tests for inputs_hash.py: hashing, pinning, status, verify-resolution, and coverage."""
import json
from pathlib import Path
from unittest import mock

import pytest

import inputs_hash

HERE = Path(__file__).parent.parent  # .builders/
REPO_ROOT = HERE.parent


def _matrix_entry(out: dict[str, str], image: str) -> dict[str, str]:
    """Return the matrix row for `image` from whichever of matrix_container/matrix_macos contains it."""
    rows = json.loads(out['matrix_container']) + json.loads(out['matrix_macos'])
    matches = [r for r in rows if r['image'] == image]
    assert len(matches) == 1, f'expected exactly one row for {image}, got {matches}'
    return matches[0]


def test_status_raises_for_unknown_target(fake_repo: Path, tmp_path: Path) -> None:
    """An unknown target name is a usage error and must raise."""
    bogus = tmp_path / 'bogus_targets.json'
    bogus.write_text(
        json.dumps([{'platform': 'nonexistent', 'arch': 'target', 'runner_os': 'ubuntu-22.04'}]),
        encoding='utf-8',
    )
    with pytest.raises(FileNotFoundError, match='Unknown builder target'):
        inputs_hash.status(bogus)


# ---------------------------------------------------------------------------
# Bot-commit neutrality
# ---------------------------------------------------------------------------

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

def test_status_all_fresh(fake_repo_with_fresh_pin: dict, targets_file: Path) -> None:
    """A pin matching the working tree leaves every freshness flag false."""
    out = inputs_hash.status(targets_file)
    assert out['needs_resolution'] == 'false'
    assert _matrix_entry(out, 'linux-x86_64')['rebuild'] == 'false'


def test_status_stale_resolution_only(fake_repo_with_fresh_pin: dict, targets_file: Path) -> None:
    """Resolution drift alone sets needs_resolution=true but leaves the target's rebuild=false."""
    inputs_hash.write_pinned_hashes(
        inputs_hash.PINNED_FILE,
        inputs_hash.PinnedHashes(
            resolution='stale_resolution_hash',
            images=fake_repo_with_fresh_pin['target_hashes'],
        ),
    )
    out = inputs_hash.status(targets_file)
    assert out['needs_resolution'] == 'true'
    assert _matrix_entry(out, 'linux-x86_64')['rebuild'] == 'false'


def test_status_stale_target_only(fake_repo_with_fresh_pin: dict, targets_file: Path) -> None:
    """Target drift alone sets the target's rebuild=true and forces needs_resolution=true.

    A target rebuild can change which wheels link, so re-resolving on target
    drift is the safe conservative default.
    """
    inputs_hash.write_pinned_hashes(
        inputs_hash.PINNED_FILE,
        inputs_hash.PinnedHashes(
            resolution=fake_repo_with_fresh_pin['resolution_hash'],
            images={'linux-x86_64': 'stale_target_hash'},
        ),
    )
    out = inputs_hash.status(targets_file)
    assert out['needs_resolution'] == 'true'
    assert _matrix_entry(out, 'linux-x86_64')['rebuild'] == 'true'


@pytest.fixture
def targets_file(fake_repo: Path) -> Path:
    """Path to the linux-x86_64-only targets.json that fake_repo writes."""
    return fake_repo / '.builders' / 'targets.json'


@pytest.fixture
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimum repo tree satisfying SHARED_INPUTS and RESOLUTION_INPUTS for one target.

    Every pattern in the input lists has at least one matching file. Tests that
    need additional targets or extra files write them on top of the fixture.
    HERE/REPO_ROOT/PINNED_FILE are repointed at this tree so production hashing
    runs against deterministic content rather than the live repo.
    """
    files = {
        '.builders/build.py': b'build',
        '.builders/upload.py': b'upload',
        '.builders/inputs_hash.py': b'inputs_hash',
        '.builders/targets.json': b'[{"platform":"linux","arch":"x86_64","runner_os":"ubuntu-22.04"}]',
        '.builders/deps/build_dependencies.txt': b'build-deps',
        '.builders/scripts/build_wheels.py': b'build-wheels',
        '.builders/patches/some.patch': b'patch',
        '.builders/images/helpers.ps1': b'helpers',
        '.builders/images/install-from-source.sh': b'install',
        '.builders/images/runner_dependencies.txt': b'runner',
        '.builders/images/linux-x86_64/Dockerfile': b'linux-x86_64',
        'agent_requirements.in': b'requests==2.31.0',
        '.github/workflows/resolve-build-deps.yaml': b'workflow',
    }
    for rel, content in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    monkeypatch.setattr(inputs_hash, 'HERE', tmp_path / '.builders')
    monkeypatch.setattr(inputs_hash, 'REPO_ROOT', tmp_path)
    monkeypatch.setattr(inputs_hash, 'PINNED_FILE', tmp_path / '.deps' / 'builder_inputs.toml')
    return tmp_path


def _baseline(fake_repo: Path) -> dict[str, str]:
    """Write a placeholder pin and run status once; return the output."""
    inputs_hash.write_pinned_hashes(
        inputs_hash.PINNED_FILE,
        inputs_hash.PinnedHashes(resolution='placeholder'),
    )
    return inputs_hash.status(fake_repo / '.builders' / 'targets.json')


@pytest.fixture
def fake_repo_with_fresh_pin(fake_repo: Path) -> dict:
    """fake_repo plus a pin that matches the working tree (everything fresh).

    Tests mutate one side of the pin to introduce a single dimension of
    staleness without losing control of the others. Returned dict has the
    discovered `resolution_hash` and per-target `target_hashes` so the test
    can rewrite the pin while preserving whichever side it doesn't want to
    flip.
    """
    discovered = _baseline(fake_repo)
    rows = json.loads(discovered['matrix_container']) + json.loads(discovered['matrix_macos'])
    target_hashes = {row['image']: row['hash'] for row in rows}
    inputs_hash.write_pinned_hashes(
        inputs_hash.PINNED_FILE,
        inputs_hash.PinnedHashes(
            resolution=discovered['resolution_hash'],
            images=target_hashes,
        ),
    )
    return {
        'resolution_hash': discovered['resolution_hash'],
        'target_hashes': target_hashes,
    }


@pytest.mark.parametrize('rel_path', [
    # _is_ignored: dotfiles and __pycache__ inside tracked subtrees.
    pytest.param('.builders/scripts/__pycache__/x.pyc', id='pycache-in-scripts'),
    pytest.param('.builders/scripts/.hidden', id='dotfile-in-scripts'),
    pytest.param('.builders/images/linux-x86_64/.DS_Store', id='dotfile-in-target'),
    pytest.param('.builders/images/linux-x86_64/__pycache__/y.pyc', id='pycache-in-target'),
    # IGNORED_DIRS: subtree exemptions.
    pytest.param('.builders/tests/test_something.py', id='ignored-dir-tests'),
    pytest.param('.builders/venv/lib/x.py', id='ignored-dir-venv'),
    # IGNORED_FILES: specific-file exemptions.
    pytest.param('.builders/promote.py', id='ignored-file-promote'),
    pytest.param('.builders/pyproject.toml', id='ignored-file-pyproject'),
    pytest.param('.builders/test_dependencies.txt', id='ignored-file-test-deps'),
])
def test_adding_ignored_file_does_not_change_status(fake_repo: Path, targets_file: Path, rel_path: str) -> None:
    """Ignored files don't enter any hash and don't error.

    Three flavors are exercised: _is_ignored (dotfiles/__pycache__),
    IGNORED_DIRS (subtree exemptions), and IGNORED_FILES (specific files).
    """
    before = _baseline(fake_repo)
    path = fake_repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'irrelevant')
    after = inputs_hash.status(targets_file)
    assert after == before


@pytest.mark.parametrize('rel_path,expect_resolution_change,expect_target_change', [
    # SHARED_INPUTS pattern + RESOLUTION_INPUTS .builders/scripts/**/*: both flip.
    ('.builders/scripts/new_script.py', True, True),
    # SHARED_INPUTS patches/**/* + RESOLUTION_INPUTS .builders/patches/**/*: both flip.
    ('.builders/patches/new.patch', True, True),
    # Per-target glob + RESOLUTION_INPUTS .builders/images/**/*: both flip.
    ('.builders/images/linux-x86_64/extra.sh', True, True),
    # RESOLUTION_INPUTS .builders/images/**/* only; not in SHARED_INPUTS or per-target.
    ('.builders/images/new_top_level.txt', True, False),
])
def test_adding_tracked_file_changes_status(
    fake_repo: Path, targets_file: Path, rel_path: str, expect_resolution_change: bool, expect_target_change: bool
) -> None:
    """A new file matched by an input pattern flips the relevant hash(es)."""
    before = _baseline(fake_repo)
    path = fake_repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'new content')
    after = inputs_hash.status(targets_file)
    before_hash = _matrix_entry(before, 'linux-x86_64')['hash']
    after_hash = _matrix_entry(after, 'linux-x86_64')['hash']
    assert (after['resolution_hash'] != before['resolution_hash']) is expect_resolution_change
    assert (after_hash != before_hash) is expect_target_change


@pytest.mark.parametrize('rel_path,expect_resolution_change,expect_target_change', [
    # SHARED_INPUTS build.py + RESOLUTION_INPUTS .builders/build.py: both flip.
    ('.builders/build.py', True, True),
    # SHARED_INPUTS scripts/**/* + RESOLUTION_INPUTS .builders/scripts/**/*: both flip.
    ('.builders/scripts/build_wheels.py', True, True),
    # SHARED_INPUTS deps/build_dependencies.txt + RESOLUTION_INPUTS deps/*.txt: both flip.
    ('.builders/deps/build_dependencies.txt', True, True),
    # RESOLUTION_INPUTS only; not in SHARED_INPUTS or per-target.
    ('agent_requirements.in', True, False),
    # Per-target glob + RESOLUTION_INPUTS .builders/images/**/*: both flip.
    ('.builders/images/linux-x86_64/Dockerfile', True, True),
])
def test_modifying_tracked_file_changes_status(
    fake_repo: Path, targets_file: Path, rel_path: str, expect_resolution_change: bool, expect_target_change: bool
) -> None:
    """Modifying a tracked file's bytes flips the relevant hash(es)."""
    before = _baseline(fake_repo)
    (fake_repo / rel_path).write_bytes(b'modified content')
    after = inputs_hash.status(targets_file)
    before_hash = _matrix_entry(before, 'linux-x86_64')['hash']
    after_hash = _matrix_entry(after, 'linux-x86_64')['hash']
    assert (after['resolution_hash'] != before['resolution_hash']) is expect_resolution_change
    assert (after_hash != before_hash) is expect_target_change


def test_status_raises_when_a_pattern_matches_no_files(fake_repo: Path, targets_file: Path) -> None:
    """If a tracked file disappears so an input pattern matches nothing, status fails loudly.

    This is the drift detector for stale entries in SHARED_INPUTS / RESOLUTION_INPUTS.
    """
    (fake_repo / '.builders' / 'build.py').unlink()
    with pytest.raises(RuntimeError, match='matched no files'):
        inputs_hash.status(targets_file)


def test_status_raises_when_pattern_only_matches_ignored_files(fake_repo: Path, targets_file: Path) -> None:
    """If a tracked directory exists but every file in it is ignored, status fails loudly.

    Without this guard, the hash would silently narrow to sha256(empty) when
    every match is a dotfile or under __pycache__/.
    """
    scripts = fake_repo / '.builders' / 'scripts'
    for f in scripts.iterdir():
        f.unlink()
    (scripts / '__pycache__').mkdir()
    (scripts / '__pycache__' / 'x.pyc').write_bytes(b'x')
    with pytest.raises(RuntimeError, match='no hashable files'):
        inputs_hash.status(targets_file)


@pytest.mark.parametrize('rel_path', [
    pytest.param('.builders/some_new_top_level.py', id='top-level-py'),
    pytest.param('.builders/deps/something_else.json', id='wrong-extension-in-deps'),
    pytest.param('.builders/new_directory/file.txt', id='new-subtree'),
])
def test_status_raises_on_uncovered_file(fake_repo: Path, targets_file: Path, rel_path: str) -> None:
    """A file under .builders/ matched by no pattern and not ignored fails the gate.

    Without this guard, the gate would publish a hash that excludes a real
    input — the silent-coverage-hole failure mode the test_no_uncovered_files
    drift detector exists to prevent.
    """
    path = fake_repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'uncovered')
    with pytest.raises(RuntimeError, match='uncovered'):
        inputs_hash.status(targets_file)


def test_status_raises_on_malformed_pin(fake_repo: Path, targets_file: Path) -> None:
    """A corrupt pin file raises rather than silently acting unpinned."""
    inputs_hash.PINNED_FILE.parent.mkdir(parents=True, exist_ok=True)
    inputs_hash.PINNED_FILE.write_text('not valid [[toml', encoding='utf-8')
    with pytest.raises(RuntimeError, match='malformed'):
        inputs_hash.status(targets_file)


def test_status_no_pin_for_target_means_rebuild(fake_repo: Path, targets_file: Path, capsys) -> None:
    """When the pin has no entry for a target, status sets that target's rebuild=true.

    Covers the three "no target hash" cases collectively (no pin file, no
    [images] section, target absent from section) — they all resolve to the
    same observable behavior.
    """
    inputs_hash.write_pinned_hashes(
        inputs_hash.PINNED_FILE,
        inputs_hash.PinnedHashes(resolution='placeholder'),
    )
    out = inputs_hash.status(targets_file)
    assert _matrix_entry(out, 'linux-x86_64')['rebuild'] == 'true'
    assert 'no entry for linux-x86_64' in capsys.readouterr().err


def test_status_no_resolution_pin_emits_bootstrap_message(fake_repo: Path, targets_file: Path, capsys) -> None:
    """When the pin has no [resolution] section, status emits the bootstrap hint.

    Distinct from the generic stale-pin message so authors don't chase a
    rebase fix during the initial rollout when master simply has not
    published a resolution pin yet.
    """
    inputs_hash.write_pinned_hashes(
        inputs_hash.PINNED_FILE,
        inputs_hash.PinnedHashes(images={'linux-x86_64': 'abc'}),
    )
    out = inputs_hash.status(targets_file)
    assert out['needs_resolution'] == 'true'
    assert 'has not yet published a pin' in capsys.readouterr().err


def test_status_emits_matrix_split_by_platform(tmp_path: Path) -> None:
    """status emits matrix_container and matrix_macos JSON lists, each with image/platform/arch/runner_os/hash/rebuild."""
    pin = tmp_path / 'builder_inputs.toml'
    inputs_hash.write_pinned_hashes(pin, inputs_hash.PinnedHashes(resolution='x'))
    targets_file = tmp_path / 'targets.json'
    targets_file.write_text(json.dumps([
        {'platform': 'linux',   'arch': 'x86_64',  'runner_os': 'ubuntu-22.04'},
        {'platform': 'linux',   'arch': 'aarch64', 'runner_os': 'ubuntu-22.04-arm'},
        {'platform': 'windows', 'arch': 'x86_64',  'runner_os': 'windows-2022'},
        {'platform': 'macos',   'arch': 'x86_64',  'runner_os': 'macos-14-large'},
        {'platform': 'macos',   'arch': 'aarch64', 'runner_os': 'macos-14'},
    ]), encoding='utf-8')
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        out = inputs_hash.status(targets_file)
    container = json.loads(out['matrix_container'])
    macos = json.loads(out['matrix_macos'])
    assert {r['image'] for r in container} == {'linux-x86_64', 'linux-aarch64', 'windows-x86_64'}
    assert {r['image'] for r in macos} == {'macos-x86_64', 'macos-aarch64'}
    for row in container + macos:
        assert set(row) == {'image', 'platform', 'arch', 'runner_os', 'hash', 'rebuild'}


# ---------------------------------------------------------------------------
# main() end-to-end: stdout format and exit codes consumed by GitHub Actions
# ---------------------------------------------------------------------------

def test_main_status_emits_key_equals_value_lines(
    fake_repo_with_fresh_pin: dict, targets_file: Path, monkeypatch, capsys
) -> None:
    """`status` writes `key=value\\n` lines to stdout — the format $GITHUB_OUTPUT consumes.

    A regression that switched to JSON or a different separator would silently
    break the workflow's `if: needs.gate.outputs.needs_resolution == 'true'`
    expression, which has no test coverage outside this assertion.
    """
    monkeypatch.setattr('sys.argv', ['inputs_hash.py', 'status', str(targets_file)])
    inputs_hash.main()
    stdout = capsys.readouterr().out
    lines = stdout.splitlines()
    keys = {line.split('=', 1)[0] for line in lines if '=' in line}
    assert {'needs_resolution', 'matrix_container', 'matrix_macos', 'resolution_hash'} <= keys
    for line in lines:
        assert '=' in line, f'stdout line missing key=value separator: {line!r}'


def test_main_verify_resolution_fresh_exits_zero(
    fake_repo_with_fresh_pin: dict, monkeypatch
) -> None:
    """`verify-resolution` against a matching pin exits 0."""
    monkeypatch.setattr('sys.argv', ['inputs_hash.py', 'verify-resolution'])
    inputs_hash.main()


def test_main_verify_resolution_stale_exits_one_with_rebase_advice(
    fake_repo: Path, monkeypatch, capsys
) -> None:
    """`verify-resolution` against a stale pin exits 1 and prints rebase guidance.

    Exit 1 is what verify-deps-pin.yaml relies on to fail the merge queue; the
    rebase line is the actionable hint shown to the author whose pin is stale.
    """
    inputs_hash.write_pinned_hashes(
        inputs_hash.PINNED_FILE,
        inputs_hash.PinnedHashes(resolution='stale_resolution_hash'),
    )
    monkeypatch.setattr('sys.argv', ['inputs_hash.py', 'verify-resolution'])
    with pytest.raises(SystemExit) as excinfo:
        inputs_hash.main()
    assert excinfo.value.code == 1
    assert 'Rebase your branch' in capsys.readouterr().err


def test_main_verify_resolution_unpinned_exits_one_without_rebase_advice(
    fake_repo: Path, monkeypatch, capsys
) -> None:
    """`verify-resolution` on a tree with no [resolution] pin exits 1 but suppresses rebase advice.

    Bootstrap state: master has not yet published a pin. Telling the author to
    rebase would be wrong — there is nothing on master to rebase onto. Per B3,
    rebase advice is gated to the 'stale' branch only.
    """
    inputs_hash.write_pinned_hashes(
        inputs_hash.PINNED_FILE,
        inputs_hash.PinnedHashes(images={'linux-x86_64': 'abc'}),
    )
    monkeypatch.setattr('sys.argv', ['inputs_hash.py', 'verify-resolution'])
    with pytest.raises(SystemExit) as excinfo:
        inputs_hash.main()
    assert excinfo.value.code == 1
    assert 'Rebase your branch' not in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Coverage: every tracked .builders/ file is classified
# ---------------------------------------------------------------------------

def test_no_uncovered_files(tmp_path: Path) -> None:
    """Every file under .builders/ is classified.

    Adding a new file under .builders/ fails CI until a human adds it to
    SHARED_INPUTS, a per-target images/<target>/ directory, RESOLUTION_INPUTS,
    or IGNORED_DIRS / IGNORED_FILES (with a comment explaining why).

    Runs against the live repo by design — this is the drift detector.
    status() raises if anything is uncovered; succeeding (no exception) is
    the assertion.
    """
    pin = tmp_path / 'builder_inputs.toml'
    inputs_hash.write_pinned_hashes(pin, inputs_hash.PinnedHashes(resolution='placeholder'))
    with mock.patch.object(inputs_hash, 'PINNED_FILE', pin):
        inputs_hash.status(HERE / 'targets.json')
