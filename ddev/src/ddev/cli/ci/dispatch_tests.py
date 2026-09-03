# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The `ddev ci dispatch-tests` command: the Dispatcher's entry point."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.cli.ci.tests.batching.units import EnvironmentProvider
    from ddev.cli.ci.tests.dispatcher import DispatcherContext
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.cli.ci.tests.messages import TestBatch
    from ddev.utils.git import ChangedFile
    from ddev.utils.github_async import AsyncGitHubClient

DEFAULT_OUTPUT_DIRECTORY = ".dispatcher"


@click.command(short_help='Run the Dispatcher to test a commit as parallel batches')
@click.pass_obj
@click.option(
    '--pr',
    'pull_request',
    metavar='PR_NUMBER_OR_URL',
    default=None,
    help='Pull request to test, as a number or a URL. Everything else about the run is read from GitHub.',
)
@click.option(
    '--pr-head-sha',
    default=None,
    metavar='SHA',
    help='Head commit of the pull request to test, resolved to its pull request. What `workflow_run` provides.',
)
@click.option(
    '--pr-base-ref',
    default=None,
    metavar='BRANCH',
    help='Base branch of the pull request, when a head commit heads more than one.',
)
@click.option(
    '--commit',
    default=None,
    metavar='SHA',
    help='Commit on the default branch to test, compared with its first parent. Defaults to the local HEAD.',
)
@click.option(
    '--tags',
    default=None,
    metavar='"KEY:VALUE ..."',
    help='Tags the run reports itself under, separated by spaces. Their meaning is the caller\'s to decide.',
)
@click.option('--repo', 'repository', default=None, metavar='OWNER/NAME', help='Repository to dispatch against.')
@click.option('--all', 'all_targets', is_flag=True, help='Test every eligible target instead of the affected ones.')
@click.option(
    '--minimum-base-package',
    is_flag=True,
    help='Also test every job against the oldest supported base package, as a second job per target.',
)
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
    pr_head_sha: str | None,
    pr_base_ref: str | None,
    commit: str | None,
    tags: str | None,
    repository: str | None,
    all_targets: bool,
    minimum_base_package: bool,
    workflow: str | None,
    workflow_ref: str | None,
    output_dir: str | None,
    dry_run: bool,
) -> None:
    """Plan the tests a commit requires, run them as parallel batches of GitHub Actions jobs, and
    report the result to the pull request and to the run summary.

    Which commit to test is the only thing that has to be said. `--pr` and `--pr-head-sha` name a
    pull request, whose branch, commits and diff are then read from GitHub; `--commit` names a
    commit on the default branch, compared with its first parent using local git.
    """
    import logging
    from pathlib import Path

    from ddev.cli.ci.tests.batching.build import HatchEnvironmentProvider
    from ddev.cli.ci.tests.dispatcher import DispatcherContext, build_dispatcher
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.utils.github import resolve_owner_repo

    requested_pr, token = validate_options(
        app,
        pull_request=pull_request,
        pr_head_sha=pr_head_sha,
        pr_base_ref=pr_base_ref,
        commit=commit,
        dry_run=dry_run,
    )

    # One INFO line per request would bury the Dispatcher's own progress.
    logging.getLogger('httpx').setLevel(logging.WARNING)

    config = DispatcherConfig.from_repo_config(app.repo.config)
    owner, repo = resolve_owner_repo(app, repository)

    run = resolve_run(
        app,
        owner=owner,
        repo=repo,
        requested_pr=requested_pr,
        pr_head_sha=pr_head_sha,
        pr_base_ref=pr_base_ref,
        commit=commit,
        token=token,
        all_targets=all_targets,
    )
    if run is None:
        return

    batches = build_plan(
        app,
        config=config,
        changed_files=run.changed_files,
        all_targets=all_targets,
        minimum_base_package=minimum_base_package,
        environment_provider=HatchEnvironmentProvider(app.platform, config.default_python_version),
    )
    if not batches:
        app.display_info('No affected target to test.')
        return

    context = DispatcherContext(
        owner=owner,
        repo=repo,
        tags=tuple(tags.split()) if tags else (),
        checkout_sha=run.checkout_sha,
        base_sha=run.base_sha,
        branch=run.branch,
        workflow=workflow or config.workflow,
        workflow_ref=workflow_ref or config.workflow_ref,
        target_branch=run.target_branch,
        pr_number=run.pr_number,
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
    pr_head_sha: str | None,
    pr_base_ref: str | None,
    commit: str | None,
    dry_run: bool,
) -> tuple[int | None, str]:
    """Check every input before the run does any work, and return what checking them resolved.

    That is the pull request ``--pr`` names, if any, and the GitHub token, empty when the run needs
    none. Only a dry run of a commit on the default branch needs none: it plans from local git and
    talks to nobody. A pull request needs one even for a dry run, because both its own fields and
    its diff are read from the API.
    """
    from ddev.utils.github import parse_pull_request_reference

    named = [name for name, value in (('`--pr`', pull_request), ('`--pr-head-sha`', pr_head_sha)) if value is not None]
    if commit is not None:
        named.append('`--commit`')
    if len(named) > 1:
        app.abort(f'{", ".join(named)} name different runs, so only one can be passed.')

    if pr_base_ref is not None and pr_head_sha is None:
        app.abort('`--pr-base-ref` only narrows which pull request `--pr-head-sha` resolves to.')

    requested_pr = None
    if pull_request is not None:
        requested_pr = parse_pull_request_reference(pull_request)
        if requested_pr is None:
            app.abort(f'`{pull_request}` is neither a pull request number nor a pull request URL.')

    tests_a_pull_request = pull_request is not None or pr_head_sha is not None
    token = app.config.github.token
    if not token and (tests_a_pull_request or not dry_run):
        app.abort('A GitHub token is required. Set `github.token` in your ddev config.')

    return requested_pr, token


