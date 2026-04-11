# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from unittest.mock import patch

from ddev.cli.validate.all.orchestrator import VALIDATIONS

from .conftest import completed_process

ALL_NAMES = list(VALIDATIONS)
REPO_WIDE_NAMES = {name for name, cfg in VALIDATIONS.items() if cfg.repo_wide}
FAST_ORCHESTRATOR_OPTS = ("--grace-period", "0", "--max-timeout", "10", "--subprocess-timeout", "10")


def test_all_command_passes_when_all_validations_succeed(ddev):
    invoked: list[str] = []

    def fake_run(cmd, **kwargs):
        invoked.append(cmd[-1])
        return completed_process(returncode=0, stdout="ok")

    with patch("subprocess.run", side_effect=fake_run):
        result = ddev("validate", "all", *FAST_ORCHESTRATOR_OPTS)

    assert result.exit_code == 0, result.output
    assert set(invoked) == set(ALL_NAMES)


def test_all_command_aborts_on_failure_with_details(ddev):
    def fake_run(cmd, **kwargs):
        if "config" in cmd:
            return completed_process(returncode=1, stdout="invalid config found")
        return completed_process(returncode=0, stdout="ok")

    with patch("subprocess.run", side_effect=fake_run):
        result = ddev("validate", "all", *FAST_ORCHESTRATOR_OPTS)

    assert result.exit_code != 0
    assert "1 failed" in result.output
    assert "── config" in result.output
    assert "invalid config found" in result.output
    assert "Fix: ddev validate config --sync" in result.output
    assert "Run `ddev validate all --fix` to attempt to auto-fix supported validations." in result.output


def test_all_command_shows_both_stdout_and_stderr_on_failure(ddev):
    def fake_run(cmd, **kwargs):
        if "config" in cmd:
            return completed_process(returncode=1, stdout="stdout output", stderr="stderr output")
        return completed_process(returncode=0, stdout="ok")

    with patch("subprocess.run", side_effect=fake_run):
        result = ddev("validate", "all", *FAST_ORCHESTRATOR_OPTS)

    assert result.exit_code != 0
    assert "stdout output" in result.output
    assert "stderr output" in result.output


def test_all_command_passes_target_to_per_integration_validations(ddev):
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **kwargs):
        captured[cmd[-1] if cmd[-1] != "changed" else cmd[-2]] = list(cmd)
        return completed_process(returncode=0, stdout="ok")

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
        return completed_process(returncode=0, stdout="ok")

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
