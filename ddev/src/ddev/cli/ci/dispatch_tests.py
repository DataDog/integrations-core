# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The `ddev ci dispatch-tests` command: the Dispatcher's entry point."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import click

from ddev.cli.ci.dispatch_run import PullRequestResolver, resolve_run

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.cli.ci.tests.batching.units import EnvironmentProvider
    from ddev.cli.ci.tests.dispatcher import Dispatcher, DispatcherContext
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.cli.ci.tests.messages import TestBatch
    from ddev.monitoring import ComponentMonitor, MonitoringRuntime
    from ddev.monitoring.datadog import DatadogLogHandler
    from ddev.utils.git import ChangedFile

DEFAULT_OUTPUT_DIRECTORY = ".dispatcher"

EXPORT_DRAIN_TIMEOUT = 10.0


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
    default=None,
    help='Where the run writes what it produces: artifacts, coverage and test results.',
)
@click.option('--dry-run', is_flag=True, help='Show the plan without dispatching jobs. PR runs still read GitHub.')
@click.option(
    '--log-level',
    type=click.Choice(('debug', 'info', 'warning', 'error'), case_sensitive=False),
    default='info',
    show_default=True,
    help='Minimum severity emitted to console and Datadog.',
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
    output_dir: str | None,
    dry_run: bool,
    log_level: str,
) -> None:
    """Plan the tests a commit requires, run them as parallel batches of GitHub Actions jobs, and
    report the result to the pull request and to the run summary.

    Pass `--pr` when the number is known, with `--pr-head-sha` to reject superseded revisions.
    Otherwise use the head SHA, repository and branch from `workflow_run` to resolve the PR.
    Its base and diff come from GitHub; `--commit` instead compares a default-branch commit
    with its first parent using local git.
    """
    from pathlib import Path

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

    caller_tags = tuple(tags.split()) if tags else ()

    output_level = getattr(logging, log_level.upper())

    console_handler = AppLoggingHandler(app)
    console_handler.setLevel(output_level)
    console_handler.setFormatter(console_formatter(hidden_fields=PROTECTED_RUN_FIELDS | set(tag_fields(caller_tags))))
    monitoring = MonitoringRuntime(console_handler=console_handler, protected_fields=PROTECTED_RUN_FIELDS)
    monitoring.set_run_fields(**{**tag_fields(caller_tags), 'repo': f'{owner}/{repo}'})
    datadog_handler = build_datadog_log_handler(app, monitoring, level=output_level)
    try:
        started = time.monotonic()
        monitor = monitoring.component('dispatcher')
        monitor.logger.info(
            'Dispatcher invocation started',
            context=tag_fields(caller_tags).get('context'),
            all_targets=all_targets,
            dry_run=dry_run,
            minimum_base_package=minimum_base_package,
            tags=list(caller_tags) if caller_tags else None,
        )

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
        )

        # One INFO line per request would bury the Dispatcher's own progress.
        logging.getLogger('httpx').setLevel(logging.WARNING)

        config = DispatcherConfig.from_repo_config(app.repo.config)

        run = resolve_run(
            app,
            pr_resolver=pr_resolver,
            commit=commit,
            token=token,
            all_targets=all_targets,
            monitor=monitoring.component('resolution'),
        )
        if run is None:
            run_summary(monitor, started, outcome='no-op')
            return

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
            monitor.logger.info('Nothing to test', reason='the plan covers no target')
            run_summary(monitor, started, outcome='no-op')
            app.display_info('No affected target to test.')
            return

        display_plan(app, context, batches)
        if dry_run:
            monitor.logger.info('Dry run: nothing was dispatched')
            run_summary(
                monitor,
                started,
                outcome='dry-run',
                batch_count=len(batches),
                job_count=sum(batch.jobs_count for batch in batches),
            )
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
            monitoring=monitoring,
        )
        # A fatal processor or hook failure leaves the bus by raising out of `run`. `on_finalize` has
        # already published whatever it knew by then, so a message is more use here than a traceback.
        try:
            dispatcher.run()
        except Exception as error:
            run_summary(monitor, started, outcome='failed', dispatcher=dispatcher, error=str(error))
            app.abort(f'Dispatcher execution failed: {error}')

        outcome = dispatcher.outcome
        if outcome is None or not outcome.successful:
            run_summary(
                monitor,
                started,
                outcome='cancelled' if dispatcher.cancelled else 'failed',
                dispatcher=dispatcher,
            )
            app.abort('Dispatcher tests failed.')

        run_summary(monitor, started, outcome='passed', dispatcher=dispatcher)
        app.display_success('Dispatcher tests passed.')
    finally:
        monitoring.close()
        if datadog_handler is not None:
            # The runtime is closed first, so nothing is emitted while the handler drains.
            datadog_handler.close(EXPORT_DRAIN_TIMEOUT)


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
    needs_token = is_pr_run or not dry_run
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
    monitor: ComponentMonitor,
) -> list[TestBatch]:
    """Build the batches this run must execute, aborting with a readable message on a bad plan.

    `--all` plans every eligible target, so it needs no comparison and `changed_files` is None.
    """
    from ddev.cli.ci.tests.batching.build import build_test_batches
    from ddev.cli.ci.tests.batching.exceptions import PlanningError
    from ddev.cli.ci.tests.batching.targets import all_target_rules

    rules = all_target_rules() if all_targets else None
    monitor.logger.info(
        'Planning started',
        all_targets=all_targets,
        changed_file_count=len(changed_files) if changed_files is not None else None,
        minimum_base_package=minimum_base_package,
    )

    try:
        batches = build_test_batches(
            app.repo,
            changed_files or [],
            environment_provider=environment_provider,
            config=config.batching,
            rules=rules,
            minimum_base_package=minimum_base_package,
            monitor=monitor,
        )
    except PlanningError as error:
        monitor.logger.error('Planning failed', error=str(error))
        app.abort(f'Could not build a test plan: {error}')

    monitor.logger.info(
        'Planning completed',
        plan_batch_count=len(batches),
        plan_job_count=sum(batch.jobs_count for batch in batches),
        plan_integration_count=len({integration for batch in batches for integration in batch.integrations}),
    )
    for batch in batches:
        monitor.logger.info(
            'Planned batch',
            batch_id=batch.batch_id,
            batch_job_count=batch.jobs_count,
            batch_integration_count=len(batch.integrations),
            batch_integrations=batch.integrations,
        )

    return batches