@dataclass(frozen=True)
class ResolvedRun:
    """What the run is testing, and the changes it is responsible for.

    ``changed_files`` is None when the plan does not come from a comparison, which is `--all`.
    """

    base_sha: str
    checkout_sha: str
    branch: str
    changed_files: list[ChangedFile] | None
    pr_number: int | None = None
    target_branch: str | None = None


def resolve_run(
    app: Application,
    *,
    owner: str,
    repo: str,
    requested_pr: int | None,
    pr_head_sha: str | None,
    pr_base_ref: str | None,
    commit: str | None,
    token: str,
    all_targets: bool,
) -> ResolvedRun | None:
    """Resolve what to test, or None when a pull request is no longer open and there is nothing
    left to test or report to.
    """
    if requested_pr is not None or pr_head_sha is not None:
        return resolve_pull_request_run(
            app,
            owner=owner,
            repo=repo,
            requested_pr=requested_pr,
            pr_head_sha=pr_head_sha,
            pr_base_ref=pr_base_ref,
            token=token,
            all_targets=all_targets,
        )

    tested_commit = commit or app.repo.git.latest_commit().sha
    changed_files = None
    if not all_targets:
        from ddev.cli.ci.tests.changes import ChangeResolutionError, changes_in_commit

        try:
            changed_files = changes_in_commit(app.repo.git, tested_commit)
        except ChangeResolutionError as error:
            app.abort(str(error))

    return ResolvedRun(
        base_sha=tested_commit,
        checkout_sha=tested_commit,
        branch=app.repo.git.current_branch(),
        changed_files=changed_files,
    )


