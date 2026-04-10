# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ddev.cli.validate.all.github import (
    format_pr_comment,
    get_pr_number,
    get_workflow_run_url,
    parse_pr_number_from_event,
    parse_pr_number_from_ref,
    write_step_summary,
)
from ddev.cli.validate.all.orchestrator import (
    VALIDATIONS,
    ValidationMessage,
    ValidationOrchestrator,
    ValidationProcessor,
    ValidationResult,
)
from ddev.event_bus.orchestrator import BaseMessage

ALL_NAMES = list(VALIDATIONS)
REPO_WIDE_NAMES = {name for name, cfg in VALIDATIONS.items() if cfg.repo_wide}


@pytest.fixture(autouse=True)
def _clean_github_env(monkeypatch):
    """Provide a consistent GitHub Actions environment for all tests."""
    for key in ("GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH", "GITHUB_REF", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "DataDog/integrations-core")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")


def _completed_process(returncode=0, stdout="", stderr=""):
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


@pytest.fixture
def mock_app():
    """Mock Application that records display calls and raises SystemExit on abort."""
    app = MagicMock()
    app.abort.side_effect = SystemExit(1)
    return app


# --- ValidationProcessor ---


@pytest.mark.parametrize(
    "returncode, stdout, stderr, expected_success",
    [
        pytest.param(0, "all good", "", True, id="success"),
        pytest.param(1, "", "error details", False, id="failure"),
    ],
)
def test_processor_captures_result(mock_app, returncode, stdout, stderr, expected_success):
    results: dict[str, ValidationResult] = {}
    processor = ValidationProcessor(mock_app, results, subprocess_timeout=10)
    with patch("subprocess.run", return_value=_completed_process(returncode=returncode, stdout=stdout, stderr=stderr)):
        processor.process_message(ValidationMessage(id="config", args=[]))

    assert results["config"].success is expected_success
    assert results["config"].stdout == stdout
    assert results["config"].stderr == stderr


def test_processor_passes_args_in_subprocess_command(mock_app):
    results: dict[str, ValidationResult] = {}
    processor = ValidationProcessor(mock_app, results, subprocess_timeout=10)
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(list(cmd))
        return _completed_process()

    with patch("subprocess.run", side_effect=fake_run):
        processor.process_message(ValidationMessage(id="config", args=["changed"]))

    assert len(captured) == 1
    assert "config" in captured[0]
    assert "changed" in captured[0]


@pytest.mark.parametrize(
    "returncode, display_method, expected_text",
    [
        pytest.param(0, "display_success", "ok config", id="pass"),
        pytest.param(1, "display_error", "FAIL config", id="fail"),
    ],
)
def test_processor_displays_result(mock_app, returncode, display_method, expected_text):
    results: dict[str, ValidationResult] = {}
    processor = ValidationProcessor(mock_app, results, subprocess_timeout=10)

    with patch("subprocess.run", return_value=_completed_process(returncode=returncode, stdout="ok", stderr="bad")):
        processor.process_message(ValidationMessage(id="config", args=[]))

    display_mock = getattr(mock_app, display_method)
    display_mock.assert_called_once()
    assert expected_text in str(display_mock.call_args)


def test_processor_handles_subprocess_timeout(mock_app):
    results: dict[str, ValidationResult] = {}
    processor = ValidationProcessor(mock_app, results, subprocess_timeout=10)

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["ddev"], timeout=580)):
        processor.process_message(ValidationMessage(id="config", args=[]))

    assert results["config"].success is False
    assert "timed out" in results["config"].stderr


# --- ValidationOrchestrator.on_initialize message submission ---


