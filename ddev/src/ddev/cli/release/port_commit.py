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
@click.argument('commit_hash', required=False)
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
) -> None:
    """
    Backport a commit onto a target branch.

    Cherry-picks COMMIT_HASH onto `--target-branch` (default `master`) on a new branch named
    `<github-user>/<prefix>-<sha[:10]>-<suffix>`, preserving `.in-toto` files from the target
    branch so package signatures stay intact. Pushes the branch and, unless `--no-pr` is set,
    opens a pull request titled `[Backport] <subject>` and labeled with `--pr-labels`.

    If COMMIT_HASH is omitted, the current HEAD commit is used after confirmation.

    The GitHub user for the branch prefix is taken from `ddev config` (`github.user`) or the
    `DD_GITHUB_USER` / `GITHUB_USER` / `GITHUB_ACTOR` environment variables.
    """
    from ddev.cli.release.port_commit_workflow import PortStepError, build_port_steps, resolve_port_plan

    plan = resolve_port_plan(
        app,
        commit_hash=commit_hash,
        target_branch=target_branch,
        branch_prefix=branch_prefix,
        branch_suffix=branch_suffix,
        pr_labels=pr_labels,
        no_pr=no_pr,
        draft=draft,
        verify=verify,
        dry_run=dry_run,
    )
    steps, pr_step = build_port_steps(app, plan)

    try:
        for step in steps:
            step.run()
    except PortStepError as e:
        app.abort(str(e))

    if pr_step is not None and pr_step.pr_url:
        app.display_success(f'Pull request created: {pr_step.pr_url}')
    app.display_success('All done.')
