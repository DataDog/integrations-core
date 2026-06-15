# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.cli.ci.tests.messages import FailedCheck, UpdatePRComment, WorkflowStatus

# Hidden marker kept as the first line of every dispatcher comment. It brands the comment and lets the
# updater find an existing comment to edit across dispatcher re-runs.
COMMENT_MARKER = "<!-- ddev-dispatch-tests -->"


def format_pr_comment(message: UpdatePRComment) -> str:
    """Render an ``UpdatePRComment`` into the Markdown body for the PR comment."""
    success_total = sum(status.success_count or 0 for status in message.workflows)
    failed_total = sum(status.failed_count or 0 for status in message.workflows)

    lines = [
        COMMENT_MARKER,
        _header(message.done, failed_total),
        "",
        _summary(message.done, success_total, failed_total, message.running_count),
    ]

    failed_sections = [_format_workflow(status) for status in message.workflows if status.failed_checks]
    if failed_sections:
        lines.append("")
        lines.append("### Failed jobs")
        for section in failed_sections:
            lines.append("")
            lines.append(section)

    if message.done and message.summary_url:
        lines.append("")
        lines.append(f"[View full summary]({message.summary_url})")

    return "\n".join(lines)


def _header(done: bool, failed_total: int) -> str:
    """Build the title line for the comment."""
    if not done:
        return "## 🧪 Test Dispatcher — _running_"
    icon = "❌" if failed_total else "✅"
    return f"## {icon} Test Dispatcher — _complete_"


def _summary(done: bool, success_total: int, failed_total: int, running_total: int) -> str:
    """Build the one-line counts summary."""
    counts = f"**{success_total}** succeeded, **{failed_total}** failed"
    if not done:
        return f"{counts}, **{running_total}** running. Workflows are still running…"
    return f"{counts}."


def _format_workflow(status: WorkflowStatus) -> str:
    """Render a single workflow's failed jobs as a linked heading followed by a list."""
    lines = [f"#### [Workflow run]({status.url})"]
    lines.extend(_format_failed_check(check) for check in status.failed_checks)
    return "\n".join(lines)


def _format_failed_check(check: FailedCheck) -> str:
    """Render one failed/timed-out job line with its error and any failed tests."""
    target = f"`{check.name}` · `{check.environment}`" if check.environment else f"`{check.name}`"
    error = f" — {check.error}" if check.error else ""
    line = f"- {target}{error}"
    if check.failed_tests:
        tests = ", ".join(f"`{test}`" for test in check.failed_tests)
        line += f"\n  - Failed tests: {tests}"
    return line