def build_datadog_log_handler(
    app: Application, monitoring: MonitoringRuntime, *, level: int
) -> DatadogLogHandler | None:
    """Attach Dispatcher-formatted Datadog delivery when the organization has an API key."""
    from ddev.cli.ci.tests.dispatcher_logging import dispatcher_datadog_formatter
    from ddev.monitoring.datadog import DatadogLogHandler

    api_key = app.config.org.config.get('api_key')
    if not api_key:
        return None
    try:
        handler = DatadogLogHandler(
            api_key=api_key,
            site=app.config.org.config.get('site', 'datadoghq.com'),
            diagnostics=app.display_warning,
            level=level,
        )
    except Exception as error:
        app.display_warning(f'Datadog log delivery is unavailable: {type(error).__name__}: {error}')
        return None
    handler.setFormatter(dispatcher_datadog_formatter())
    monitoring.add_log_handler(handler)
    return handler


def run_summary(
    monitor: ComponentMonitor,
    started: float,
    *,
    outcome: str,
    dispatcher: Dispatcher | None = None,
    batch_count: int = 0,
    job_count: int = 0,
    error: str | None = None,
) -> None:
    """Emit one terminal record for both executed and valid no-op runs."""
    progress = dispatcher.outcome.progress if dispatcher is not None and dispatcher.outcome is not None else None
    if progress is not None:
        batch_count = len(progress.batches)
        job_count = sum(len(batch.jobs_progress) for batch in progress.batches)
    cancelled = dispatcher.cancelled if dispatcher is not None else False
    final_report_published = (
        dispatcher.outcome.final_report_published
        if dispatcher is not None and dispatcher.outcome is not None
        else False
    )
    log = monitor.logger.error if outcome == 'failed' else monitor.logger.warning if cancelled else monitor.logger.info
    log(
        'Dispatcher run finished',
        outcome=outcome,
        cancelled=cancelled,
        batch_count=batch_count,
        job_count=job_count,
        final_report_published=final_report_published,
        elapsed_seconds=round(time.monotonic() - started, 3),
        error=error,
    )


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
