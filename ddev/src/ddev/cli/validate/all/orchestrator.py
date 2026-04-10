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

REPO_WIDE_VALIDATIONS: frozenset[str] = frozenset({"ci", "codeowners", "dep", "labeler", "licenses"})

# This is a subset of the available validations. Some validations still live
# in datadog-checks-dev and are not yet migrated to ddev. Once all validations
# are migrated, we can improve the command structure so each validation
# auto-registers itself with this list instead of maintaining it manually.
ALL_CORE_VALIDATIONS: list[str] = [
    "agent-reqs",
    "ci",
    "codeowners",
    "config",
    "dep",
    "http",
    "imports",
    "integration-style",
    "jmx-metrics",
    "labeler",
    "legacy-signature",
    "license-headers",
    "licenses",
    "metadata",
    "models",
    "openmetrics",
    "package",
    "readmes",
    "saved-views",
    "version",
]

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
        pr_number: int | None = None,
        grace_period: float = 5,
        max_timeout: float = 600,
        subprocess_timeout: float = SUBPROCESS_TIMEOUT,
    ):
        validations = validations if validations is not None else list(ALL_CORE_VALIDATIONS)
        super().__init__(
            logger=app.logger,
            max_timeout=max_timeout,
            grace_period=grace_period,
            executor=ThreadPoolExecutor(max_workers=len(validations)),
        )
        self._app = app
        self._validations = validations
        self._target = target
        self._pr_number = pr_number
        self._results: dict[str, ValidationResult] = {}

        self.register_processor(
            ValidationProcessor(app, self._results, subprocess_timeout),
            [ValidationMessage],
        )

    async def on_initialize(self) -> None:
        for name in self._validations:
            # Repo-wide validations (ci, codeowners, etc.) always run without a
            # target because they check the entire repository. Per-integration
            # validations receive the target (e.g. "changed") to scope their check.
            args: list[str] = [] if name in REPO_WIDE_VALIDATIONS else ([self._target] if self._target else [])
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
        passed = sum(bool(r.success) for r in self._results.values())
        failed = sum(not r.success for r in self._results.values())
        incomplete = len(self._validations) - len(self._results)

        self._app.display_info("")
        if incomplete:
            self._app.display_warning(f"{incomplete} validation(s) did not complete")
        if failed or incomplete:
            self._app.display_error(f"{failed} failed, {passed} passed")
            self._app.abort()
        else:
            self._app.display_success(f"All {passed} validations passed")
