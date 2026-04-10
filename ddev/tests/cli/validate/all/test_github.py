# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.cli.validate.all.github import (
    format_pr_comment,
    get_pr_number,
    get_workflow_run_url,
    parse_pr_number_from_event,
    parse_pr_number_from_ref,
    write_step_summary,
)
from ddev.cli.validate.all.orchestrator import ValidationResult

# --- parse_pr_number_from_event ---


@pytest.mark.parametrize(
    "content, expected",
    [
        pytest.param('{"pull_request": {"number": 42}}', 42, id="happy-path"),
        pytest.param("{bad json}", None, id="malformed-json"),
        pytest.param("{}", None, id="missing-pr-key"),
        pytest.param('{"pull_request": "bad"}', None, id="pr-not-dict"),
        pytest.param('{"pull_request": {}}', None, id="missing-number"),
        pytest.param('{"pull_request": {"number": "x"}}', None, id="number-not-int"),
    ],
)
def test_parse_pr_number_from_event(tmp_path, content, expected):
    event_file = tmp_path / "event.json"
    event_file.write_text(content)
    assert parse_pr_number_from_event(str(event_file)) == expected


def test_parse_pr_number_from_event_file_not_found():
    assert parse_pr_number_from_event("/nonexistent/event.json") is None


# --- parse_pr_number_from_ref ---


@pytest.mark.parametrize(
    "ref, expected",
    [
        pytest.param("refs/pull/99/merge", 99, id="valid-ref"),
        pytest.param("refs/heads/main", None, id="branch-ref"),
        pytest.param("refs/pull/notanumber/merge", None, id="non-numeric-ref"),
        pytest.param("refs/pull//merge", None, id="empty-number"),
        pytest.param("", None, id="empty-string"),
    ],
)
def test_parse_pr_number_from_ref(ref, expected):
    assert parse_pr_number_from_ref(ref) == expected


# --- get_pr_number ---


@pytest.mark.parametrize(
    "event_name",
    [
        pytest.param("push", id="push-event"),
        pytest.param("merge_group", id="merge-group-event"),
    ],
)
def test_get_pr_number_non_pr_events(mock_app, monkeypatch, event_name):
    monkeypatch.setenv("GITHUB_EVENT_NAME", event_name)

    assert get_pr_number(mock_app) is None
    mock_app.display_warning.assert_not_called()


def test_get_pr_number_no_event_name(mock_app):
    assert get_pr_number(mock_app) is None
    mock_app.display_warning.assert_not_called()


def test_get_pr_number_from_event_file(mock_app, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    event_file = tmp_path / "event.json"
    event_file.write_text('{"pull_request": {"number": 42}}')
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))

    assert get_pr_number(mock_app) == 42


def test_get_pr_number_from_ref_fallback(mock_app, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_REF", "refs/pull/99/merge")

    assert get_pr_number(mock_app) == 99


def test_get_pr_number_warns_on_event_file_failure(mock_app, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(tmp_path / "missing.json"))

    assert get_pr_number(mock_app) is None
    mock_app.display_warning.assert_called()


def test_get_pr_number_warns_when_no_source_available(mock_app, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")

    assert get_pr_number(mock_app) is None
    mock_app.display_warning.assert_called()


# --- format_pr_comment ---


def test_format_pr_comment_all_passed():
    results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
        "ci": ValidationResult(name="ci", success=True, stdout="ok", stderr="", duration=2.0),
    }
    expected = "## Validation Report\n\nAll **2** validations passed."
    assert format_pr_comment(results, target="changed") == expected


def test_format_pr_comment_one_failure_with_target(helpers):
    results = {
        "config": ValidationResult(name="config", success=False, stdout="error output", stderr="", duration=1.0),
        "ci": ValidationResult(name="ci", success=True, stdout="ok", stderr="", duration=2.0),
    }
    expected = helpers.dedent("""
        ## Validation Report

        **1 validation(s) failed** — 1 passed.

        <details>
        <summary><code>config</code></summary>

        ```
        error output
        ```

        **Fix locally:**
        ```shell
        ddev validate config changed
        ```
        </details>

        <details>
        <summary>Passed (1)</summary>

        - `ci`
        </details>

        Run `ddev validate all changed --fix` to attempt to auto-fix supported validations.""")
    assert format_pr_comment(results, target="changed") == expected


def test_format_pr_comment_stderr_fallback():
    results = {
        "config": ValidationResult(name="config", success=False, stdout="", stderr="stderr output", duration=1.0),
    }
    comment = format_pr_comment(results, target=None)
    assert "stderr output" in comment


def test_format_pr_comment_long_output_trimmed():
    long_output = "\n".join(f"line {i}" for i in range(200))
    results = {
        "config": ValidationResult(name="config", success=False, stdout=long_output, stderr="", duration=1.0),
    }
    comment = format_pr_comment(results, target=None)
    assert "trimmed to last 100 lines" in comment
    assert "line 199" in comment
    assert "line 0" not in comment


def test_format_pr_comment_failure_without_output():
    results = {
        "config": ValidationResult(name="config", success=False, stdout="", stderr="", duration=1.0),
    }
    comment = format_pr_comment(results, target=None)
    assert "<code>config</code>" in comment
    assert "```\n\n```" not in comment


def test_format_pr_comment_no_target():
    results = {
        "config": ValidationResult(name="config", success=False, stdout="fail", stderr="", duration=1.0),
    }
    comment = format_pr_comment(results, target=None)
    assert "ddev validate config\n" in comment


def test_format_pr_comment_with_error_and_warning(helpers):
    results = {
        "config": ValidationResult(name="config", success=False, stdout="bad", stderr="", duration=1.0),
    }
    expected = helpers.dedent("""
        ## Validation Report

        > **Error:** Error running validations: boom

        > **Warning:** Could not determine PR number

        **1 validation(s) failed** — 0 passed.

        <details>
        <summary><code>config</code></summary>

        ```
        bad
        ```

        **Fix locally:**
        ```shell
        ddev validate config
        ```
        </details>

        Run `ddev validate all --fix` to attempt to auto-fix supported validations.""")
    assert (
        format_pr_comment(
            results, target=None, error="Error running validations: boom", warning="Could not determine PR number"
        )
        == expected
    )


# --- get_workflow_run_url ---


def test_get_workflow_run_url_returns_url():
    assert get_workflow_run_url() == "https://github.com/DataDog/integrations-core/actions/runs/12345"


def test_get_workflow_run_url_returns_none_when_env_missing(monkeypatch):
    monkeypatch.delenv("GITHUB_RUN_ID")
    assert get_workflow_run_url() is None


# --- write_step_summary ---


def test_write_step_summary_writes_to_file(tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_step_summary("## Report\nAll good")
    assert summary_file.read_text() == "## Report\nAll good\n"


def test_write_step_summary_appends(tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    summary_file.write_text("existing\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_step_summary("new content")
    assert "existing\n" in summary_file.read_text()
    assert "new content\n" in summary_file.read_text()


def test_write_step_summary_noop_without_env(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    write_step_summary("should not error")
