# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The `ddev ci dispatch-tests` command: the Dispatcher's entry point."""

from __future__ import annotations

import asyncio
import logging
import time
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
from ddev.cli.ci.tests.execution_metrics import ExecutionOutcome

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.application import Application
    from ddev.cli.ci.dispatch_run import ResolvedRun
    from ddev.cli.ci.tests.batching.units import EnvironmentProvider
    from ddev.cli.ci.tests.dispatcher import Dispatcher
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.cli.ci.tests.messages import TestBatch
    from ddev.monitoring import ComponentMonitor, MonitoringRuntime
    from ddev.monitoring.datadog import DatadogLogHandler
    from ddev.monitoring.datadog_metrics import DatadogMetricsSink
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
    help='Additional run tags, separated by spaces. Service ownership and resolved identity cannot be overridden.',
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
    '--log-level',
    type=click.Choice(('debug', 'info', 'warning', 'error'), case_sensitive=False),
    default='info',
    show_default=True,
    help='Minimum severity emitted to console and Datadog.',
)
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
    log_level: str,
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
    from ddev.cli.ci.tests.batching.exceptions import PlanningError
    from ddev.cli.ci.tests.batching.hatch_environments import HatchEnvironmentProvider
    from ddev.cli.ci.tests.dispatcher import build_dispatcher
    from ddev.cli.ci.tests.dispatcher_attributes import (
        BASE_FIELDS,
        PROTECTED_RUN_FIELDS,
        UNRESOLVED_RUN_FIELDS,
        console_hidden_fields,
        metric_tag_mapping,
        repository_fields,
        run_fields,
        tag_fields,
    )
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.cli.ci.tests.dispatcher_logging import ci_pipeline_id
    from ddev.monitoring import MonitoringRuntime, console_formatter

    tested_repository = f'{owner}/{repo}'

    caller_tags = tuple(tags.split()) if tags else ()
    output_level = getattr(logging, log_level.upper())

    console_handler = AppLoggingHandler(app)
    console_handler.setLevel(output_level)
    console_handler.setFormatter(
        console_formatter(hidden_fields=console_hidden_fields() | PROTECTED_RUN_FIELDS | set(tag_fields(caller_tags)))
    )
    # `--dry-run` and `--resolve-only` dispatch nothing, so they report no metrics either.
    metrics_sink = None if (dry_run or resolve_only) else build_datadog_metrics_sink(app)
    monitoring = MonitoringRuntime(
        console_handler=console_handler,
        metrics_sink=metrics_sink,
        metrics_tag_projector=metric_tag_mapping,
        protected_fields=PROTECTED_RUN_FIELDS,
        base_fields={
            **{name: value for name, value in tag_fields(caller_tags).items() if name not in PROTECTED_RUN_FIELDS},
            **BASE_FIELDS,
            **repository_fields(owner, repo),
            **UNRESOLVED_RUN_FIELDS,
            # Bind even when absent, so caller tags and scopes cannot forge the workflow's identity.
            'ci_pipeline_id': ci_pipeline_id(),
        },
    )
    datadog_handler = attach_datadog_log_handler(app, monitoring, level=output_level)
    started = time.monotonic()
    monitor = monitoring.component('dispatcher')
    outcome: ExecutionOutcome | None = None
    dispatcher: Dispatcher | None = None
    summary_error: str | None = None
    batch_count = job_count = 0
    try:
        monitor.logger.info(
            'Dispatcher invocation started',
            all_targets=all_targets,
            dry_run=dry_run,
            minimum_base_package=minimum_base_package,
            tags=list(caller_tags) if caller_tags else None,
        )

        # One INFO line per request would bury the Dispatcher's own progress.
        logging.getLogger('httpx').setLevel(logging.WARNING)

        base_path = app.repo.path / output_dir

        run: ResolvedRun | None
        if run_manifest is not None:
            # The manifest is the whole run: its identity is read, not recalculated, and a
            # manifest the caller explicitly supplied is not rewritten either.
            run = load_run_manifest(app, Path(run_manifest), repository=tested_repository)
            all_targets = run.all_targets
        else:
            run = resolve_run(
                app,
                repository=tested_repository,
                pr_resolver=pr_resolver,
                commit=commit,
                token=token,
                all_targets=all_targets,
                monitor=monitoring.component('resolution'),
            )
            if run is None:
                outcome = ExecutionOutcome.NO_OP
                return

        # Bind before setup can fail, so terminal records retain the resolved identity.
        monitoring.set_run_fields(**run_fields(run, tags=caller_tags))

        if run_manifest is None:
            write_run_manifest(base_path, run=run)
            if resolve_only:
                outcome = ExecutionOutcome.RESOLVED
                app.display_success(f'Resolved run written to {base_path / RUN_MANIFEST_NAME}.')
                return

        changed_files = changes_for_run(app, run=run, monitor=monitoring.component('resolution'))

        # Read after resolution: `--resolve-only` stops before the run needs planning configuration.
        config = DispatcherConfig.from_repo_config(app.repo.config)
        overrides = {'workflow': workflow, 'workflow_ref': workflow_ref}
        config = config.model_copy(update={name: value for name, value in overrides.items() if value})

        try:
            batches = build_plan(
                app,
                config=config,
                changed_files=changed_files,
                all_targets=all_targets,
                minimum_base_package=minimum_base_package,
                environment_provider=HatchEnvironmentProvider(default_python_version=config.default_python_version),
                monitor=monitoring.component('planner'),
            )
        except PlanningError as error:
            outcome = ExecutionOutcome.PLANNING_FAILED
            summary_error = str(error)
            app.abort(f'Could not build a test plan: {error}')

        if not batches:
            monitor.logger.info('Nothing to test', reason='the plan covers no target')
            outcome = ExecutionOutcome.NO_OP
            return

        display_plan(app, run, config, batches, tags=caller_tags, pytest_args=pytest_args or '')
        if dry_run:
            monitor.logger.info('Dry run: nothing was dispatched')
            outcome = ExecutionOutcome.DRY_RUN
            batch_count = len(batches)
            job_count = sum(batch.jobs_count for batch in batches)
            return

        dispatcher = build_dispatcher(
            batches=batches,
            run=run,
            config=config,
            token=token,
            artifacts_path=base_path / 'artifacts',
            output_path=base_path / 'results',
            monitoring=monitoring,
            tags=caller_tags,
            pytest_args=pytest_args or '',
        )
        # A fatal processor or hook failure leaves the bus by raising out of `run`. `on_finalize` has
        # already published whatever it knew by then, so a message is more use here than a traceback.
        try:
            dispatcher.run()
        except Exception as error:
            outcome = ExecutionOutcome.FAILED
            summary_error = str(error)
            app.abort(f'Dispatcher execution failed: {error}')

        dispatcher_outcome = dispatcher.outcome
        if dispatcher_outcome is None or not dispatcher_outcome.successful:
            outcome = ExecutionOutcome.CANCELLED if dispatcher.cancelled else ExecutionOutcome.FAILED
            app.abort('Dispatcher tests failed.')

        outcome = ExecutionOutcome.PASSED
    except (KeyboardInterrupt, asyncio.CancelledError):
        if outcome is None:
            outcome = ExecutionOutcome.CANCELLED
        raise
    finally:
        try:
            run_summary(
                monitor,
                started=started,
                outcome=outcome or ExecutionOutcome.FAILED,
                dispatcher=dispatcher,
                batch_count=batch_count,
                job_count=job_count,
                error=summary_error,
            )
        finally:
            monitoring.close()
            if datadog_handler is not None:
                # Close the runtime first so no event arrives while delivery drains.
                datadog_handler.close(EXPORT_DRAIN_TIMEOUT)


