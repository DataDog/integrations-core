# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import contextlib
import json
import os
from string import Template
from typing import TYPE_CHECKING

from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.cli.validate.all.orchestrator import ValidationResult

MAX_OUTPUT_LINES = 100

FAILURE_DETAIL_TEMPLATE = Template("""\
<details>
<summary><code>${name}</code></summary>

${output_block}\
**Fix locally:**
```shell
ddev validate ${name}${fix_target}
```
</details>
""")

PASSED_SECTION_TEMPLATE = Template("""\
<details>
<summary>Passed (${count})</summary>

${items}
</details>""")


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


def format_failure_output(result: ValidationResult) -> str:
    output = result.stdout or result.stderr
    if not output:
        return ""
    lines = output.splitlines()
    if len(lines) > MAX_OUTPUT_LINES:
        output = f"... (trimmed to last {MAX_OUTPUT_LINES} lines)\n" + "\n".join(lines[-MAX_OUTPUT_LINES:])
    return f"```\n{output}\n```\n\n"


def format_pr_comment(
    results: dict[str, ValidationResult],
    target: str | None,
    *,
    error: str | None = None,
    warning: str | None = None,
) -> str:
    failures: dict[str, ValidationResult] = {}
    successes: dict[str, ValidationResult] = {}
    for name, result in results.items():
        (successes if result.success else failures)[name] = result

    parts = ["## Validation Report\n"]
    if error:
        parts.append(f"> **Error:** {error}\n")
    if warning:
        parts.append(f"> **Warning:** {warning}\n")

    if not failures:
        parts.append(f"All **{len(successes)}** validations passed.")
        return "\n".join(parts)

    parts.append(f"**{len(failures)} validation(s) failed** — {len(successes)} passed.\n")

    fix_target = f" {target}" if target else ""
    for name, result in sorted(failures.items()):
        parts.append(
            FAILURE_DETAIL_TEMPLATE.substitute(
                name=name, output_block=format_failure_output(result), fix_target=fix_target
            )
        )

    if successes:
        items = "\n".join(f"- `{name}`" for name in sorted(successes))
        parts.append(PASSED_SECTION_TEMPLATE.substitute(count=len(successes), items=items))

    fix_all_cmd = f"ddev validate all{fix_target} --fix"
    body = "\n".join(parts).rstrip()
    body += f"\n\nRun `{fix_all_cmd}` to attempt to auto-fix supported validations."

    return body
