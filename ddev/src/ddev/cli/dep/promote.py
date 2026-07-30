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

    Refuses to dispatch while dependency resolution is still running for the head
    commit, because promotion publishes whatever is in dev storage at the time.

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

        with app.status('Checking for dependency resolution in flight...'):
            unfinished_runs = app.github.get_unfinished_workflow_runs(RESOLUTION_WORKFLOW, head_sha)

        if unfinished_runs:
            # Promotion copies whatever is in dev storage when it runs, and an
            # unfinished run has not uploaded its wheels or committed its lockfiles.
            app.display_error(f'Dependency resolution is still running for {head_sha}.')
            for run in unfinished_runs:
                app.display_info(f'  {run["status"]}: {run["html_url"]}')
            app.abort('Wait for it to commit the lockfiles, then promote the new head.')

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