def build_datadog_metrics_sink(app: Application) -> DatadogMetricsSink | None:
    """Build metric delivery when the organization has an API key."""
    from ddev.monitoring.datadog_metrics import DatadogMetricsSink

    api_key = app.config.org.config.get('api_key')
    if not api_key:
        return None
    try:
        return DatadogMetricsSink(
            api_key=api_key,
            site=app.config.org.config.get('site', 'datadoghq.com'),
            namespace='agent_integrations.test_dispatcher',
            diagnostics=app.display_warning,
        )
    except Exception as error:
        app.display_warning(f'Datadog metric delivery is unavailable: {type(error).__name__}: {error}')
        return None


def attach_datadog_log_handler(
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
    *,
    started: float,
    outcome: ExecutionOutcome,
    dispatcher: Dispatcher | None = None,
    batch_count: int = 0,
    job_count: int = 0,
    error: str | None = None,
) -> None:
    """Emit one terminal record for executed and valid no-op runs."""
    dispatcher_outcome = dispatcher.outcome if dispatcher is not None else None
    progress = dispatcher_outcome.progress if dispatcher_outcome is not None else None
    if progress is not None:
        batch_count = len(progress.batches)
        job_count = sum(len(batch.jobs_progress) for batch in progress.batches)
    cancelled = outcome is ExecutionOutcome.CANCELLED or (
        dispatcher_outcome is not None and dispatcher_outcome.cancelled
    )
    final_report_published = dispatcher_outcome.final_report_published if dispatcher_outcome is not None else False
    timed_out = dispatcher_outcome is not None and dispatcher_outcome.timed_out
    elapsed = time.monotonic() - started
    if outcome not in (ExecutionOutcome.RESOLVED, ExecutionOutcome.DRY_RUN):
        metrics = monitor.metrics
        metrics.count('runs.count', 1)
        metrics.count('runs.failed', int(outcome in (ExecutionOutcome.FAILED, ExecutionOutcome.PLANNING_FAILED)))
        metrics.count('runs.planning_failed', int(outcome is ExecutionOutcome.PLANNING_FAILED))
        metrics.count('runs.cancelled', int(cancelled))
        metrics.count('runs.timed_out', int(timed_out))
        metrics.count('runs.no_op', int(outcome is ExecutionOutcome.NO_OP))
        metrics.distribution('run.duration', elapsed)
    log = (
        monitor.logger.error
        if outcome in (ExecutionOutcome.FAILED, ExecutionOutcome.PLANNING_FAILED)
        else monitor.logger.warning
        if cancelled
        else monitor.logger.info
    )
    log(
        'Dispatcher run finished',
        outcome=outcome,
        cancelled=cancelled,
        batch_count=batch_count,
        job_count=job_count,
        final_report_published=final_report_published,
        elapsed_seconds=round(elapsed, 3),
        error=error,
    )


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
    """Build the batches this run must execute, raising `PlanningError` on a bad plan.

    `--all` plans every eligible target, so it needs no comparison and `changed_files` is None.
    """
    from ddev.cli.ci.tests.batching.build import build_test_batches
    from ddev.cli.ci.tests.batching.exceptions import PlanningError
    from ddev.cli.ci.tests.batching.targets import all_target_rules
    from ddev.cli.ci.tests.dispatcher_attributes import batch_fields

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
        raise

    monitor.logger.info(
        'Planning completed',
        plan_batch_count=len(batches),
        plan_job_count=sum(batch.jobs_count for batch in batches),
        plan_integration_count=len({integration for batch in batches for integration in batch.integrations}),
    )
    for batch in batches:
        monitor.logger.info(
            'Planned batch %s (%s %s)',
            batch.batch_id,
            batch.jobs_count,
            'job' if batch.jobs_count == 1 else 'jobs',
            **batch_fields(batch),
        )

    return batches


def display_plan(
    app: Application,
    run: ResolvedRun,
    config: DispatcherConfig,
    batches: list[TestBatch],
    *,
    tags: Sequence[str] = (),
    pytest_args: str = '',
) -> None:
    app.display_header('Dispatcher plan')
    app.display_pair('Repository', run.repository)
    app.display_pair('Head branch', run.head_branch)
    app.display_pair('Head SHA', run.head_sha)
    app.display_pair('Checkout SHA', run.checkout_sha)
    if run.pr_number is not None:
        app.display_pair('Pull request', str(run.pr_number))
    if run.base_branch is not None:
        app.display_pair('Base branch', run.base_branch)
    if run.base_sha is not None:
        app.display_pair('Base SHA', run.base_sha)
    if tags:
        app.display_pair('Tags', ' '.join(tags))
    if pytest_args:
        app.display_pair('Pytest args', pytest_args)
    app.display_pair('Workflow', f'{config.workflow} @ {config.workflow_ref}')

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
