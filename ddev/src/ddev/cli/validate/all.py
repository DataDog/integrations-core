# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import click

from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator, SyncProcessor
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from collections.abc import Callable

    from ddev.cli.application import Application

REPO_WIDE_VALIDATIONS: frozenset[str] = frozenset({"ci", "codeowners", "dep", "labeler", "licenses"})

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

_MAX_OUTPUT_LINES = 100


def _get_pr_number() -> int | None:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        return None

    if event_path := os.environ.get("GITHUB_EVENT_PATH"):
        try:
            event = json.loads(Path(event_path).read_text())
        except (json.JSONDecodeError, OSError):
            return None
        pr = event.get("pull_request")
        if not isinstance(pr, dict):
            return None
        number = pr.get("number")
        return number if isinstance(number, int) else None

    ref = os.environ.get("GITHUB_REF", "")
    if ref.startswith("refs/pull/") and ref.endswith("/merge"):
        try:
            return int(ref.split("/")[2])
        except (IndexError, ValueError):
            pass

    return None


def _format_pr_comment(results: dict[str, ValidationResult], target: str | None) -> str:
    failed = {name: r for name, r in results.items() if not r.success}
    passed = {name: r for name, r in results.items() if r.success}

    lines: list[str] = ["## Validation Report", ""]

    if failed:
        lines.append(f"**{len(failed)} validation(s) failed** — {len(passed)} passed.")
    else:
        lines.append(f"All **{len(passed)}** validations passed.")
        return "\n".join(lines)

    lines.append("")

    for name, result in sorted(failed.items()):
        output = result.stdout or result.stderr
        if output:
            output_lines = output.splitlines()
            if len(output_lines) > _MAX_OUTPUT_LINES:
                output_lines = output_lines[-_MAX_OUTPUT_LINES:]
                output = "\n".join(output_lines)
                output = f"... (trimmed to last {_MAX_OUTPUT_LINES} lines)\n{output}"
            else:
                output = "\n".join(output_lines)

        fix_target = f" {target}" if target else ""
        lines.append("<details>")
        lines.append(f"<summary><code>{name}</code></summary>")
        lines.append("")
        if output:
            lines.append("```")
            lines.append(output)
            lines.append("```")
            lines.append("")
        lines.append("**Fix locally:**")
        lines.append("```shell")
        lines.append(f"ddev validate {name}{fix_target}")
        lines.append("```")
        lines.append("</details>")
        lines.append("")

    if passed:
        lines.append("<details>")
        lines.append(f"<summary>Passed ({len(passed)})</summary>")
        lines.append("")
        for name in sorted(passed):
            lines.append(f"- `{name}`")
        lines.append("</details>")

    return "\n".join(lines)


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
    def __init__(
        self,
        results: dict[str, ValidationResult],
        on_result: Callable[[ValidationResult], None] | None = None,
    ):
        super().__init__("validation-processor")
        self._results = results
        self._lock = threading.Lock()
        self._on_result = on_result

    def process_message(self, message: ValidationMessage) -> None:
        start = time.monotonic()
        proc = subprocess.run(
            [sys.executable, "-m", "ddev", "validate", message.id, *message.args],
            capture_output=True,
            text=True,
        )
        duration = time.monotonic() - start
        result = ValidationResult(
            name=message.id,
            success=proc.returncode == 0,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration=duration,
        )
        with self._lock:
            self._results[message.id] = result
        if self._on_result:
            self._on_result(result)


class ValidationOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        app: Application,
        validations: list[str],
        target: str | None,
        on_complete: Callable[[dict[str, ValidationResult]], None] | None = None,
    ):
        super().__init__(
            logger=app.logger,
            max_timeout=600,
            grace_period=5,
            executor=ThreadPoolExecutor(max_workers=len(validations)),
        )
        self._app = app
        self._validations = validations
        self._target = target
        self._on_complete = on_complete
        self._results: dict[str, ValidationResult] = {}

        def _on_result(result: ValidationResult) -> None:
            if result.success:
                app.display_success(f"  ok {result.name} ({result.duration:.1f}s)")
            else:
                app.display_error(f"  FAIL {result.name} ({result.duration:.1f}s)")

        self.register_processor(
            ValidationProcessor(self._results, on_result=_on_result),
            [ValidationMessage],
        )

    async def on_initialize(self) -> None:
        for name in self._validations:
            args: list[str] = [] if name in REPO_WIDE_VALIDATIONS else ([self._target] if self._target else [])
            self.submit_message(ValidationMessage(id=name, args=args))

    async def on_message_received(self, message: BaseMessage) -> None:
        self._app.display_info(f"Starting: {message.id}")

    async def on_finalize(self, exception: Exception | None) -> None:
        if self._on_complete is not None:
            self._on_complete(self._results)

        passed = sum(1 for r in self._results.values() if r.success)
        failed = sum(1 for r in self._results.values() if not r.success)
        incomplete = len(self._validations) - len(self._results)

        self._app.display_info("")
        if incomplete:
            self._app.display_warning(f"{incomplete} validation(s) did not complete")
        if failed:
            self._app.display_error(f"{failed} failed, {passed} passed")
            self._app.abort()
        else:
            self._app.display_success(f"All {passed} validations passed")


@click.command(short_help="Run all validations in parallel")
@click.argument("target", required=False)
@click.pass_obj
def all(app: Application, target: str | None) -> None:
    """Run all validations in parallel.

    If TARGET is provided (e.g. 'changed'), per-integration validations are
    scoped to that target. Repo-wide validations always run without a target.
    """
    on_complete: Callable[[dict[str, ValidationResult]], None] | None = None

    pr_number = _get_pr_number()
    if pr_number is not None and app.config.github.token:

        def on_complete(results: dict[str, ValidationResult]) -> None:
            any_failed = any(not r.success for r in results.values())
            if not any_failed:
                return
            body = _format_pr_comment(results, target)
            try:
                app.github.post_pull_request_comment(pr_number, body)
            except Exception:
                app.display_warning("Failed to post PR comment")

    orchestrator = ValidationOrchestrator(
        app=app,
        validations=ALL_CORE_VALIDATIONS,
        target=target,
        on_complete=on_complete,
    )
    orchestrator.run()
