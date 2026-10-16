# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.cli.validate.all.orchestrator import ValidationConfig


def _load_validations(app: Application) -> dict[str, ValidationConfig]:
    """Read the selected validations from `.ddev/config.toml`.

    If the `/validations` key is absent, all known validations are returned.
    Unknown names are warned about and skipped.
    """
    from ddev.cli.validate.all.orchestrator import VALIDATIONS

    selected: list[str] | None = app.repo.config.get('/validations', None)
    if selected is None:
        return VALIDATIONS

    result: dict[str, ValidationConfig] = {}
    for name in selected:
        if name in VALIDATIONS:
            result[name] = VALIDATIONS[name]
        else:
            app.display_warning(f"Unknown validation in .ddev/config.toml: {name!r}")
    return result


@click.command(short_help="Run all validations in parallel")
@click.argument("target", required=False)
@click.option("--fix", is_flag=True, help="Attempt to auto-fix issues (passes --sync/--fix to each validation).")
@click.option("--grace-period", type=float, default=5, help="Seconds to wait for stragglers after first completion.")
@click.option("--max-timeout", type=float, default=600, help="Maximum total seconds before the orchestrator stops.")
@click.option(
    "--subprocess-timeout", type=float, default=580, help="Timeout in seconds for each validation subprocess."
)
@click.option(
    "--pr-comment-output",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Write the formatted pull request comment to this file instead of posting it to the pull request.",
)
@click.pass_obj
def all(
    app: Application,
    target: str | None,
    fix: bool,
    grace_period: float,
    max_timeout: float,
    subprocess_timeout: float,
    pr_comment_output: Path | None,
) -> None:
    """Run all validations in parallel.

    If TARGET is provided (e.g. 'changed'), per-integration validations are
    scoped to that target. Repo-wide validations always run without a target.
    """
    from ddev.cli.validate.all.github import format_pr_comment, get_pr_number
    from ddev.cli.validate.all.orchestrator import ValidationOrchestrator
    from ddev.utils.github_actions import get_workflow_run_url, write_step_summary

    selected = _load_validations(app)
    if not selected:
        msg = (
            "No validations are configured to run for this repository.\n"
            "Add entries to the `validations` list in `.ddev/config.toml` or remove the validation workflow."
        )
        app.display_error(msg)
        write_step_summary(f"## Validation Report\n\n> **Error:** {msg}")
        if pr_comment_output is not None:
            comment_body = format_pr_comment({}, {}, target, [], error=msg)
            if run_url := get_workflow_run_url():
                comment_body += f"\n\n[View full run]({run_url})"
            pr_comment_output.write_text(comment_body, encoding="utf-8")
        app.abort()

    pr_number = get_pr_number(app)
    orchestrator = ValidationOrchestrator(
        app=app,
        target=target,
        validations=list(selected),
        fix=fix,
        pr_number=pr_number,
        grace_period=grace_period,
        max_timeout=max_timeout,
        subprocess_timeout=subprocess_timeout,
        pr_comment_output=pr_comment_output,
    )
    orchestrator.run()

    if orchestrator.had_failures:
        app.abort()
