# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import patch

import pytest

from ddev.cli.validate.all import _load_validations
from ddev.cli.validate.all.orchestrator import (
    VALIDATIONS,
    ValidationMessage,
    ValidationOrchestrator,
    ValidationProcessor,
    ValidationResult,
)
from ddev.event_bus.orchestrator import BaseMessage

from .conftest import completed_process

ALL_NAMES = list(VALIDATIONS)
REPO_WIDE_NAMES = {name for name, cfg in VALIDATIONS.items() if cfg.repo_wide}


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
    with patch("subprocess.run", return_value=completed_process(returncode=returncode, stdout=stdout, stderr=stderr)):
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
        return completed_process()

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

    with patch("subprocess.run", return_value=completed_process(returncode=returncode, stdout="ok", stderr="bad")):
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


# --- ValidationOrchestrator.on_initialize ---


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


def test_all_pass_had_failures_is_false(mock_app):
    with patch("subprocess.run", return_value=completed_process(returncode=0)):
        orch = ValidationOrchestrator(app=mock_app, validations=["config", "ci"], target=None, grace_period=0)
        orch.run()

    assert orch.had_failures is False
    mock_app.abort.assert_not_called()


def test_any_failure_marks_had_failures(mock_app):
    def fake_run(cmd, **kwargs):
        if "config" in cmd:
            return completed_process(returncode=1, stderr="bad config")
        return completed_process(returncode=0)

    with patch("subprocess.run", side_effect=fake_run):
        orch = ValidationOrchestrator(app=mock_app, validations=["config", "ci"], target=None, grace_period=0)
        orch.run()

    assert orch.had_failures is True
    # Aborting is the CLI command's responsibility, not the orchestrator's.
    mock_app.abort.assert_not_called()


def test_incomplete_validations_marks_had_failures(mock_app):
    orch = ValidationOrchestrator(app=mock_app, validations=["config", "ci", "metadata"], target=None)
    orch._results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=None))

    assert orch.had_failures is True
    mock_app.display_warning.assert_called()
    warning_args = [str(c) for c in mock_app.display_warning.call_args_list]
    assert any("2 validation(s) did not complete" in w for w in warning_args)
    mock_app.abort.assert_not_called()


def test_on_finalize_logs_exception(mock_app):
    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None)
    orch._results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=RuntimeError("boom")))
    error_args = [str(c) for c in mock_app.display_error.call_args_list]
    assert any("boom" in e for e in error_args)


# --- on_finalize PR comment + step summary ---


def test_on_finalize_writes_step_summary(mock_app, tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    mock_app.config.github.token = ""
    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None)
    orch._results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=None))

    content = summary_file.read_text(encoding="utf-8")
    assert "Validation Report" in content
    assert "| Validation | Description | Status |" in content
    assert "| `config` |" in content


def test_on_finalize_posts_pr_comment_on_failure(mock_app):
    mock_app.config.github.token = "fake-token"

    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None, pr_number=42)
    orch._results = {
        "config": ValidationResult(name="config", success=False, stdout="err", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=None))

    mock_app.github.post_pull_request_comment.assert_called_once()
    body = mock_app.github.post_pull_request_comment.call_args[0][1]
    assert "Validation Report" in body
    assert "| Validation | Description | Status |" in body
    assert "Validate default configuration files against spec.yaml" in body
    assert "| `config` |" in body
    assert "❌" in body
    assert "[View full run](https://github.com/DataDog/integrations-core/actions/runs/12345)" in body


def test_on_finalize_pr_comment_omits_run_link_when_env_missing(mock_app, monkeypatch):
    monkeypatch.delenv("GITHUB_RUN_ID")
    mock_app.config.github.token = "fake-token"

    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None, pr_number=42)
    orch._results = {
        "config": ValidationResult(name="config", success=False, stdout="err", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=None))

    body = mock_app.github.post_pull_request_comment.call_args[0][1]
    assert "[View full run]" not in body


def test_on_finalize_step_summary_does_not_include_run_link(mock_app, tmp_path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    mock_app.config.github.token = "fake-token"
    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None, pr_number=42)
    orch._results = {
        "config": ValidationResult(name="config", success=False, stdout="err", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=None))

    content = summary_file.read_text(encoding="utf-8")
    assert "[View full run]" not in content


def test_on_finalize_posts_pr_comment_on_success(mock_app):
    mock_app.config.github.token = "fake-token"

    orch = ValidationOrchestrator(app=mock_app, validations=["config", "ci"], target=None, pr_number=42)
    orch._results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
        "ci": ValidationResult(name="ci", success=True, stdout="ok", stderr="", duration=2.0),
    }
    asyncio.run(orch.on_finalize(exception=None))

    mock_app.github.post_pull_request_comment.assert_called_once()
    body = mock_app.github.post_pull_request_comment.call_args[0][1]
    assert "All 2 validations passed." in body
    assert "<details>" in body
    assert "| `ci` |" in body
    assert "| `config` |" in body


def test_on_finalize_deletes_previous_validation_comments(mock_app):
    mock_app.config.github.token = "fake-token"
    mock_app.github.get_pull_request_comments.return_value = [
        {"id": 100, "body": "## Validation Report\nold report"},
        {"id": 200, "body": "unrelated comment"},
    ]

    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None, pr_number=42)
    orch._results = {
        "config": ValidationResult(name="config", success=True, stdout="ok", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=None))

    mock_app.github.delete_comment.assert_called_once_with(100)
    mock_app.github.post_pull_request_comment.assert_called_once()


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

    content = summary_file.read_text(encoding="utf-8")
    assert "could not determine PR number" in content


def test_on_finalize_handles_post_failure(mock_app):
    mock_app.config.github.token = "fake-token"
    mock_app.github.post_pull_request_comment.side_effect = RuntimeError("network error")

    orch = ValidationOrchestrator(app=mock_app, validations=["config"], target=None, pr_number=42)
    orch._results = {
        "config": ValidationResult(name="config", success=False, stdout="err", stderr="", duration=1.0),
    }
    asyncio.run(orch.on_finalize(exception=None))

    mock_app.display_warning.assert_called()
    warning_args = [str(c) for c in mock_app.display_warning.call_args_list]
    assert any("network error" in w for w in warning_args)


# --- load_validations ---


def test_load_validations_returns_all_when_config_absent(mock_app):
    mock_app.repo.config.get.return_value = None

    result = _load_validations(mock_app)

    assert result is VALIDATIONS
    mock_app.display_warning.assert_not_called()


def test_load_validations_filters_to_selected_names(mock_app):
    mock_app.repo.config.get.return_value = ["ci", "config"]

    result = _load_validations(mock_app)

    assert set(result) == {"ci", "config"}
    assert result["ci"] == VALIDATIONS["ci"]
    assert result["config"] == VALIDATIONS["config"]
    mock_app.display_warning.assert_not_called()


def test_load_validations_warns_on_unknown_name(mock_app):
    mock_app.repo.config.get.return_value = ["ci", "nonexistent"]

    result = _load_validations(mock_app)

    assert set(result) == {"ci"}
    mock_app.display_warning.assert_called_once()
    assert "nonexistent" in str(mock_app.display_warning.call_args)


def test_load_validations_empty_list_returns_empty(mock_app):
    mock_app.repo.config.get.return_value = []

    result = _load_validations(mock_app)

    assert result == {}
    mock_app.display_warning.assert_not_called()
