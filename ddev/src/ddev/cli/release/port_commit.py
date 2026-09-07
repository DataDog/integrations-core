# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(name='port-commit', short_help='Backport a commit onto a target branch')
@click.pass_obj
@click.argument('commit_hash', required=False, metavar='COMMIT_OR_PR')
@click.option('-t', '--target-branch', default='master', show_default=True, help='Target branch to port to.')
@click.option('-p', '--branch-prefix', default='port', show_default=True, help='Branch name prefix.')
@click.option('-s', '--branch-suffix', default=None, help='Branch name suffix. Defaults to `to-<target-branch>`.')
@click.option(
    '-l',
    '--pr-labels',
    default='qa/skip-qa',
    show_default=True,
    help='Comma-separated PR labels.',
)
@click.option('--no-pr', is_flag=True, default=False, help="Don't create a pull request.")
@click.option('--draft', is_flag=True, default=False, help='Open the PR as a draft.')
@click.option('--verify', is_flag=True, default=False, help='Run commit hooks (skipped by default).')
@click.option('--dry-run', is_flag=True, default=False, help='Print every step instead of executing it.')
@click.option(
    '--from-pr',
    'from_pr',
    type=int,
    default=None,
    metavar='PR_NUMBER',
    help='Backport a merged PR to every `backport/<base>` label on it, deriving the commit and target '
    'branches from the PR. Mutually exclusive with COMMIT_OR_PR.',
)
def port_commit(
    app: Application,
    commit_hash: str | None,
    target_branch: str,
    branch_prefix: str,
    branch_suffix: str | None,
    pr_labels: str,
    no_pr: bool,
    draft: bool,
    verify: bool,
    dry_run: bool,
    from_pr: int | None,
) -> None:
    """
    Backport a commit onto a target branch.

    Cherry-picks COMMIT_OR_PR onto `--target-branch` (default `master`) on a new branch named
    `<github-user>/<prefix>-<sha[:10]>-<suffix>`, preserving `.in-toto` and `.deps/` files from the target
    branch so package signatures stay intact. Pushes the branch and, unless `--no-pr` is set,
    opens a pull request titled `[Backport] <subject>` and labeled with `--pr-labels`.

    COMMIT_OR_PR accepts: a full 40-character commit SHA, a PR number (e.g. `23703`), an
    explicit `PR-<number>` token, or a GitHub PR URL. Pure-digit inputs are tried as a PR
    first when a GitHub token is configured, and fall back to commit resolution on 404. If
    omitted, the current HEAD commit is used after confirmation.

    Pass `--from-pr <number>` instead of COMMIT_OR_PR to backport a merged PR to every
    `backport/<base>` label on it, deriving the commit and target branches from the PR. A base
    whose backport PR already exists (open, merged, or closed) is skipped, so re-runs are
    idempotent. Give `--target-branch` alongside `--from-pr` to restrict the backport to that one
    branch.

    The GitHub user for the branch prefix is taken from `ddev config` (`github.user`) or the
    `DD_GITHUB_USER` / `GITHUB_USER` / `GITHUB_ACTOR` environment variables.
    """
    import logging

    from ddev.cli.release.port_commit_workflow import (
        PortOptions,
        display_completion_summary,
        execute_port_plan,
        resolve_port_plan,
        run_backport_from_pr,
    )

    # httpx logs every request at INFO and clutters the workflow output. The PR-resolution and
    # PR-creation steps already print their own status lines; the underlying HTTP traffic is noise.
    logging.getLogger('httpx').setLevel(logging.WARNING)

    options = PortOptions(
        branch_prefix=branch_prefix,
        branch_suffix=branch_suffix,
        pr_labels=pr_labels,
        no_pr=no_pr,
        draft=draft,
        verify=verify,
        dry_run=dry_run,
    )

    if from_pr is not None:
        if commit_hash is not None:
            app.abort('Pass either COMMIT_OR_PR or --from-pr, not both.')
        from click.core import ParameterSource

        ctx = click.get_current_context()
        target_branch_explicit = ctx.get_parameter_source('target_branch') is not ParameterSource.DEFAULT
        override_base = target_branch if target_branch_explicit else None
        succeeded = run_backport_from_pr(
            app,
            pr_number=from_pr,
            override_base=override_base,
            options=options,
        )
        if not succeeded:
            app.abort('One or more backports failed.')
        return

    plan = resolve_port_plan(
        app,
        commit_hash=commit_hash,
        target_branch=target_branch,
        options=options,
    )

    outcome = execute_port_plan(app, plan)
    if outcome.error is not None:
        app.abort(outcome.error)

    if plan.dry_run:
        app.display_success('Dry run complete.')
        return

    display_completion_summary(app, plan, pr_url=outcome.pr_url)
