# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help="Run all validations in parallel")
@click.argument("target", required=False)
@click.option("--grace-period", type=float, default=5, help="Seconds to wait for stragglers after first completion.")
@click.option("--max-timeout", type=float, default=600, help="Maximum total seconds before the orchestrator stops.")
@click.option(
    "--subprocess-timeout", type=float, default=580, help="Timeout in seconds for each validation subprocess."
)
@click.pass_obj
def all(
    app: Application, target: str | None, grace_period: float, max_timeout: float, subprocess_timeout: float
) -> None:
    """Run all validations in parallel.

    If TARGET is provided (e.g. 'changed'), per-integration validations are
    scoped to that target. Repo-wide validations always run without a target.
    """
    from ddev.cli.validate.all.github import get_pr_number
    from ddev.cli.validate.all.orchestrator import ValidationOrchestrator

    pr_number = get_pr_number(app)
    orchestrator = ValidationOrchestrator(
        app=app,
        target=target,
        pr_number=pr_number,
        grace_period=grace_period,
        max_timeout=max_timeout,
        subprocess_timeout=subprocess_timeout,
    )
    orchestrator.run()
