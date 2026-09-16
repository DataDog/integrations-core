# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The `ddev ci dispatch-tests` command: the Dispatcher's entry point."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import click

from ddev.cli.ci.dispatch_options import validate_options
from ddev.cli.ci.dispatch_run import (
    RUN_MANIFEST_NAME,
    changes_for_run,
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
    '--pr-head-branch',
    default=None,
    metavar='BRANCH',
    help='Expected PR head branch. Required for head-based PR lookup; optional with `--pr`.',
)
@click.option(
    '--pr-base-branch',
    default=None,
    metavar='BRANCH',
    help='Optional base branch to narrow or verify the pull request. Otherwise read from the resolved PR.',
)
@click.option(
    '--commit',
    default=None,
    metavar='SHA',
    help='Checked-out commit to test, compared with its first parent. Cannot be combined with PR '
    'options. Defaults to local HEAD.',
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
    help='Reuse the run a `--resolve-only` invocation resolved, reading its identity from FILE.',
)
def dispatch_tests(
    app: Application,
    pull_request: str | None,
    pr_head_sha: str | None,
    pr_head_repo: str | None,
    pr_head_branch: str | None,
    pr_base_branch: str | None,
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
    A pull request is tested at its immutable merge commit, and its changes are computed from
    that checkout; `--commit` instead compares the checked-out commit with its first parent.

    Resolution and planning can also run as two invocations: `--resolve-only` writes the resolved
    run to `<output-dir>/run.json`, and a later `--run-manifest FILE` plans and dispatches from
    that file without resolving the run again.
    """
    from ddev.utils.github import resolve_owner_repo

    owner, repo = resolve_owner_repo(app, repository)
    pr_resolver, token = validate_options(
        app,
        owner=owner,
        repo=repo,
        pull_request=pull_request,
        pr_head_sha=pr_head_sha,
        pr_head_repo=pr_head_repo,
        pr_head_branch=pr_head_branch,
        pr_base_branch=pr_base_branch,
        commit=commit,
        all_targets=all_targets,
        dry_run=dry_run,
        resolve_only=resolve_only,
        run_manifest=run_manifest,
    )

    from ddev.cli.application import AppLoggingHandler
    from ddev.cli.ci.tests.batching.hatch_environments import HatchEnvironmentProvider
    from ddev.cli.ci.tests.dispatcher import DispatcherContext, build_dispatcher
    from ddev.cli.ci.tests.dispatcher_attributes import (
        PROTECTED_RUN_FIELDS,
        repository_fields,
        run_fields,
        tag_fields,
    )
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.monitoring import MonitoringRuntime, console_formatter

    tested_repository = f'{owner}/{repo}'

    caller_tags = tuple(tags.split()) if tags else ()

    console_handler = AppLoggingHandler(app)
    console_handler.setFormatter(console_formatter(hidden_fields=PROTECTED_RUN_FIELDS | set(tag_fields(caller_tags))))
    monitoring = MonitoringRuntime(console_handler=console_handler, protected_fields=PROTECTED_RUN_FIELDS)
    try:
        monitoring.set_run_fields(**{**tag_fields(caller_tags), **repository_fields(owner, repo)})

        # One INFO line per request would bury the Dispatcher's own progress.
        logging.getLogger('httpx').setLevel(logging.WARNING)

        base_path = app.repo.path / output_dir

        if run_manifest is not None:
            # The manifest is the whole run: its identity is read, not recalculated, and a
            # manifest the caller explicitly supplied is not rewritten either.
            run = load_run_manifest(app, Path(run_manifest), repository=tested_repository)
            all_targets = run.all_targets
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

        changed_files = changes_for_run(app, run=run)

        # Read after resolution: `--resolve-only` stops before the run needs planning configuration.
        config = DispatcherConfig.from_repo_config(app.repo.config)

        context = DispatcherContext(
            owner=owner,
            repo=repo,
            tags=caller_tags,
            pytest_args=pytest_args or '',
            checkout_sha=run.checkout_sha,
            head_sha=run.head_sha,
            head_branch=run.head_branch,
            is_fork=run.is_fork,
            workflow=workflow or config.workflow,
            workflow_ref=workflow_ref or config.workflow_ref,
            base_branch=run.base_branch,
            base_sha=run.base_sha,
            pr_number=run.pr_number,
        )

        # Resolved identity binds before planning, so a bad plan is still reported on its own run.
        monitoring.set_run_fields(**run_fields(context))

        batches = build_plan(
            app,
            config=config,
            changed_files=changed_files,
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
    app.display_pair('Head branch', context.head_branch)
    app.display_pair('Head SHA', context.head_sha)
    app.display_pair('Checkout SHA', context.checkout_sha)
    if context.pr_number is not None:
        app.display_pair('Pull request', str(context.pr_number))
    if context.base_branch is not None:
        app.display_pair('Base branch', context.base_branch)
    if context.base_sha is not None:
        app.display_pair('Base SHA', context.base_sha)
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
