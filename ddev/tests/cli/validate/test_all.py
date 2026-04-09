# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ddev.cli.validate.all import (
    ALL_CORE_VALIDATIONS,
    REPO_WIDE_VALIDATIONS,
    ValidationMessage,
    ValidationOrchestrator,
    ValidationProcessor,
    ValidationResult,
    _format_pr_comment,
    _get_pr_number,
)


def _completed_process(returncode=0, stdout="", stderr=""):
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def _make_app():
    app = MagicMock()
    app.abort.side_effect = SystemExit(1)
    return app


# --- ValidationProcessor ---


def test_processor_captures_stdout_stderr_on_success():
    results: dict[str, ValidationResult] = {}
    processor = ValidationProcessor(results)
    with patch("subprocess.run", return_value=_completed_process(returncode=0, stdout="all good", stderr="")):
        processor.process_message(ValidationMessage(id="config", args=[]))

    assert results["config"].success is True
    assert results["config"].stdout == "all good"
    assert results["config"].stderr == ""
    assert results["config"].duration >= 0


def test_processor_captures_stderr_on_failure():
    results: dict[str, ValidationResult] = {}
    processor = ValidationProcessor(results)
    with patch("subprocess.run", return_value=_completed_process(returncode=1, stdout="", stderr="error details")):
        processor.process_message(ValidationMessage(id="metadata", args=["changed"]))

    assert results["metadata"].success is False
    assert results["metadata"].stderr == "error details"


def test_processor_passes_args_in_subprocess_command():
    results: dict[str, ValidationResult] = {}
    processor = ValidationProcessor(results)
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(list(cmd))
        return _completed_process()

    with patch("subprocess.run", side_effect=fake_run):
        processor.process_message(ValidationMessage(id="config", args=["changed"]))

    assert len(captured) == 1
    assert "config" in captured[0]
    assert "changed" in captured[0]


def test_processor_on_result_callback_called():
    results: dict[str, ValidationResult] = {}
    callback_results: list[ValidationResult] = []
    processor = ValidationProcessor(results, on_result=callback_results.append)

    with patch("subprocess.run", return_value=_completed_process(returncode=0, stdout="ok")):
        processor.process_message(ValidationMessage(id="config", args=[]))

    assert len(callback_results) == 1
    assert callback_results[0].name == "config"
    assert callback_results[0].success is True


def test_processor_on_result_callback_not_called_when_none():
    results: dict[str, ValidationResult] = {}
    processor = ValidationProcessor(results, on_result=None)

    with patch("subprocess.run", return_value=_completed_process(returncode=0)):
        processor.process_message(ValidationMessage(id="config", args=[]))

    assert "config" in results


# --- ValidationOrchestrator.on_initialize message submission ---


@pytest.mark.parametrize(
    "validation, target, expect_args",
    [
        ("config", "changed", ["changed"]),
        ("metadata", "changed", ["changed"]),
        *[(name, "changed", []) for name in REPO_WIDE_VALIDATIONS],
        ("config", None, []),
        ("ci", None, []),
    ],
)
def test_on_initialize_message_args(validation: str, target: str | None, expect_args: list[str]):
    app = _make_app()
    submitted: list[ValidationMessage] = []

    class CapturingOrchestrator(ValidationOrchestrator):
        def submit_message(self, message):
            submitted.append(message)

    orch = CapturingOrchestrator(app=app, validations=[validation], target=target)
    asyncio.run(orch.on_initialize())

    assert len(submitted) == 1
    assert submitted[0].id == validation
    assert submitted[0].args == expect_args


def test_on_initialize_submits_one_message_per_validation():
    app = _make_app()
    submitted: list[ValidationMessage] = []

    class CapturingOrchestrator(ValidationOrchestrator):
        def submit_message(self, message):
            submitted.append(message)

    orch = CapturingOrchestrator(app=app, validations=ALL_CORE_VALIDATIONS, target=None)
    asyncio.run(orch.on_initialize())

    assert len(submitted) == len(ALL_CORE_VALIDATIONS)
    assert {m.id for m in submitted} == set(ALL_CORE_VALIDATIONS)


# --- ValidationOrchestrator exit code logic ---


def test_all_pass_abort_not_called():
    app = _make_app()
    with patch("subprocess.run", return_value=_completed_process(returncode=0)):
        orch = ValidationOrchestrator(app=app, validations=["config", "ci"], target=None)
        orch.run()

    app.abort.assert_not_called()


def test_any_failure_calls_abort():
    app = _make_app()

    def fake_run(cmd, **kwargs):
        if "config" in cmd:
            return _completed_process(returncode=1, stderr="bad config")
        return _completed_process(returncode=0)

    with patch("subprocess.run", side_effect=fake_run):
        orch = ValidationOrchestrator(app=app, validations=["config", "ci"], target=None)
        with pytest.raises(SystemExit):
            orch.run()

    app.abort.assert_called_once()