def resolve_pull_request_run(
    app: Application,
    *,
    owner: str,
    repo: str,
    requested_pr: int | None,
    pr_head_sha: str | None,
    pr_base_ref: str | None,
    token: str,
    all_targets: bool,
) -> ResolvedRun | None:
    """Read the pull request and its changed files from the API, in one client session."""
    import asyncio

    import httpx
    from pydantic import ValidationError

    from ddev.cli.ci.tests.changes import ChangeResolutionError, changes_in_pull_request
    from ddev.utils.github_async import async_github_client
    from ddev.utils.github_async.models import PullRequestState
    from ddev.utils.github_errors import GitHubAuthenticationError

    async def resolve() -> ResolvedRun | None:
        async with async_github_client(token=token) as client:
            number = requested_pr
            if number is None:
                assert pr_head_sha is not None, (
                    'A pull request run needs either a number or a head commit, and this run reported '
                    'neither. `resolve_run` dispatched to the wrong resolver.'
                )
                numbers = await resolve_pull_requests_headed_by(client, owner, repo, pr_head_sha, pr_base_ref)
                if not numbers:
                    app.display_info(
                        f'{pr_head_sha} heads no open pull request, so there is nothing to test. A commit that '
                        'later commits have superseded reports here too, since testing it would plan the newer '
                        'revision against the older one.'
                    )
                    return None
                if len(numbers) > 1:
                    listed = ', '.join(f'#{number}' for number in sorted(numbers))
                    app.abort(
                        f'{pr_head_sha} heads {len(numbers)} open pull requests ({listed}), so which one this run '
                        'is testing is ambiguous. Pass `--pr-base-ref` to name the base branch.'
                    )
                number = numbers[0]

            pull = (await client.get_pull_request(owner, repo, number)).data
            if pull.head is None or pull.base is None:
                app.abort(f'Pull request {pull.number} reports no branch references.')
            if pull.state is not PullRequestState.OPEN:
                app.display_info(f'Pull request {pull.number} is not open, so there is nothing to test.')
                return None

            changed_files = None
            if not all_targets:
                changed_files = await changes_in_pull_request(client, owner, repo, pull.number, pull.changed_files)

            return ResolvedRun(
                base_sha=pull.head.sha,
                checkout_sha=f'refs/pull/{pull.number}/merge',
                branch=pull.head.ref,
                changed_files=changed_files,
                pr_number=pull.number,
                target_branch=pull.base.ref,
            )

    try:
        return asyncio.run(resolve())
    except GitHubAuthenticationError as error:
        app.abort(str(error))
    except ChangeResolutionError as error:
        app.abort(str(error))
    except (httpx.HTTPError, ValidationError) as error:
        app.abort(f'Could not read the pull request to test: {error}')


async def resolve_pull_requests_headed_by(
    client: AsyncGitHubClient, owner: str, repo: str, head_sha: str, base_ref: str | None
) -> list[int]:
    """Return the open pull requests whose head *is* `head_sha`, narrowed to `base_ref` when given.

    A commit stays associated with its pull request after later commits land on the branch, so a
    pull request whose head has moved on is not a match: testing it would plan the newer revision
    while reporting against the older one. A fork's head resolves too, because the base repository
    keeps it as `refs/pull/<n>/head`.
    """
    from ddev.utils.github_async.models import PullRequestState

    matches = []
    async for page in client.list_commit_pulls(owner, repo, head_sha):
        for pull in page.data:
            if pull.state is not PullRequestState.OPEN or pull.head is None or pull.base is None:
                continue
            if not pull.head.sha.startswith(head_sha):
                continue
            if base_ref is not None and pull.base.ref != base_ref:
                continue
            matches.append(pull.number)

    return matches


def build_plan(
    app: Application,
    *,
    config: DispatcherConfig,
    changed_files: list[ChangedFile] | None,
    all_targets: bool,
    minimum_base_package: bool,
    environment_provider: EnvironmentProvider,
) -> list[TestBatch]:
    """Build the batches this run must execute, aborting with a readable message on a bad plan.

    `--all` plans every eligible target, so it needs no comparison and `changed_files` is None.
    """
    from ddev.cli.ci.tests.batching.build import build_test_batches
    from ddev.cli.ci.tests.batching.exceptions import PlanningError
    from ddev.cli.ci.tests.batching.targets import all_target_rules

    rules = all_target_rules() if all_targets else None

    try:
        batches = build_test_batches(
            app.repo,
            changed_files or [],
            environment_provider=environment_provider,
            config=config.batching,
            rules=rules,
            minimum_base_package=minimum_base_package,
        )
    except PlanningError as error:
        app.abort(f'Could not build a test plan: {error}')

    return batches


def display_plan(app: Application, context: DispatcherContext, batches: list[TestBatch]) -> None:
    app.display_header('Dispatcher plan')
    app.display_pair('Repository', f'{context.owner}/{context.repo}')
    app.display_pair('Branch', context.branch)
    app.display_pair('Base commit', context.base_sha)
    app.display_pair('Checkout ref', context.checkout_sha)
    if context.pr_number is not None:
        app.display_pair('Pull request', str(context.pr_number))
    if context.target_branch is not None:
        app.display_pair('Target branch', context.target_branch)
    if context.tags:
        app.display_pair('Tags', ' '.join(context.tags))
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
