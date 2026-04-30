# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

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
@click.pass_obj
def all(
    app: Application,
    target: str | None,
    fix: bool,
    grace_period: float,
    max_timeout: float,
    subprocess_timeout: float,
) -> None:
    """Run all validations in parallel.

    If TARGET is provided (e.g. 'changed'), per-integration validations are
    scoped to that target. Repo-wide validations always run without a target.
    """
    from ddev.cli.validate.all.github import get_pr_number, should_suppress_validation_comments, write_step_summary
    from ddev.cli.validate.all.orchestrator import ValidationOrchestrator

    selected = _load_validations(app)
    if not selected:
        msg = (
            "No validations are configured to run for this repository.\n"
            "Add entries to the `validations` list in `.ddev/config.toml` or remove the validation workflow."
        )
        app.display_error(msg)
        write_step_summary(f"## Validation Report\n\n> **Error:** {msg}")
        app.abort()

    pr_number = get_pr_number(app)
    suppress_pr_comments = should_suppress_validation_comments()
    orchestrator = ValidationOrchestrator(
        app=app,
        target=target,
        validations=list(selected),
        fix=fix,
        pr_number=pr_number,
        suppress_pr_comments=suppress_pr_comments,
        grace_period=grace_period,
        max_timeout=max_timeout,
        subprocess_timeout=subprocess_timeout,
    )
    orchestrator.run()
