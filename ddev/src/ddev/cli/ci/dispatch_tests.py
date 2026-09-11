# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The `ddev ci dispatch-tests` command: the Dispatcher's entry point."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import click

from ddev.cli.ci.dispatch_run import (
    RUN_MANIFEST_NAME,
    PullRequestResolver,
    load_run_manifest,
    resolve_run,
    write_run_manifest,
)

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.cli.ci.tests.batching.units import EnvironmentProvider
    from ddev.cli.ci.tests.dispatcher import DispatcherContext
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.cli.ci.tests.messages import TestBatch
    from ddev.monitoring import ComponentMonitor
    from ddev.utils.git import ChangedFile

DEFAULT_OUTPUT_DIRECTORY = ".dispatcher"


@click.command(short_help='Run the Dispatcher to test a commit as parallel batches')
@click.pass_obj
@click.option(
    '--pr',
    'pull_request',
    metavar='PR_NUMBER_OR_URL',
    default=None,
    help='PR number or URL. Supplied head/base options constrain this PR; otherwise its context comes from GitHub.',
)
@click.option(
    '--pr-head-sha',
    default=None,
    metavar='SHA',
    help='Expected PR head commit. Required for head-based PR lookup; use with `--pr` to skip stale revisions.',
)
@click.option(
    '--pr-head-repo',
    default=None,
    metavar='OWNER/NAME',
    help='Expected PR head repository. Required for head-based PR lookup; optional with `--pr`.',
)
@click.option(
    '--pr-head-ref',
    default=None,
    metavar='BRANCH',
    help='Expected PR head branch. Required for head-based PR lookup; optional with `--pr`.',
)
@click.option(
    '--pr-base-ref',
    default=None,
    metavar='BRANCH',
    help='Optional base branch to narrow or verify the pull request. Otherwise read from the resolved PR.',
)
@click.option(
    '--commit',
    default=None,
    metavar='SHA',
    help='Commit to compare with its first parent. Cannot be combined with PR options. Defaults to local HEAD.',
)
@click.option(
    '--tags',
    default=None,
    metavar='"KEY:VALUE ..."',
    help='Tags the run reports itself under, separated by spaces. Their meaning is the caller\'s to decide.',
)
@click.option(
    '--pytest-args',
    default=None,
    metavar='ARGS',
    help='Arguments every job appends to pytest, as one string. For example: -m "not flaky".',
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
    default=DEFAULT_OUTPUT_DIRECTORY,
    show_default=True,
    help='Where the run writes what it produces: artifacts, coverage and test results.',
)
@click.option('--dry-run', is_flag=True, help='Show the plan without dispatching jobs. PR runs still read GitHub.')
@click.option(
    '--resolve-only',
    'resolve_only',
    is_flag=True,
    help='Resolve the run, write its manifest, and stop before planning or dispatching anything.',
)
@click.option(
    '--run-manifest',
    'run_manifest',
    metavar='FILE',
    default=None,
    type=click.Path(dir_okay=False),
    help='Reuse the run a `--resolve-only` invocation resolved, reading its identity and changes from FILE.',
)
def dispatch_tests(
    app: Application,
    pull_request: str | None,
    pr_head_sha: str | None,
    pr_head_repo: str | None,
    pr_head_ref: str | None,
    pr_base_ref: str | None,
    commit: str | None,
    tags: str | None,
    pytest_args: str | None,
    repository: str | None,
    all_targets: bool,
    minimum_base_package: bool,
    workflow: str | None,
    workflow_ref: str | None,
    output_dir: str,
    dry_run: bool,
    resolve_only: bool,
    run_manifest: str | None,
) -> None:
    """Plan the tests a commit requires, run them as parallel batches of GitHub Actions jobs, and
    report the result to the pull request and to the run summary.

    Pass `--pr` when the number is known, with `--pr-head-sha` to reject superseded revisions.
    Otherwise use the head SHA, repository and branch from `workflow_run` to resolve the PR.
    Its base and diff come from GitHub; `--commit` instead compares a default-branch commit
    with its first parent using local git.

    Resolution and planning can also run as two invocations: `--resolve-only` writes the resolved
    run to `<output-dir>/run.json`, and a later `--run-manifest FILE` plans and dispatches from
    that file without resolving the run again.
    """
    if resolve_only and run_manifest is not None:
        raise click.UsageError('`--resolve-only` and `--run-manifest` cannot be combined.')
    if resolve_only and dry_run:
        raise click.UsageError('`--resolve-only` stops before planning, so `--dry-run` has no effect.')
    if run_manifest is not None:
        conflicting = [
            option
            for option, present in {
                '--pr': pull_request is not None,
                '--pr-head-repo': pr_head_repo is not None,
                '--pr-head-ref': pr_head_ref is not None,
                '--pr-head-sha': pr_head_sha is not None,
                '--pr-base-ref': pr_base_ref is not None,
                '--commit': commit is not None,
                '--all': all_targets,
            }.items()
            if present
        ]
        if conflicting:
            raise click.UsageError(
                f'`--run-manifest` supplies the resolved run, '
                f'so it cannot be combined with `{"`, `".join(conflicting)}`.'
            )

    from ddev.cli.application import AppLoggingHandler
    from ddev.cli.ci.tests.batching.hatch_environments import HatchEnvironmentProvider
    from ddev.cli.ci.tests.dispatcher import (
        PROTECTED_RUN_FIELDS,
        DispatcherContext,
        build_dispatcher,
        run_fields,
        tag_fields,
    )
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.monitoring import MonitoringRuntime, console_formatter
    from ddev.utils.github import resolve_owner_repo

    owner, repo = resolve_owner_repo(app, repository)
    tested_repository = f'{owner}/{repo}'

    caller_tags = tuple(tags.split()) if tags else ()

    console_handler = AppLoggingHandler(app)
    console_handler.setFormatter(console_formatter(hidden_fields=PROTECTED_RUN_FIELDS | set(tag_fields(caller_tags))))
    monitoring = MonitoringRuntime(console_handler=console_handler, protected_fields=PROTECTED_RUN_FIELDS)
    try:
        monitoring.set_run_fields(**{**tag_fields(caller_tags), 'repo': f'{owner}/{repo}'})

        pr_resolver, token = validate_options(
            app,
            owner=owner,
            repo=repo,
            pull_request=pull_request,
            pr_head_sha=pr_head_sha,
            pr_head_repo=pr_head_repo,
            pr_head_ref=pr_head_ref,
            pr_base_ref=pr_base_ref,
            commit=commit,
            dry_run=dry_run,
            resolve_only=resolve_only,
        )

        # One INFO line per request would bury the Dispatcher's own progress.
        logging.getLogger('httpx').setLevel(logging.WARNING)

        base_path = app.repo.path / output_dir

        if run_manifest is not None:
            # The manifest is the whole run: its identity and changes are read, not recalculated,
            # and a manifest the caller explicitly supplied is not rewritten either.
            run = load_run_manifest(app, Path(run_manifest), repository=tested_repository)
            # A null `changed_files` is how a manifest says the run covers every target.
            all_targets = run.changed_files is None
        else:
            resolved = resolve_run(
                app,
                repository=tested_repository,
                pr_resolver=pr_resolver,
                commit=commit,
                token=token,
                all_targets=all_targets,
                monitor=monitoring.component('resolution'),
            )
            if resolved is None:
                return

            run = resolved
            write_run_manifest(base_path, run=run)
            if resolve_only:
                app.display_success(f'Resolved run written to {base_path / RUN_MANIFEST_NAME}.')
                return

        # Read after resolution: `--resolve-only` stops before the run needs planning configuration.
        config = DispatcherConfig.from_repo_config(app.repo.config)

        context = DispatcherContext(
            owner=owner,
            repo=repo,
            tags=caller_tags,
            pytest_args=pytest_args or '',
            checkout_sha=run.checkout_sha,
            base_sha=run.base_sha,
            branch=run.branch,
            is_fork=run.is_fork,
            workflow=workflow or config.workflow,
            workflow_ref=workflow_ref or config.workflow_ref,
            target_branch=run.target_branch,
            pr_number=run.pr_number,
        )

        # Resolved identity binds before planning, so a bad plan is still reported on its own run.
        monitoring.set_run_fields(**run_fields(context))

        batches = build_plan(
            app,
            config=config,
            changed_files=run.changed_files,
            all_targets=all_targets,
            minimum_base_package=minimum_base_package,
            environment_provider=HatchEnvironmentProvider(default_python_version=config.default_python_version),
            monitor=monitoring.component('planner'),
        )
        if not batches:
            app.display_info('No affected target to test.')
            return

        display_plan(app, context, batches)
        if dry_run:
            app.display_info('Dry run: nothing was dispatched.')
            return

        dispatcher = build_dispatcher(
            batches=batches,
            context=context,
            config=config,
            token=token,
            artifacts_path=base_path / 'artifacts',
            output_path=base_path / 'results',
            run_logger=app.logger,
            monitoring=monitoring,
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
    finally:
        monitoring.close()


def validate_options(
    app: Application,
    *,
    owner: str,
    repo: str,
    pull_request: str | None,
    pr_head_sha: str | None,
    pr_head_repo: str | None,
    pr_head_ref: str | None,
    pr_base_ref: str | None,
    commit: str | None,
    dry_run: bool,
    resolve_only: bool,
) -> tuple[PullRequestResolver | None, str]:
    """Validate run selection and authentication, returning a PR resolver when needed."""
    from ddev.utils.github import parse_pull_request_reference

    pr_options = {
        '--pr': pull_request,
        '--pr-head-repo': pr_head_repo,
        '--pr-head-ref': pr_head_ref,
        '--pr-head-sha': pr_head_sha,
        '--pr-base-ref': pr_base_ref,
    }
    is_pr_run = any(value is not None for value in pr_options.values())
    if commit is not None and is_pr_run:
        raise click.UsageError('`--commit` cannot be combined with PR options.')

    token = app.config.github.token
    # A resolve-only run stops before dispatch, so only pull request resolution can need a token.
    needs_token = is_pr_run or (not dry_run and not resolve_only)
    if needs_token and not token:
        app.abort('A GitHub token is required. Set `github.token` in your ddev config.')
    if not is_pr_run:
        return None, token

    for option, value in pr_options.items():
        if value == '':
            raise click.UsageError(f'`{option}` must not be empty.')

    number = None
    if pull_request is not None:
        number = parse_pull_request_reference(pull_request)
        if number is None:
            raise click.UsageError(f'`{pull_request}` is neither a pull request number nor a pull request URL.')
    elif not all((pr_head_repo, pr_head_ref, pr_head_sha)):
        raise click.UsageError('Specify `--pr` or all of `--pr-head-repo`, `--pr-head-ref`, and `--pr-head-sha`.')

    if pr_head_repo is not None:
        head_owner, _, head_name = pr_head_repo.partition('/')
        if not head_owner or not head_name or '/' in head_name:
            raise click.UsageError('`--pr-head-repo` must have the form OWNER/NAME.')

    return PullRequestResolver(
        owner=owner,
        repo=repo,
        number=number,
        head_repo=pr_head_repo,
        head_ref=pr_head_ref,
        head_sha=pr_head_sha,
        base_ref=pr_base_ref,
    ), token


def build_plan(
    app: Application,
    *,
    config: DispatcherConfig,
    changed_files: list[ChangedFile] | None,
    all_targets: bool,
    minimum_base_package: bool,
    environment_provider: EnvironmentProvider,
    monitor: ComponentMonitor | None = None,
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
    if context.pytest_args:
        app.display_pair('Pytest args', context.pytest_args)
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
