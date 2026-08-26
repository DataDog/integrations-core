# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The `ddev ci dispatch-tests` command: the Dispatcher's entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.cli.ci.tests.batching.units import EnvironmentProvider
    from ddev.cli.ci.tests.dispatcher import DispatcherContext, RunContext
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.cli.ci.tests.messages import TestBatch
    from ddev.utils.github_async.models import PullRequest

DEFAULT_OUTPUT_DIRECTORY = ".dispatcher"


@click.command(short_help='Run the Dispatcher to test a commit as parallel batches')
@click.pass_obj
@click.option(
    '--pr',
    'pull_request',
    metavar='PR_NUMBER_OR_URL',
    default=None,
    help='Pull request to test, as a number or a URL. Its branch, commits and target branch are read from GitHub.',
)
@click.option('--pr-number', type=int, default=None, help='Pull request number, when not using `--pr`.')
@click.option('--checkout-sha', default=None, help='Ref the test workflow checks out. Defaults to the base commit.')
@click.option('--base-sha', default=None, help='Commit the run reports against. Defaults to the local HEAD.')
@click.option('--branch', default=None, help='Branch being tested. Defaults to the current branch.')
@click.option('--target-branch', default=None, help='Target branch of the pull request, used as the comparison base.')
@click.option(
    '--context',
    'run_context',
    type=click.Choice(['pr', 'master', 'agent-test', 'release']),
    default=None,
    help='Kind of run. Defaults to `pr` when a pull request is known, `master` otherwise.',
)
@click.option('--repo', 'repository', default=None, metavar='OWNER/NAME', help='Repository to dispatch against.')
@click.option('--all', 'all_targets', is_flag=True, help='Test every eligible target instead of the affected ones.')
@click.option('--workflow', default=None, help='Workflow each batch is dispatched to.')
@click.option('--workflow-ref', default=None, help='Ref the workflow definition is loaded from.')
@click.option(
    '--output-dir',
    default=None,
    help='Where the run writes what it produces: artifacts, coverage and test results.',
)
@click.option('--dry-run', is_flag=True, help='Show the plan and the resolved context without calling GitHub.')
def dispatch_tests(
    app: Application,
    pull_request: str | None,
    pr_number: int | None,
    checkout_sha: str | None,
    base_sha: str | None,
    branch: str | None,
    target_branch: str | None,
    run_context: str | None,
    repository: str | None,
    all_targets: bool,
    workflow: str | None,
    workflow_ref: str | None,
    output_dir: str | None,
    dry_run: bool,
) -> None:
    """Plan the tests a commit requires, run them as parallel batches of GitHub Actions jobs, and
    report the result to the pull request and to the run summary.

    Every input can be passed explicitly, which is how a workflow calls it. Locally, `--pr` reads
    the branch, commits and target branch from GitHub so only the pull request has to be named.
    """
    import logging
    from pathlib import Path

    from ddev.cli.ci.tests.batching.build import HatchEnvironmentProvider
    from ddev.cli.ci.tests.dispatcher import DispatcherContext, RunContext, build_dispatcher
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.utils.github import resolve_owner_repo

    requested_pr, token = validate_options(
        app,
        pull_request=pull_request,
        pr_number=pr_number,
        branch=branch,
        base_sha=base_sha,
        target_branch=target_branch,
        dry_run=dry_run,
    )

    # One INFO line per request would bury the Dispatcher's own progress.
    logging.getLogger('httpx').setLevel(logging.WARNING)

    config = DispatcherConfig.from_repo_config(app.repo.config)
    owner, repo = resolve_owner_repo(app, repository)

    resolved_number = resolved_branch = resolved_sha = resolved_target = None
    if requested_pr is not None:
        resolved = fetch_pull_request(app, owner, repo, requested_pr, token)
        if resolved.head is None or resolved.base is None:
            app.abort(f'Pull request {resolved.number} reports no branch references.')
        resolved_number = resolved.number
        resolved_branch, resolved_sha, resolved_target = resolved.head.ref, resolved.head.sha, resolved.base.ref

    pr_number = pr_number if pr_number is not None else resolved_number
    branch = branch or resolved_branch or app.repo.git.current_branch()
    base_sha = base_sha or resolved_sha or app.repo.git.latest_commit().sha
    target_branch = target_branch or resolved_target
    checkout_sha = checkout_sha or (f'refs/pull/{pr_number}/merge' if pr_number is not None else base_sha)
    resolved_context = RunContext(run_context) if run_context else (RunContext.PR if pr_number else RunContext.MASTER)

    batches = build_plan(
        app,
        config=config,
        base_sha=base_sha,
        run_context=resolved_context,
        target_branch=target_branch,
        all_targets=all_targets,
        environment_provider=HatchEnvironmentProvider(app.platform, config.default_python_version),
    )
    if not batches:
        app.display_info('No affected target to test.')
        return

    context = DispatcherContext(
        owner=owner,
        repo=repo,
        run_context=resolved_context,
        checkout_sha=checkout_sha,
        base_sha=base_sha,
        branch=branch,
        workflow=workflow or config.workflow,
        workflow_ref=workflow_ref or config.workflow_ref,
        target_branch=target_branch,
        pr_number=pr_number,
    )

    display_plan(app, context, batches)
    if dry_run:
        app.display_info('Dry run: nothing was dispatched.')
        return

    base_path = Path(output_dir) if output_dir else app.repo.path / DEFAULT_OUTPUT_DIRECTORY
    dispatcher = build_dispatcher(
        batches=batches,
        context=context,
        config=config,
        token=token,
        artifacts_path=base_path / 'artifacts',
        output_path=base_path / 'results',
        run_logger=app.logger,
    )
    # A fatal processor or hook failure leaves the bus by raising out of `run`. `on_finalize` has
    # already published whatever it knew by then, so a message is more use here than a traceback.
    try:
        dispatcher.run()
    except Exception as error:
        app.abort(f'Dispatcher execution failed: {error}')

    outcome = dispatcher.outcome
    if outcome is None or not outcome.successful:
        app.abort('Dispatcher tests failed.')

    app.display_success('Dispatcher tests passed.')