def test_on_complete_hook_called_with_results():
    app = _make_app()
    collected: list[dict] = []

    with patch("subprocess.run", return_value=_completed_process(returncode=0, stdout="ok")):
        orch = ValidationOrchestrator(
            app=app,
            validations=["config"],
            target=None,
            on_complete=lambda results: collected.append(results),
        )
        orch.run()

    assert len(collected) == 1
    assert "config" in collected[0]
    assert collected[0]["config"].success is True


# --- _get_pr_number ---


_GITHUB_ENV_KEYS = ("GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH", "GITHUB_REF")


def _clear_github_env(monkeypatch):
    for key in _GITHUB_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize(
    "env, event_content, expected",
    [
        pytest.param({"GITHUB_EVENT_NAME": "push"}, None, None, id="push-event"),
        pytest.param({"GITHUB_EVENT_NAME": "merge_group"}, None, None, id="merge-group-event"),
        pytest.param({}, None, None, id="no-event-name"),
        pytest.param({"GITHUB_EVENT_NAME": "pull_request"}, None, None, id="no-event-path-no-ref"),
        pytest.param(
            {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_EVENT_PATH": "/nonexistent/event.json"},
            None,
            None,
            id="file-not-found",
        ),
        pytest.param(
            {"GITHUB_EVENT_NAME": "pull_request"},
            "{bad json}",
            None,
            id="malformed-json",
        ),
        pytest.param(
            {"GITHUB_EVENT_NAME": "pull_request"},
            "{}",
            None,
            id="missing-pr-key",
        ),
        pytest.param(
            {"GITHUB_EVENT_NAME": "pull_request"},
            '{"pull_request": "bad"}',
            None,
            id="pr-not-dict",
        ),
        pytest.param(
            {"GITHUB_EVENT_NAME": "pull_request"},
            '{"pull_request": {}}',
            None,
            id="missing-number",
        ),
        pytest.param(
            {"GITHUB_EVENT_NAME": "pull_request"},
            '{"pull_request": {"number": "x"}}',
            None,
            id="number-not-int",
        ),
        pytest.param(
            {"GITHUB_EVENT_NAME": "pull_request"},
            '{"pull_request": {"number": 42}}',
            42,
            id="happy-path",
        ),
    ],
)
def test_get_pr_number(tmp_path, monkeypatch, env, event_content, expected):
    _clear_github_env(monkeypatch)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    if event_content is not None and "GITHUB_EVENT_PATH" not in env:
        event_file = tmp_path / "event.json"
        event_file.write_text(event_content)
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))

    assert _get_pr_number() == expected


@pytest.mark.parametrize(
    "ref, expected",
    [
        pytest.param("refs/pull/99/merge", 99, id="valid-ref"),
        pytest.param("refs/heads/main", None, id="branch-ref"),
        pytest.param("refs/pull/notanumber/merge", None, id="non-numeric-ref"),
    ],
)
def test_get_pr_number_github_ref_fallback(monkeypatch, ref, expected):
    _clear_github_env(monkeypatch)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_REF", ref)

    assert _get_pr_number() == expected


# --- _format_pr_comment ---


def test_format_pr_comment_all_passed():
    results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
        "ci": ValidationResult(name="ci", success=True, stdout="ok", stderr="", duration=2.0),
    }
    comment = _format_pr_comment(results, target="changed")
    assert "All **2** validations passed" in comment
    assert "<details>" not in comment


def test_format_pr_comment_mixed_results():
    results = {
        "config": ValidationResult(name="config", success=False, stdout="error output", stderr="", duration=1.0),
        "ci": ValidationResult(name="ci", success=True, stdout="ok", stderr="", duration=2.0),
    }
    comment = _format_pr_comment(results, target="changed")
    assert "**1 validation(s) failed**" in comment
    assert "1 passed" in comment
    assert "<code>config</code>" in comment
    assert "error output" in comment
    assert "ddev validate config changed" in comment
    assert "Passed (1)" in comment


def test_format_pr_comment_stderr_fallback():
    results = {
        "config": ValidationResult(name="config", success=False, stdout="", stderr="stderr output", duration=1.0),
    }
    comment = _format_pr_comment(results, target=None)
    assert "stderr output" in comment


def test_format_pr_comment_long_output_trimmed():
    long_output = "\n".join(f"line {i}" for i in range(200))
    results = {
        "config": ValidationResult(name="config", success=False, stdout=long_output, stderr="", duration=1.0),
    }
    comment = _format_pr_comment(results, target=None)
    assert "trimmed to last 100 lines" in comment
    assert "line 199" in comment
    assert "line 0" not in comment


def test_format_pr_comment_no_target():
    results = {
        "config": ValidationResult(name="config", success=False, stdout="fail", stderr="", duration=1.0),
    }
    comment = _format_pr_comment(results, target=None)
    assert "ddev validate config\n" in comment
