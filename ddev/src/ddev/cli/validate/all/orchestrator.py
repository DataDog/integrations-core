# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ddev.cli.validate.all.github import (
    format_pr_comment,
    get_workflow_run_url,
    write_step_summary,
)
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator, SyncProcessor

if TYPE_CHECKING:
    from ddev.cli.application import Application


@dataclass(frozen=True)
class ValidationConfig:
    repo_wide: bool = False
    fix_flag: str | None = None


# This is a subset of the available validations. Some validations still live
# in datadog-checks-dev and are not yet migrated to ddev. Once all validations
# are migrated, we can improve the command structure so each validation
# auto-registers itself instead of maintaining this manually.
VALIDATIONS: dict[str, ValidationConfig] = {
    "agent-reqs": ValidationConfig(),
    "ci": ValidationConfig(repo_wide=True, fix_flag="--sync"),
    "codeowners": ValidationConfig(repo_wide=True),
    "config": ValidationConfig(fix_flag="--sync"),
    "dep": ValidationConfig(repo_wide=True),
    "http": ValidationConfig(),
    "imports": ValidationConfig(),
    "integration-style": ValidationConfig(),
    "jmx-metrics": ValidationConfig(),
    "labeler": ValidationConfig(repo_wide=True, fix_flag="--sync"),
    "legacy-signature": ValidationConfig(),
    "license-headers": ValidationConfig(fix_flag="--fix"),
    "licenses": ValidationConfig(repo_wide=True, fix_flag="--sync"),
    "metadata": ValidationConfig(fix_flag="--sync"),
    "models": ValidationConfig(fix_flag="--sync"),
    "openmetrics": ValidationConfig(),
    "package": ValidationConfig(),
    "readmes": ValidationConfig(),
    "saved-views": ValidationConfig(),
    "version": ValidationConfig(),
}

SUBPROCESS_TIMEOUT = 580


@dataclass
class ValidationMessage(BaseMessage):
    args: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    name: str
    success: bool
    stdout: str
    stderr: str
    duration: float


class ValidationProcessor(SyncProcessor[ValidationMessage]):
    def __init__(self, app: Application, results: dict[str, ValidationResult], subprocess_timeout: float):
        super().__init__("validation-processor")
        self._app = app
        self._results = results
        self._subprocess_timeout = subprocess_timeout
        self._lock = threading.Lock()

    def process_message(self, message: ValidationMessage) -> None:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "ddev", "validate", message.id, *message.args],
                capture_output=True,
                text=True,
                timeout=self._subprocess_timeout,
            )
            result = ValidationResult(
                name=message.id,
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration=time.monotonic() - start,
            )
        except subprocess.TimeoutExpired:
            result = ValidationResult(
                name=message.id,
                success=False,
                stdout="",
                stderr=f"Validation timed out after {self._subprocess_timeout}s",
                duration=time.monotonic() - start,
            )

        with self._lock:
            self._results[message.id] = result

        if result.success:
            self._app.display_success(f"  ok {result.name} ({result.duration:.1f}s)")
        else:
            self._app.display_error(f"  FAIL {result.name} ({result.duration:.1f}s)")


class ValidationOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        app: Application,
        target: str | None,
        validations: list[str] | None = None,
        fix: bool = False,
        pr_number: int | None = None,
        grace_period: float = 5,
        max_timeout: float = 600,
        subprocess_timeout: float = SUBPROCESS_TIMEOUT,
    ):
        validations = validations if validations is not None else list(VALIDATIONS)
        super().__init__(
            logger=app.logger,
            max_timeout=max_timeout,
            grace_period=grace_period,
            executor=ThreadPoolExecutor(max_workers=len(validations)),
        )
        self._app = app
        self._validations = validations
        self._target = target
        self._fix = fix
        self._pr_number = pr_number
        self._results: dict[str, ValidationResult] = {}

        self.register_processor(
            ValidationProcessor(app, self._results, subprocess_timeout),
            [ValidationMessage],
        )

    async def on_initialize(self) -> None:
        for name in self._validations:
            config = VALIDATIONS.get(name, ValidationConfig())
            args: list[str] = []
            if not config.repo_wide and self._target:
                args.append(self._target)
            if self._fix and config.fix_flag:
                args.append(config.fix_flag)
            self.submit_message(ValidationMessage(id=name, args=args))

    async def on_message_received(self, message: BaseMessage) -> None:
        self._app.display_info(f"Starting: {message.id}")

    async def on_finalize(self, exception: Exception | None) -> None:
        if exception is not None:
            self._app.display_error(f"Error running validations: {exception}")

        self._post_pr_comment(exception)
        self._print_console_output()

    def _build_report_body(self, exception: Exception | None) -> str:
        error_msg = f"Error running validations: {exception}" if exception else None

        if self._pr_number is None and os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
            extra_warning = "Running in pull_request context but could not determine PR number to post a comment."
        else:
            extra_warning = None

        body = format_pr_comment(self._results, self._target, error=error_msg, warning=extra_warning)
        if run_url := get_workflow_run_url():
            body += f"\n\n[View full run]({run_url})"
        return body

    def _post_pr_comment(self, exception: Exception | None) -> None:
        body = self._build_report_body(exception)
        write_step_summary(body)

        any_failed = any(not r.success for r in self._results.values())
        if self._pr_number is not None and self._app.config.github.token and (any_failed or exception):
            try:
                self._app.github.post_pull_request_comment(self._pr_number, body)
            except Exception as exc:
                self._app.display_warning(f"Failed to post PR comment: {exc}")
                write_step_summary(f"\n> Failed to post PR comment: {exc}")

    def _print_console_output(self) -> None:
        failures = {name: r for name, r in self._results.items() if not r.success}
        passed = len(self._results) - len(failures)
        incomplete = len(self._validations) - len(self._results)

        if failures:
            self._app.display_info("")
            for name, result in sorted(failures.items()):
                config = VALIDATIONS.get(name, ValidationConfig())
                output = result.stdout or result.stderr
                self._app.display_error(f"── {name} {'─' * (60 - len(name))}")
                if output:
                    self._app.display_info(output.rstrip())
                fix_cmd = f"ddev validate {name}"
                if self._target and not config.repo_wide:
                    fix_cmd += f" {self._target}"
                if config.fix_flag:
                    fix_cmd += f" {config.fix_flag}"
                self._app.display_info(f"Fix: {fix_cmd}")

        self._app.display_info("")
        if incomplete:
            self._app.display_warning(f"{incomplete} validation(s) did not complete")
        if failures or incomplete:
            self._app.display_error(f"{len(failures)} failed, {passed} passed")
            fix_all_cmd = "ddev validate all --fix"
            if self._target:
                fix_all_cmd = f"ddev validate all {self._target} --fix"
            self._app.display_info(f"\nRun `{fix_all_cmd}` to attempt to auto-fix supported validations.")
            self._app.abort()
        else:
            self._app.display_success(f"All {passed} validations passed")
