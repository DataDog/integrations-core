# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.utils.github_actions import get_workflow_run_url, write_step_summary


@pytest.fixture(autouse=True)
def _github_actions_env(monkeypatch):
    """A consistent GitHub Actions environment, so a real one cannot leak into these tests."""
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "DataDog/integrations-core")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")


# --- get_workflow_run_url ---


def test_get_workflow_run_url_returns_url():
    assert get_workflow_run_url() == "https://github.com/DataDog/integrations-core/actions/runs/12345"


@pytest.mark.parametrize("missing", ["GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"])
def test_get_workflow_run_url_returns_none_when_env_missing(monkeypatch, missing):
    monkeypatch.delenv(missing)
    assert get_workflow_run_url() is None


# --- write_step_summary ---


def test_write_step_summary_writes_to_file(tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_step_summary("## Report\nAll good")
    assert summary_file.read_text(encoding="utf-8") == "## Report\nAll good\n"


def test_write_step_summary_appends(tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    summary_file.write_text("existing\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_step_summary("new content")
    assert "existing\n" in summary_file.read_text(encoding="utf-8")
    assert "new content\n" in summary_file.read_text(encoding="utf-8")


def test_write_step_summary_noop_without_env(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    write_step_summary("should not error")


def test_write_step_summary_survives_an_unwritable_summary_file(tmp_path, monkeypatch):
    """Reporting is never the reason a command fails, so an unusable summary path is swallowed."""
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "missing-dir" / "summary.md"))
    write_step_summary("should not error")


def test_the_step_summary_is_written_as_utf8_whatever_the_locale(tmp_path, monkeypatch):
    """The Dispatcher report is emoji-dense, so the encoding is part of the contract.

    Asserted in bytes, because reading it back as text would use the locale encoding and agree with
    whatever was written. Only fails where it matters — Windows CI, or ``LC_ALL=C PYTHONUTF8=0``.
    """
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_step_summary("## ✅ passed · ❌ failed")

    # The trailing newline is excluded deliberately: text mode translates it to CRLF on Windows.
    assert summary_file.read_bytes().startswith("## ✅ passed · ❌ failed".encode())