def validate_options(
    app: Application,
    *,
    pull_request: str | None,
    pr_number: int | None,
    branch: str | None,
    base_sha: str | None,
    target_branch: str | None,
    dry_run: bool,
) -> tuple[int | None, str]:
    """Check every input before the run does any work, and return what checking them resolved.

    That is the pull request ``--pr`` names, if any, and the GitHub token, empty when the run needs
    none: a dry run planning from local git talks to nobody. Reading a pull request needs a token
    even for a dry run, because the API client refuses to be built without one.
    """
    from ddev.utils.github import parse_pull_request_reference

    requested_pr = None
    if pull_request is not None:
        resolved_by_pr = [
            name
            for name, value in (
                ('`--pr-number`', pr_number),
                ('`--branch`', branch),
                ('`--base-sha`', base_sha),
                ('`--target-branch`', target_branch),
            )
            if value is not None
        ]
        if resolved_by_pr:
            app.abort(f'{", ".join(resolved_by_pr)} cannot be passed with `--pr`, which reads them from GitHub.')

        requested_pr = parse_pull_request_reference(pull_request)
        if requested_pr is None:
            app.abort(f'`{pull_request}` is neither a pull request number nor a pull request URL.')

    token = app.config.github.token
    if not token and (pull_request is not None or not dry_run):
        app.abort('A GitHub token is required. Set `github.token` in your ddev config.')

    return requested_pr, token


def fetch_pull_request(app: Application, owner: str, repo: str, number: int, token: str) -> PullRequest:
    """Read pull request *number* from the GitHub API."""
    import asyncio

    import httpx
    from pydantic import ValidationError

    from ddev.utils.github_async import async_github_client
    from ddev.utils.github_errors import GitHubAuthenticationError

    async def fetch() -> PullRequest:
        async with async_github_client(token=token) as client:
            response = await client.get_pull_request(owner, repo, number)
            return response.data

    try:
        return asyncio.run(fetch())
    except GitHubAuthenticationError as error:
        app.abort(str(error))
    except (httpx.HTTPError, ValidationError) as error:
        app.abort(f'Could not read pull request {number}: {error}')


def build_plan(
    app: Application,
    *,
    config: DispatcherConfig,
    base_sha: str,
    run_context: RunContext,
    target_branch: str | None,
    all_targets: bool,
    environment_provider: EnvironmentProvider,
) -> list[TestBatch]:
    """Build the batches this run must execute, aborting with a readable message on a bad plan.

    `--all` skips the comparison entirely: what changed is not what decides which targets run.
    """
    from ddev.cli.ci.tests.batching.build import build_test_batches
    from ddev.cli.ci.tests.batching.exceptions import PlanningError
    from ddev.cli.ci.tests.batching.targets import all_target_rules
    from ddev.cli.ci.tests.changes import CIContext, get_changed_files
    from ddev.cli.ci.tests.dispatcher import RunContext

    changed_files = []
    rules = None
    if all_targets:
        rules = all_target_rules()
    else:
        ci_context = CIContext.PULL_REQUEST if run_context is RunContext.PR else CIContext.DEFAULT_BRANCH
        try:
            changed_files = get_changed_files(app.repo.git, base_sha, context=ci_context, target_branch=target_branch)
        except ValueError as error:
            app.abort(str(error))
        except OSError as error:
            # `GitRepository` reports a failed git invocation as OSError, and the usual cause is a
            # commit the local clone has never fetched.
            app.abort(
                f'Could not compare {base_sha} against {target_branch or "its parent"} locally: {error}\n'
                'Fetch the commit first, or pass `--all` to plan every target.'
            )

    try:
        batches = build_test_batches(
            app.repo,
            changed_files,
            environment_provider=environment_provider,
            config=config.batching,
            rules=rules,
        )
    except PlanningError as error:
        app.abort(f'Could not build a test plan: {error}')

    return batches


def display_plan(app: Application, context: DispatcherContext, batches: list[TestBatch]) -> None:
    app.display_header('Dispatcher plan')
    app.display_pair('Repository', f'{context.owner}/{context.repo}')
    app.display_pair('Context', context.run_context.value)
    app.display_pair('Branch', context.branch)
    app.display_pair('Base commit', context.base_sha)
    app.display_pair('Checkout ref', context.checkout_sha)
    if context.pr_number is not None:
        app.display_pair('Pull request', str(context.pr_number))
    if context.target_branch is not None:
        app.display_pair('Target branch', context.target_branch)
    app.display_pair('Workflow', f'{context.workflow} @ {context.workflow_ref}')

    total = sum(batch.jobs_count for batch in batches)
    app.display_pair('Batches', f'{len(batches)} ({total} jobs)')
    for batch in batches:
        count = len(batch.integrations)
        app.display(f'  {batch.batch_id}: {batch.jobs_count} jobs, {count} integration{"" if count == 1 else "s"}')
        app.display(f'    {summarize(batch.integrations)}')


def summarize(names: list[str]) -> str:
    """The first few names and a count of the rest: a repository-wide run has hundreds."""
    limit = 10
    if len(names) <= limit:
        return ', '.join(names)
    return f'{", ".join(names[:limit])}, and {len(names) - limit} more'
