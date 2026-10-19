"""Tests for the release_push_tags entry-point script."""
import subprocess
from unittest.mock import call, patch

import pytest

import release_push_tags


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
