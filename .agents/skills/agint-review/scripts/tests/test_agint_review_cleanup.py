import importlib.util
import os
import time
import shutil
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
CLEANUP_PATH = SCRIPTS_DIR / "agint-review-cleanup"
SETUP_PATH = SCRIPTS_DIR / "agint-review-setup"

# Every text file in a round survives cleanup; only the worktrees go.
TEXT_FILES = (
    "review.json",
    "context.json",
    "scout-context.md",
    "findings",
    "diffs",
    "challenger.md",
    "diff.full",
    "callers",
)


def load(name, path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def setup_script():
    return load("agint_review_setup", SETUP_PATH)


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "file.txt").write_text("hello\n")
    git(repo, "add", "file.txt")
    git(repo, "commit", "-q", "-m", "init")
    return repo


def make_round(repo, pr, n):
    """Create a round dir with real head/base worktrees and every artifact."""
    round_dir = repo / ".agint-review" / str(pr) / f"round-{n}"
    round_dir.mkdir(parents=True)
    for name in ("head", "base"):
        git(repo, "worktree", "add", "-q", "--detach", str(round_dir / name), "HEAD")
    for name in ("findings", "diffs"):
        (round_dir / name).mkdir()
        (round_dir / name / "x.md").write_text("x")
    for name in TEXT_FILES:
        if not (round_dir / name).exists():
            (round_dir / name).write_text("x")
    return round_dir


def registered_worktrees(repo):
    return [
        Path(line.split(" ", 1)[1]).resolve()
        for line in git(repo, "worktree", "list", "--porcelain").splitlines()
        if line.startswith("worktree ")
    ]


def run_cleanup(path, *extra):
    return subprocess.run(
        [sys.executable, str(CLEANUP_PATH), str(path), *extra], capture_output=True, text=True
    )


def test_cleanup_removes_worktrees_and_keeps_every_text_file(repo):
    round_dir = make_round(repo, 1234, 1)
    (round_dir / "head" / "dirty.txt").write_text("untracked change")

    res = run_cleanup(round_dir)

    assert res.returncode == 0, res.stderr
    assert not (round_dir / "head").exists()
    assert not (round_dir / "base").exists()
    assert registered_worktrees(repo) == [repo.resolve()]
    for name in TEXT_FILES:
        assert (round_dir / name).exists(), name


def test_cleanup_is_idempotent(repo):
    round_dir = make_round(repo, 1234, 1)

    assert run_cleanup(round_dir).returncode == 0
    second = run_cleanup(round_dir)

    assert second.returncode == 0, second.stderr
    assert (round_dir / "review.json").exists()


def test_cleanup_of_a_round_without_worktrees_or_a_missing_dir_succeeds(repo):
    round_dir = repo / ".agint-review" / "1234" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "review.json").write_text("{}")

    assert run_cleanup(round_dir).returncode == 0
    assert run_cleanup(round_dir.parent / "round-9").returncode == 0
    assert (round_dir / "review.json").exists()


def test_cleanup_deletes_worktree_dir_that_git_no_longer_knows(repo):
    round_dir = make_round(repo, 1234, 1)
    stray = round_dir / "head"
    git(repo, "worktree", "remove", "--force", str(stray))
    stray.mkdir()
    (stray / "leftover.txt").write_text("x")

    assert run_cleanup(round_dir).returncode == 0
    assert not stray.exists()


@pytest.mark.parametrize("relative", ["", ".agint-review", "other/1234/round-1"])
def test_cleanup_refuses_paths_outside_the_review_dir(repo, relative):
    target = repo / relative
    target.mkdir(parents=True, exist_ok=True)
    (target / "diff.full").write_text("keep me")

    res = run_cleanup(target)

    assert res.returncode == 2
    assert "refusing" in res.stderr
    assert (target / "diff.full").exists()


def test_cleanup_refuses_dotdot_escape(repo):
    (repo / ".agint-review" / "1234").mkdir(parents=True)
    (repo / "diff.full").write_text("keep me")

    res = run_cleanup(repo / ".agint-review" / "1234" / ".." / "..")

    assert res.returncode == 2
    assert (repo / "diff.full").exists()


def test_cleanup_honours_a_custom_review_dir_base(repo):
    round_dir = repo / "custom-reviews" / "1234" / "round-1"
    round_dir.mkdir(parents=True)
    (round_dir / "diff.full").write_text("x")

    assert run_cleanup(round_dir).returncode == 2
    assert run_cleanup(round_dir, "--review-dir-base", "custom-reviews").returncode == 0
    assert (round_dir / "diff.full").exists()


# --- agint-review-setup: round selection and pruning ------------------------


@pytest.mark.parametrize(
    ("dirs", "explicit", "reuse_latest", "expected"),
    [
        ([], None, False, 1),
        (["round-1", "round-2"], None, False, 3),
        (["round-1", "round-10", "round-2", "notes", "round-x"], None, False, 11),
        (["round-1", "round-2"], 1, False, 1),
        (["round-1", "round-2"], None, True, 2),
        ([], None, True, 1),
        (["round-1", "round-2"], 1, True, 1),
    ],
)
def test_resolve_round(setup_script, tmp_path, dirs, explicit, reuse_latest, expected):
    for name in dirs:
        (tmp_path / name).mkdir()

    assert setup_script.resolve_round(tmp_path, explicit, reuse_latest) == expected


