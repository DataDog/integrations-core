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
    from ddev.cli.validate.all.orchestrator import ValidationResult

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
            with open(summary_path, "a") as f:
                f.write(content + "\n")


def format_pr_comment(
    results: dict[str, ValidationResult],
    target: str | None,
    *,
    error: str | None = None,
    warning: str | None = None,
) -> str:
    failures = {n for n, r in results.items() if not r.success}

    parts = [f"{COMMENT_HEADING}\n"]
    if error:
        parts.append(f"> **Error:** {error}\n")
    if warning:
        parts.append(f"> **Warning:** {warning}\n")

    parts.append("| Validation | Status |")
    parts.append("|---|---|")
    for name in sorted(results):
        status = "❌" if name in failures else "✅"
        parts.append(f"| `{name}` | {status} |")

    if failures:
        fix_target = f" {target}" if target else ""
        fix_all_cmd = f"ddev validate all{fix_target} --fix"
        parts.append(f"\nRun `{fix_all_cmd}` to attempt to auto-fix supported validations.")

    return "\n".join(parts)
