# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application

PR_URL_RE = re.compile(r"https://github\.com/[^/]+/[^/]+/pull/(\d+)")
PROMOTE_WORKFLOW = "dependency-wheel-promotion.yaml"
PROMOTE_WORKFLOW_REF = "master"
RESOLUTION_WORKFLOW = "resolve-build-deps.yaml"


@click.command(short_help='Promote dependency wheels from dev to stable')
@click.argument('pr_url')
@click.pass_obj
def promote(app: Application, pr_url: str):
    """
    Promote dependency wheels for a pull request from dev to stable storage.

    Dispatches the dependency-wheel-promotion workflow for PR_URL, which copies
    wheels from the dev/ GCS prefix to stable/ so the Agent can reference them
    after merge.

    Refuses to dispatch unless dependency resolution has finished successfully for the
    head commit, because promotion publishes whatever is in dev storage at the time.
    Pull requests from forks cannot be promoted, since resolution never runs on them.

    Example:

    \b
        ddev dep promote https://github.com/DataDog/integrations-core/pull/12345
    """
    match = PR_URL_RE.search(pr_url)
    if not match:
        app.abort(f'Could not extract a PR number from: {pr_url}')
    assert match

    pr_number = int(match.group(1))

    httpx_logger = logging.getLogger('httpx')
    previous_level = httpx_logger.level
    httpx_logger.setLevel(logging.WARNING)
    try:
        with app.status(f'Fetching PR #{pr_number} head...'):
            head_sha, head_ref = app.github.get_pr_head(pr_number)

        app.display_info(f'PR #{pr_number}: branch {head_ref}, SHA {head_sha}')

        with app.status('Checking whether the pull request comes from a fork...'):
            from_fork = app.github.pull_request_is_from_fork(pr_number)

        if from_fork:
            # Resolution only runs on pushes to branches in this repository, so a fork
            # head carries no lockfiles of its own and promoting it would publish the
            # base branch's wheels behind a green check.
            app.display_error(f'PR #{pr_number} comes from a fork, so its dependencies were never resolved.')
            app.abort('Reopen the change as a branch in this repository, then promote that pull request.')

        with app.status('Checking dependency resolution for the head commit...'):
            resolution_run = app.github.get_latest_workflow_run(RESOLUTION_WORKFLOW, head_sha)

        # No run at all leaves nothing to judge, so promotion goes ahead as before.
        if resolution_run is not None:
            if resolution_run['status'] != 'completed':
                # Promotion copies whatever is in dev storage when it runs, and a run
                # still going has not uploaded its wheels or committed its lockfiles.
                app.display_error(f'Dependency resolution is still running for {head_sha}.')
                app.display_info(f'  {resolution_run["status"]}: {resolution_run["html_url"]}')
                app.abort('Wait for it to commit the lockfiles, then promote the new head.')
            elif resolution_run.get('conclusion') != 'success':
                # The lockfiles at this head are still the previous ones, so promoting
                # would report a resolution that never published as ready to merge.
                app.display_error(f'Dependency resolution did not succeed for {head_sha}.')
                app.display_info(f'  {resolution_run.get("conclusion")}: {resolution_run["html_url"]}')
                app.abort('Re-run it and let it commit the lockfiles before promoting.')

        with app.status('Dispatching promote workflow...'):
            run_details = app.github.dispatch_workflow(
                workflow_id=PROMOTE_WORKFLOW,
                ref=PROMOTE_WORKFLOW_REF,
                inputs={'pr_number': str(pr_number), 'head_sha': head_sha},
                return_run_details=True,
            )

        if not run_details:
            app.abort('Workflow dispatched but no run details were returned.')
        app.display_success(f'Promote workflow dispatched for PR #{pr_number}.')
        app.display_info(f'Workflow run: {run_details["html_url"]}')
    finally:
        httpx_logger.setLevel(previous_level)
