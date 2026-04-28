# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ddev.cli.validate.all.github import (
    COMMENT_HEADING,
    format_pr_comment,
    format_step_summary,
    get_workflow_run_url,
    write_step_summary,
)
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator, SyncProcessor

if TYPE_CHECKING:
    from ddev.cli.application import Application


@dataclass(frozen=True)
class ValidationConfig:
    description: str = ""
    repo_wide: bool = False
    fix_flag: str | None = None


# This is a subset of the available validations. Some validations still live
# in datadog-checks-dev and are not yet migrated to ddev. Once all validations
# are migrated, we can improve the command structure so each validation
# auto-registers itself instead of maintaining this manually.
VALIDATIONS: dict[str, ValidationConfig] = {
    "agent-reqs": ValidationConfig(
        description="Verify check versions match the Agent requirements file",
    ),
    "ci": ValidationConfig(
        description="Validate CI configuration and Codecov settings",
        repo_wide=True,
        fix_flag="--sync",
    ),
    "codeowners": ValidationConfig(
        description="Validate every integration has a CODEOWNERS entry",
        repo_wide=True,
    ),
    "config": ValidationConfig(
        description="Validate default configuration files against spec.yaml",
        fix_flag="--sync",
    ),
    "dep": ValidationConfig(
        description="Verify dependency pins are consistent and Agent-compatible",
        repo_wide=True,
    ),
    "eula": ValidationConfig(
        description="Validate EULA definition files",
    ),
    "http": ValidationConfig(
        description="Validate integrations use the HTTP wrapper correctly",
    ),
    "imports": ValidationConfig(
        description="Validate check imports do not use deprecated modules",
    ),
    "integration-style": ValidationConfig(
        description="Validate check code style conventions",
    ),
    "jmx-metrics": ValidationConfig(
        description="Validate JMX metrics definition files and config",
    ),
    "labeler": ValidationConfig(
        description="Validate PR labeler config matches integration directories",
        repo_wide=True,
        fix_flag="--sync",
    ),
    "legacy-signature": ValidationConfig(
        description="Validate no integration uses the legacy Agent check signature",
    ),
    "license-headers": ValidationConfig(
        description="Validate Python files have proper license headers",
        fix_flag="--fix",
    ),
    "licenses": ValidationConfig(
        description="Validate third-party license attribution list",
        repo_wide=True,
        fix_flag="--sync",
    ),
    "metadata": ValidationConfig(
        description="Validate metadata.csv metric definitions",
        fix_flag="--sync",
    ),
    "models": ValidationConfig(
        description="Validate configuration data models match spec.yaml",
        fix_flag="--sync",
    ),
    "openmetrics": ValidationConfig(
        description="Validate OpenMetrics integrations disable the metric limit",
    ),
    "package": ValidationConfig(
        description="Validate Python package metadata and naming",
    ),
    "readmes": ValidationConfig(
        description="Validate README files have required sections",
    ),
    "saved-views": ValidationConfig(
        description="Validate saved view JSON file structure and fields",
    ),
    "version": ValidationConfig(
        description="Validate version consistency between package and changelog",
    ),
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
            # Surface lifecycle hook failures so on_finalize can render them in the
            # validation report instead of silently logging.
            fail_fast=True,
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

        self._publish_report(exception)
        self._print_console_output()

    @property
    def had_failures(self) -> bool:
        """True if any validation failed or did not complete."""
        return any(not r.success for r in self._results.values()) or len(self._results) < len(self._validations)

    def _build_error_and_warning(self, exception: Exception | None) -> tuple[str | None, str | None]:
        error_msg = f"Error running validations: {exception}" if exception else None

        if self._pr_number is None and os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
            extra_warning = "Running in pull_request context but could not determine PR number to post a comment."
        else:
            extra_warning = None

        return error_msg, extra_warning

    def _delete_previous_comments(self, pr_number: int) -> None:
        try:
            comments = self._app.github.get_pull_request_comments(pr_number)
            for comment in comments:
                if comment.get("body", "").startswith(COMMENT_HEADING):
                    self._app.github.delete_comment(comment["id"])
        except Exception as exc:
            self._app.display_warning(f"Failed to clean up previous validation comments: {exc}")

    def _publish_report(self, exception: Exception | None) -> None:
        error_msg, extra_warning = self._build_error_and_warning(exception)

        summary_body = format_step_summary(
            self._results,
            VALIDATIONS,
            self._target,
            self._validations,
            error=error_msg,
            warning=extra_warning,
        )
        write_step_summary(summary_body)

        comment_body = format_pr_comment(
            self._results,
            VALIDATIONS,
            self._target,
            self._validations,
            error=error_msg,
            warning=extra_warning,
        )
        if run_url := get_workflow_run_url():
            comment_body += f"\n\n[View full run]({run_url})"

        self._app.logger.debug("PR number: %s", self._pr_number)
        self._app.logger.debug("GitHub token configured: %s", bool(self._app.config.github.token))

        if self._pr_number is None:
            self._app.logger.debug("No PR number — skipping PR comment.")
            return
        if not self._app.config.github.token:
            self._app.logger.debug("No GitHub token — skipping PR comment.")
            return

        httpx_logger = logging.getLogger("httpx")
        previous_level = httpx_logger.level
        httpx_logger.setLevel(logging.WARNING)
        try:
            self._app.logger.debug("Deleting previous validation comments on PR #%s...", self._pr_number)
            self._delete_previous_comments(self._pr_number)
            self._app.logger.debug("Posting validation comment on PR #%s...", self._pr_number)
            self._app.github.post_pull_request_comment(self._pr_number, comment_body)
            self._app.logger.debug("Comment posted successfully.")
        except Exception as exc:
            self._app.display_warning(f"Failed to post PR comment: {type(exc).__name__}: {exc}")
            write_step_summary(f"\n> Failed to post PR comment: {type(exc).__name__}: {exc}")
        finally:
            httpx_logger.setLevel(previous_level)

    def _print_console_output(self) -> None:
        from rich.rule import Rule

        failures = {name: r for name, r in self._results.items() if not r.success}
        passed = len(self._results) - len(failures)
        incomplete = len(self._validations) - len(self._results)

        self._app.display_info("")

        if failures:
            for name, result in sorted(failures.items()):
                self._app.console.print(Rule(title=name, style="red"))
                output = "\n".join(filter(None, [result.stdout, result.stderr]))
                if output:
                    self._app.console.print(output.rstrip())
                config = VALIDATIONS.get(name, ValidationConfig())
                if config.fix_flag:
                    fix_cmd = f"ddev validate {name} {config.fix_flag}"
                    self._app.display_info(f"Fix: {fix_cmd}")
                self._app.console.print()

        if incomplete:
            self._app.display_warning(f"{incomplete} validation(s) did not complete")
        if failures or incomplete:
            self._app.display_error(f"{len(failures)} failed, {passed} passed")
            fix_all_cmd = "ddev validate all --fix"
            if self._target:
                fix_all_cmd = f"ddev validate all {self._target} --fix"
            self._app.display_info(f"\nRun `{fix_all_cmd}` to attempt to auto-fix supported validations.")
        else:
            self._app.display_success(f"All {passed} validations passed")
