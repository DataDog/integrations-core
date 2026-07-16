"""Tests for the release_push_tags entry-point script."""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import call, patch

import pytest

import release_push_tags

SCRIPT_PATH = Path(release_push_tags.__file__).resolve()


def _git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repositories(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--quiet", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "--quiet", str(source)], check=True)
    _git(source, "config", "user.name", "test")
    _git(source, "config", "user.email", "test@example.com")
    (source / "file").write_text("test\n")
    _git(source, "add", "file")
    _git(source, "commit", "--quiet", "-m", "initial")
    _git(source, "remote", "add", "origin", str(remote))
    _git(source, "push", "--quiet", "origin", "HEAD:refs/heads/master")
    return source, remote


def _create_tags(source: Path, tags: list[str]) -> None:
    for tag in tags:
        _git(source, "tag", "-a", tag, "-m", "release")


def _run_script(source: Path, tags: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["NEW_TAGS"] = json.dumps(tags)
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=source,
        env=env,
        capture_output=True,
        text=True,
    )


def _remote_tags(remote: Path) -> set[str]:
    result = _git(remote, "for-each-ref", "refs/tags", "--format=%(refname:short)")
    return set(result.stdout.splitlines())


def test_pushes_exact_tags_atomically(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEW_TAGS", '["postgres-1.0.0", "mysql-2.0.0"]')
    with patch("release_push_tags.subprocess.run") as mock_run:
        release_push_tags.main()

    assert mock_run.mock_calls == [
        call(
            [
                "git",
                "push",
                "--atomic",
                "origin",
                "refs/tags/postgres-1.0.0:refs/tags/postgres-1.0.0",
                "refs/tags/mysql-2.0.0:refs/tags/mysql-2.0.0",
            ],
            check=True,
        )
    ]


def test_empty_tags_exits_without_pushing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("NEW_TAGS", "[]")
    with patch("release_push_tags.subprocess.run") as mock_run, pytest.raises(SystemExit) as exc_info:
        release_push_tags.main()

    assert exc_info.value.code == 1
    assert "no release tags were provided" in capsys.readouterr().err
    mock_run.assert_not_called()


def test_push_failure_is_propagated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEW_TAGS", '["postgres-1.0.0"]')
    error = subprocess.CalledProcessError(1, ["git", "push"])

    with patch("release_push_tags.subprocess.run", side_effect=error), \
         pytest.raises(subprocess.CalledProcessError) as exc_info:
        release_push_tags.main()

    assert exc_info.value is error


def test_pushes_prepared_tags_after_shallow_fetch(tmp_path: Path) -> None:
    source, remote = _init_repositories(tmp_path)
    tags = ["dummy-1.0.0", "dummy-2.0.0"]
    _create_tags(source, tags)

    commit = _git(source, "rev-parse", "HEAD").stdout.strip()
    _git(
        source,
        "fetch",
        "--no-tags",
        "--prune",
        "--no-recurse-submodules",
        "--depth=1",
        "origin",
        commit,
    )
    _git(source, "checkout", "--quiet", "--force", commit)

    result = _run_script(source, tags)

    assert result.returncode == 0, result.stderr
    assert _remote_tags(remote) == set(tags)


def test_atomic_rejection_pushes_no_tags(tmp_path: Path) -> None:
    source, remote = _init_repositories(tmp_path)
    tags = ["accepted-1.0.0", "rejected-1.0.0"]
    _create_tags(source, tags)

    update_hook = remote / "hooks" / "update"
    update_hook.write_text(
        '#!/bin/sh\ncase "$1" in\n  refs/tags/rejected-*) exit 1 ;;\nesac\n'
    )
    update_hook.chmod(0o755)

    result = _run_script(source, tags)

    assert result.returncode != 0
    assert _remote_tags(remote) == set()