def test_cleanup_older_rounds_only_touches_older_rounds_of_the_same_pr(setup_script, repo):
    old = make_round(repo, 1234, 1)
    current = make_round(repo, 1234, 2)
    other_pr = make_round(repo, 5678, 1)

    setup_script.cleanup_older_rounds(repo / ".agint-review" / "1234", 2, ".agint-review")

    assert not (old / "head").exists()
    assert (old / "diff.full").exists()
    assert (old / "review.json").exists()
    for kept in (current, other_pr):
        assert (kept / "head").exists()
        assert (kept / "base").exists()
        assert (kept / "diff.full").exists()


def test_prune_worktrees_drops_stale_entries(setup_script, repo, monkeypatch):
    round_dir = make_round(repo, 1234, 1)
    shutil.rmtree(round_dir / "head")
    monkeypatch.chdir(repo)

    setup_script.prune_worktrees()

    assert (round_dir / "head").resolve() not in registered_worktrees(repo)
    assert (round_dir / "base").resolve() in registered_worktrees(repo)


# --- agint-review-setup: sweeping other PRs' folders ------------------------

CURRENT_PR = 1000


def age(round_dir, hours):
    """Backdate a round dir so the sweep treats its worktrees as leftovers."""
    t = time.time() - hours * 3600
    os.utime(round_dir, (t, t))


def sweep(setup_script, repo, states):
    return setup_script.sweep_review_base(
        repo / ".agint-review", CURRENT_PR, lambda n: states.get(n)
    )


@pytest.mark.parametrize("state", ["MERGED", "CLOSED"])
def test_sweep_deletes_merged_or_closed_pr_folders(setup_script, repo, state):
    gone = make_round(repo, 2001, 1)

    deleted, worktrees = sweep(setup_script, repo, {2001: state})

    assert (deleted, worktrees) == (1, 2)
    assert not gone.parent.exists()
    assert registered_worktrees(repo) == [repo.resolve()]


def test_sweep_keeps_open_pr_folders_and_removes_only_old_worktrees(setup_script, repo):
    old = make_round(repo, 2002, 1)
    recent = make_round(repo, 2002, 2)
    age(old, 7)

    deleted, worktrees = sweep(setup_script, repo, {2002: "OPEN"})

    assert (deleted, worktrees) == (0, 2)
    assert not (old / "head").exists() and not (old / "base").exists()
    assert (old / "review.json").exists() and (old / "findings").exists()
    assert (recent / "head").exists() and (recent / "base").exists()


def test_sweep_keeps_the_folder_when_the_state_lookup_fails(setup_script, repo):
    unknown = make_round(repo, 2003, 1)
    age(unknown, 48)

    assert sweep(setup_script, repo, {2003: None}) == (0, 0)
    assert (unknown / "head").exists() and (unknown / "review.json").exists()


def test_sweep_never_touches_the_current_pr(setup_script, repo):
    current = make_round(repo, CURRENT_PR, 1)
    age(current, 48)

    assert sweep(setup_script, repo, {CURRENT_PR: "MERGED"}) == (0, 0)
    assert (current / "head").exists() and (current / "review.json").exists()


def test_sweep_refuses_a_pr_folder_that_points_outside_the_review_dir(setup_script, repo, tmp_path):
    outside = tmp_path / "outside"
    (outside / "round-1").mkdir(parents=True)
    (outside / "round-1" / "review.json").write_text("keep me")
    (repo / ".agint-review").mkdir(exist_ok=True)
    (repo / ".agint-review" / "2004").symlink_to(outside, target_is_directory=True)

    assert sweep(setup_script, repo, {2004: "MERGED"}) == (0, 0)
    assert (outside / "round-1" / "review.json").exists()


@pytest.mark.parametrize("relative", ["", ".agint-review", "elsewhere", ".agint-review/../elsewhere"])
def test_safe_rmtree_refuses_paths_outside_the_review_dir(setup_script, repo, relative):
    (repo / ".agint-review").mkdir(exist_ok=True)
    (repo / "elsewhere").mkdir(exist_ok=True)
    target = repo / relative

    assert setup_script.safe_rmtree(target, repo / ".agint-review") is False
    assert target.exists()


def test_sweep_ignores_non_pr_folders(setup_script, repo):
    notes = repo / ".agint-review" / "notes"
    notes.mkdir(parents=True)

    assert sweep(setup_script, repo, {}) == (0, 0)
    assert notes.exists()


def test_lookup_pr_state_returns_none_when_gh_fails(setup_script, monkeypatch):
    monkeypatch.setattr(
        setup_script.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, stdout="", stderr="HTTP 404"),
    )

    assert setup_script.lookup_pr_state("DataDog/integrations-core", 1) is None