class CapturingOrchestrator(ValidationOrchestrator):
    """Orchestrator that captures submitted messages instead of dispatching them."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submitted: list[ValidationMessage] = []

    def submit_message(self, message: BaseMessage) -> None:
        assert isinstance(message, ValidationMessage)
        self.submitted.append(message)


@pytest.mark.parametrize(
    "validation, target, expect_args",
    [
        ("config", "changed", ["changed"]),
        ("metadata", "changed", ["changed"]),
        *[pytest.param(name, "changed", [], id=f"repo-wide-{name}") for name in sorted(REPO_WIDE_NAMES)],
        ("config", None, []),
        ("ci", None, []),
    ],
)
def test_on_initialize_message_args(mock_app, validation: str, target: str | None, expect_args: list[str]):
    orch = CapturingOrchestrator(app=mock_app, validations=[validation], target=target)
    asyncio.run(orch.on_initialize())

    assert len(orch.submitted) == 1
    assert orch.submitted[0].id == validation
    assert orch.submitted[0].args == expect_args


def test_on_initialize_submits_one_message_per_validation(mock_app):
    orch = CapturingOrchestrator(app=mock_app, validations=ALL_NAMES, target=None)
    asyncio.run(orch.on_initialize())

    assert len(orch.submitted) == len(ALL_NAMES)
    assert {m.id for m in orch.submitted} == set(ALL_NAMES)


# --- ValidationOrchestrator exit code logic ---


def test_all_pass_abort_not_called(mock_app):
    with patch("subprocess.run", return_value=_completed_process(returncode=0)):
        orch = ValidationOrchestrator(app=mock_app, validations=["config", "ci"], target=None, grace_period=0)
        orch.run()

    mock_app.abort.assert_not_called()


def test_any_failure_calls_abort(mock_app):
    def fake_run(cmd, **kwargs):
        if "config" in cmd:
            return _completed_process(returncode=1, stderr="bad config")
        return _completed_process(returncode=0)

    with patch("subprocess.run", side_effect=fake_run):
        orch = ValidationOrchestrator(app=mock_app, validations=["config", "ci"], target=None, grace_period=0)
        with pytest.raises(SystemExit):
            orch.run()

    mock_app.abort.assert_called_once()


def test_on_finalize_warns_on_incomplete_validations(mock_app):
    orch = ValidationOrchestrator(app=mock_app, validations=["config", "ci", "metadata"], target=None)
    orch._results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
    }
    with pytest.raises(SystemExit):
        asyncio.run(orch.on_finalize(exception=None))
    mock_app.display_warning.assert_called()
    warning_args = [str(c) for c in mock_app.display_warning.call_args_list]
    assert any("2 validation(s) did not complete" in w for w in warning_args)


def test_on_finalize_logs_exception(mock_app):
    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None)
    orch._results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=RuntimeError("boom")))
    error_args = [str(c) for c in mock_app.display_error.call_args_list]
    assert any("boom" in e for e in error_args)


# --- on_finalize PR comment + step summary integration ---


def test_on_finalize_writes_step_summary(mock_app, tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    mock_app.config.github.token = ""
    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None)
    orch._results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=None))

    assert summary_file.exists()
    assert "Validation Report" in summary_file.read_text()


def test_on_finalize_posts_pr_comment_on_failure(mock_app):
    mock_app.config.github.token = "fake-token"

    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None, pr_number=42)
    orch._results = {
        "config": ValidationResult(name="config", success=False, stdout="err", stderr="", duration=1.0),
    }
    with pytest.raises(SystemExit):
        asyncio.run(orch.on_finalize(exception=None))

    mock_app.github.post_pull_request_comment.assert_called_once()
    body = mock_app.github.post_pull_request_comment.call_args[0][1]
    assert "Validation Report" in body
    assert "[View full run](https://github.com/DataDog/integrations-core/actions/runs/12345)" in body


def test_on_finalize_includes_pr_warning_in_summary(mock_app, tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")

    mock_app.config.github.token = ""
    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None, pr_number=None)
    orch._results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=None))

    content = summary_file.read_text()
    assert "could not determine PR number" in content


def test_on_finalize_handles_post_failure(mock_app):
    mock_app.config.github.token = "fake-token"
    mock_app.github.post_pull_request_comment.side_effect = RuntimeError("network error")

    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None, pr_number=42)
    orch._results = {
        "config": ValidationResult(name="config", success=False, stdout="err", stderr="", duration=1.0),
    }
    with pytest.raises(SystemExit):
        asyncio.run(orch.on_finalize(exception=None))

    mock_app.display_warning.assert_called()
    warning_args = [str(c) for c in mock_app.display_warning.call_args_list]
    assert any("network error" in w for w in warning_args)


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
def testparse_pr_number_from_event(tmp_path, content, expected):
    event_file = tmp_path / "event.json"
    event_file.write_text(content)
    assert parse_pr_number_from_event(str(event_file)) == expected


def testparse_pr_number_from_event_file_not_found():
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
def testparse_pr_number_from_ref(ref, expected):
    assert parse_pr_number_from_ref(ref) == expected


# --- get_pr_number (integration with env vars and warnings) ---


@pytest.mark.parametrize(
    "event_name",
    [
        pytest.param("push", id="push-event"),
        pytest.param("merge_group", id="merge-group-event"),
    ],
)
def testget_pr_number_non_pr_events(mock_app, monkeypatch, event_name):
    monkeypatch.setenv("GITHUB_EVENT_NAME", event_name)

    assert get_pr_number(mock_app) is None
    mock_app.display_warning.assert_not_called()


def testget_pr_number_no_event_name(mock_app):
    assert get_pr_number(mock_app) is None
    mock_app.display_warning.assert_not_called()


def testget_pr_number_from_event_file(mock_app, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    event_file = tmp_path / "event.json"
    event_file.write_text('{"pull_request": {"number": 42}}')
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))

    assert get_pr_number(mock_app) == 42


def testget_pr_number_from_ref_fallback(mock_app, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_REF", "refs/pull/99/merge")

    assert get_pr_number(mock_app) == 99


def testget_pr_number_warns_on_event_file_failure(mock_app, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(tmp_path / "missing.json"))

    assert get_pr_number(mock_app) is None
    mock_app.display_warning.assert_called()


def testget_pr_number_warns_when_no_source_available(mock_app, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")

    assert get_pr_number(mock_app) is None
    mock_app.display_warning.assert_called()


# --- format_pr_comment ---


def testformat_pr_comment_all_passed():
    results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
        "ci": ValidationResult(name="ci", success=True, stdout="ok", stderr="", duration=2.0),
    }
    expected = "## Validation Report\n\nAll **2** validations passed."
    assert format_pr_comment(results, target="changed") == expected


def testformat_pr_comment_one_failure_with_target(helpers):
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


def testformat_pr_comment_stderr_fallback():
    results = {
        "config": ValidationResult(name="config", success=False, stdout="", stderr="stderr output", duration=1.0),
    }
    comment = format_pr_comment(results, target=None)
    assert "stderr output" in comment


def testformat_pr_comment_long_output_trimmed():
    long_output = "\n".join(f"line {i}" for i in range(200))
    results = {
        "config": ValidationResult(name="config", success=False, stdout=long_output, stderr="", duration=1.0),
    }
    comment = format_pr_comment(results, target=None)
    assert "trimmed to last 100 lines" in comment
    assert "line 199" in comment
    assert "line 0" not in comment


def testformat_pr_comment_failure_without_output():
    results = {
        "config": ValidationResult(name="config", success=False, stdout="", stderr="", duration=1.0),
    }
    comment = format_pr_comment(results, target=None)
    assert "<code>config</code>" in comment
    assert "```\n\n```" not in comment


def testformat_pr_comment_no_target():
    results = {
        "config": ValidationResult(name="config", success=False, stdout="fail", stderr="", duration=1.0),
    }
    comment = format_pr_comment(results, target=None)
    assert "ddev validate config\n" in comment


def testformat_pr_comment_with_error_and_warning(helpers):
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


def testget_workflow_run_url_returns_url():
    assert get_workflow_run_url() == "https://github.com/DataDog/integrations-core/actions/runs/12345"


def testget_workflow_run_url_returns_none_when_env_missing(monkeypatch):
    monkeypatch.delenv("GITHUB_RUN_ID")
    assert get_workflow_run_url() is None


# --- on_finalize without workflow run URL ---


def test_on_finalize_pr_comment_omits_run_link_when_env_missing(mock_app, monkeypatch):
    monkeypatch.delenv("GITHUB_RUN_ID")
    mock_app.config.github.token = "fake-token"

    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None, pr_number=42)
    orch._results = {
        "config": ValidationResult(name="config", success=False, stdout="err", stderr="", duration=1.0),
    }
    with pytest.raises(SystemExit):
        asyncio.run(orch.on_finalize(exception=None))

    body = mock_app.github.post_pull_request_comment.call_args[0][1]
    assert "[View full run]" not in body


# --- write_step_summary ---


def testwrite_step_summary_writes_to_file(tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_step_summary("## Report\nAll good")
    assert summary_file.read_text() == "## Report\nAll good\n"


def testwrite_step_summary_appends(tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    summary_file.write_text("existing\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_step_summary("new content")
    assert "existing\n" in summary_file.read_text()
    assert "new content\n" in summary_file.read_text()


def testwrite_step_summary_noop_without_env(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    write_step_summary("should not error")


# --- all click command (integration) ---

FAST_ORCHESTRATOR_OPTS = ("--grace-period", "0", "--max-timeout", "10", "--subprocess-timeout", "10")


def test_all_command_passes_when_all_validations_succeed(ddev):
    invoked: list[str] = []

    def fake_run(cmd, **kwargs):
        invoked.append(cmd[-1])
        return _completed_process(returncode=0, stdout="ok")

    with patch("subprocess.run", side_effect=fake_run):
        result = ddev("validate", "all", *FAST_ORCHESTRATOR_OPTS)

    assert result.exit_code == 0, result.output
    assert set(invoked) == set(ALL_NAMES)


def test_all_command_aborts_on_failure_with_details(ddev):
    def fake_run(cmd, **kwargs):
        if "config" in cmd:
            return _completed_process(returncode=1, stdout="invalid config found")
        return _completed_process(returncode=0, stdout="ok")

    with patch("subprocess.run", side_effect=fake_run):
        result = ddev("validate", "all", *FAST_ORCHESTRATOR_OPTS)

    assert result.exit_code != 0
    assert "1 failed" in result.output
    assert "── config" in result.output
    assert "invalid config found" in result.output
    assert "Fix: ddev validate config --sync" in result.output
    assert "Run `ddev validate all --fix` to attempt to auto-fix supported validations." in result.output


def test_all_command_passes_target_to_per_integration_validations(ddev):
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **kwargs):
        captured[cmd[-1] if cmd[-1] != "changed" else cmd[-2]] = list(cmd)
        return _completed_process(returncode=0, stdout="ok")

    with patch("subprocess.run", side_effect=fake_run):
        result = ddev("validate", "all", "changed", *FAST_ORCHESTRATOR_OPTS)

    assert result.exit_code == 0, result.output
    for name in ALL_NAMES:
        assert name in captured
        if name not in REPO_WIDE_NAMES:
            assert "changed" in captured[name]
        else:
            assert "changed" not in captured[name]


def test_all_command_fix_passes_correct_flags(ddev):
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **kwargs):
        name = cmd[4]
        captured[name] = list(cmd)
        return _completed_process(returncode=0, stdout="ok")

    with patch("subprocess.run", side_effect=fake_run):
        result = ddev("validate", "all", "--fix", *FAST_ORCHESTRATOR_OPTS)

    assert result.exit_code == 0, result.output
    for name, config in VALIDATIONS.items():
        assert name in captured
        if config.fix_flag:
            assert config.fix_flag in captured[name], f"{name} should have {config.fix_flag}"
        else:
            assert "--fix" not in captured[name] and "--sync" not in captured[name], (
                f"{name} should not have a fix flag"
            )
