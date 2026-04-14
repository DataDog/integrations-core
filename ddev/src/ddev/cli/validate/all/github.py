# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import contextlib
import json
import os
from typing import TYPE_CHECKING

from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.cli.validate.all.orchestrator import ValidationConfig, ValidationResult

COMMENT_HEADING = "## Validation Report"


def parse_pr_number_from_event(event_path: str) -> int | None:
    """Extract the PR number from the GitHub Actions event JSON file."""
    try:
        event = json.loads(Path(event_path).read_text())
    except (json.JSONDecodeError, OSError):
        return None

    pr = event.get("pull_request")
    if isinstance(pr, dict):
        number = pr.get("number")
        if isinstance(number, int):
            return number

    return None


def parse_pr_number_from_ref(ref: str) -> int | None:
    """Extract the PR number from a GITHUB_REF like refs/pull/123/merge."""
    if ref.startswith("refs/pull/") and ref.endswith("/merge"):
        with contextlib.suppress(IndexError, ValueError):
            return int(ref.split("/")[2])
    return None


def get_pr_number(app: Application) -> int | None:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        return None

    if event_path := os.environ.get("GITHUB_EVENT_PATH"):
        if pr_number := parse_pr_number_from_event(event_path):
            return pr_number
        app.display_warning(f"Failed to extract PR number from event file: {event_path}")
        return None

    ref = os.environ.get("GITHUB_REF", "")
    if pr_number := parse_pr_number_from_ref(ref):
        return pr_number

    app.display_warning("Running in pull_request context but could not determine PR number")
    return None


def get_workflow_run_url() -> str | None:
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return None


def write_step_summary(content: str) -> None:
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with contextlib.suppress(OSError):
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(content + "\n")


def _build_preamble(error: str | None, warning: str | None) -> list[str]:
    parts: list[str] = [f"{COMMENT_HEADING}\n"]
    if error:
        parts.append(f"> **Error:** {error}\n")
    if warning:
        parts.append(f"> **Warning:** {warning}\n")
    return parts


def _build_table(
    rows: dict[str, ValidationResult],
    configs: dict[str, ValidationConfig],
) -> list[str]:
    """Build a markdown table with Validation, Description, and Status columns."""
    from ddev.cli.validate.all.orchestrator import ValidationConfig as _VC

    lines = ["| Validation | Description | Status |", "|---|---|---|"]
    for name in sorted(rows):
        status = "✅" if rows[name].success else "❌"
        description = configs.get(name, _VC()).description
        lines.append(f"| `{name}` | {description} | {status} |")
    return lines


def _build_report_section(
    rows: dict[str, ValidationResult],
    configs: dict[str, ValidationConfig],
    *,
    header: str | None = None,
    collapsed: bool = False,
) -> list[str]:
    table = _build_table(rows, configs)
    if collapsed:
        summary = header or "Details"
        return [
            "",
            f"<details>\n<summary>{summary}</summary>\n",
            *table,
            "\n</details>",
        ]
    if header:
        return [header, "", *table]
    return table


def format_pr_comment(
    results: dict[str, ValidationResult],
    configs: dict[str, ValidationConfig],
    target: str | None,
    *,
    expected_count: int | None = None,
    error: str | None = None,
    warning: str | None = None,
) -> str:
    """Format a PR comment with collapsible sections to reduce clutter."""
    failures: dict[str, ValidationResult] = {}
    passed: dict[str, ValidationResult] = {}
    for name, result in results.items():
        (passed if result.success else failures)[name] = result

    incomplete = (expected_count or 0) - len(results)
    parts = _build_preamble(error, warning)

    if incomplete > 0:
        parts.append(f"> **Warning:** {incomplete} validation(s) did not complete.\n")

    if failures:
        parts.extend(_build_report_section(failures, configs))
        fix_target = f" {target}" if target else ""
        parts.append(f"\nRun `ddev validate all{fix_target} --fix` to attempt to auto-fix supported validations.")

    if passed:
        if failures or incomplete > 0:
            header = f"Passed validations ({len(passed)})"
        else:
            parts.append(f"All {len(passed)} validations passed.")
            header = "Show details"
        parts.extend(_build_report_section(passed, configs, header=header, collapsed=True))

    return "\n".join(parts)


def format_step_summary(
    results: dict[str, ValidationResult],
    configs: dict[str, ValidationConfig],
    target: str | None,
    *,
    expected_count: int | None = None,
    error: str | None = None,
    warning: str | None = None,
) -> str:
    """Format a flat summary table for the GitHub Actions step summary."""
    has_failures = any(not r.success for r in results.values())
    incomplete = (expected_count or 0) - len(results)

    parts = _build_preamble(error, warning)

    if incomplete > 0:
        parts.append(f"> **Warning:** {incomplete} validation(s) did not complete.\n")

    parts.extend(_build_table(results, configs))

    if has_failures:
        fix_target = f" {target}" if target else ""
        fix_all_cmd = f"ddev validate all{fix_target} --fix"
        parts.append(f"\nRun `{fix_all_cmd}` to attempt to auto-fix supported validations.")

    return "\n".join(parts)
