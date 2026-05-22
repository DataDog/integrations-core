# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Monitor dispatched Agent test workflow runs."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text
from rich.tree import Tree

from ddev.cli.release.test_agent.dispatch import REPO_NAME, REPO_OWNER, DispatchedWorkflow
from ddev.utils.github_async import async_github_client

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.cli.terminal import Terminal
    from ddev.utils.github_async.client import AsyncGitHubClient

SUCCESS_MARK = '\u2713'
ERROR_MARK = '\u2717'
RUNNING_SPINNER = 'dots'


@dataclass(frozen=True)
class JobState:
    """Current state for one GitHub Actions job."""

    name: str
    status: str
    conclusion: str | None
    html_url: str | None

    @property
    def is_failure(self) -> bool:
        return self.status == 'completed' and self.conclusion not in {'success', 'skipped'}


@dataclass(frozen=True)
class WorkflowState:
    """Current state for one GitHub Actions workflow run."""

    label: str
    run_id: int
    status: str
    conclusion: str | None
    html_url: str
    jobs: list[JobState]

    @property
    def is_complete(self) -> bool:
        return self.status == 'completed'

    @property
    def failed_jobs(self) -> list[JobState]:
        return [job for job in self.jobs if job.is_failure]


@dataclass(frozen=True)
class MonitorState:
    """Current state for all monitored workflow runs."""

    workflows: list[WorkflowState]

    @property
    def is_complete(self) -> bool:
        return all(workflow.is_complete for workflow in self.workflows)


@dataclass(frozen=True)
class JobCounts:
    """Aggregate job counts for one workflow."""

    waiting: int = 0
    running: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0


async def collect_monitor_state(
    client: AsyncGitHubClient,
    workflows: Sequence[DispatchedWorkflow],
) -> MonitorState:
    """Fetch current workflow and job state for every dispatched workflow."""
    states = await asyncio.gather(*(collect_workflow_state(client, workflow) for workflow in workflows))
    return MonitorState(list(states))


async def collect_workflow_state(client: AsyncGitHubClient, workflow: DispatchedWorkflow) -> WorkflowState:
    """Fetch current workflow and job state for one dispatched workflow."""
    run_response = await client.get_workflow_run(REPO_OWNER, REPO_NAME, workflow.run_id)
    run = run_response.data
    jobs: list[JobState] = []

    async for page in client.list_workflow_run_jobs(REPO_OWNER, REPO_NAME, workflow.run_id, per_page=100):
        jobs.extend(
            JobState(
                name=job.name,
                status=job.status,
                conclusion=job.conclusion,
                html_url=job.html_url,
            )
            for job in page.data.jobs
        )

    return WorkflowState(
        label=workflow.label,
        run_id=workflow.run_id,
        status=run.status,
        conclusion=run.conclusion,
        html_url=run.html_url or workflow.html_url,
        jobs=jobs,
    )


def monitor_dispatched_workflows(
    app: Application,
    token: str,
    *,
    ref: str,
    workflows: Sequence[DispatchedWorkflow],
    poll_interval: float = 10.0,
) -> None:
    """Monitor dispatched workflows until GitHub marks every run completed."""

    async def run() -> None:
        async with async_github_client(token=token) as client:
            await monitor_workflows(app, client, ref=ref, workflows=workflows, poll_interval=poll_interval)

    asyncio.run(run())


async def monitor_workflows(
    app: Application,
    client: AsyncGitHubClient,
    *,
    ref: str,
    workflows: Sequence[DispatchedWorkflow],
    poll_interval: float = 10.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Render a live workflow monitor until every workflow run completes."""
    state = MonitorState(
        [
            WorkflowState(workflow.label, workflow.run_id, 'queued', None, workflow.html_url, [])
            for workflow in workflows
        ]
    )
    completed_state: MonitorState | None = None

    if not (app.interactive and app.console.is_terminal):
        while True:
            state = await collect_monitor_state(client, workflows)
            app.output(render_monitor_panel(app, ref=ref, poll_interval=poll_interval, state=state), stderr=True)
            if state.is_complete:
                return
            await sleep(poll_interval)

    original_stderr = app.console.stderr
    app.console.stderr = True
    try:
        with Live(
            render_monitor_panel(app, ref=ref, poll_interval=poll_interval, state=state),
            console=app.console,
            auto_refresh=True,
            refresh_per_second=10,
            redirect_stderr=False,
            redirect_stdout=False,
            transient=True,
            vertical_overflow='crop',
        ) as live:
            while True:
                state = await collect_monitor_state(client, workflows)
                live.update(render_monitor_panel(app, ref=ref, poll_interval=poll_interval, state=state), refresh=True)
                if state.is_complete:
                    completed_state = state
                    break
                await sleep(poll_interval)
    finally:
        app.console.stderr = original_stderr

    if completed_state is not None:
        app.output(render_monitor_panel(app, ref=ref, poll_interval=poll_interval, state=completed_state), stderr=True)


def render_monitor_panel(
    terminal: Terminal,
    *,
    ref: str,
    poll_interval: float,
    state: MonitorState,
) -> Panel:
    """Render workflow and job state as a rich panel."""
    header = terminal.labeled_lines(
        [
            ('Ref', ref),
            ('Polling', f'every {poll_interval:g}s'),
        ]
    )
    tree = Tree('Workflows', style='bold')
    for workflow in state.workflows:
        workflow_branch = tree.add(_workflow_label(workflow))
        if workflow.jobs:
            workflow_branch.add(_job_summary_label(workflow.jobs))
            if failed_jobs := workflow.failed_jobs:
                failures_branch = workflow_branch.add(Text('Failures', style='bold red'))
                for job in sorted(failed_jobs, key=lambda failed_job: failed_job.name.lower()):
                    failures_branch.add(_failed_job_label(job))
        elif workflow.is_complete:
            workflow_branch.add(Text('No jobs reported', style='bold yellow'))
        else:
            workflow_branch.add(Spinner(RUNNING_SPINNER, text='Waiting for jobs', style='bold magenta'))

    return Panel(
        Group(header, Text(''), tree),
        title='Agent test workflow monitor',
        title_align='left',
        border_style='cyan',
    )


def _workflow_label(workflow: WorkflowState) -> Text | Spinner:
    if not workflow.is_complete:
        return Spinner(RUNNING_SPINNER, text=f'{workflow.label}  {workflow.html_url}', style='bold magenta')

    success = workflow.conclusion == 'success'
    mark = SUCCESS_MARK if success else ERROR_MARK
    style = 'bold cyan' if success else 'bold red'
    label = Text(f'{mark} ', style=style)
    label.append(workflow.label, style=f'{style} link {workflow.html_url}')
    label.append('  ')
    label.append(workflow.html_url, style=f'link {workflow.html_url}')
    return label


def _job_summary_label(jobs: Sequence[JobState]) -> Text:
    counts = _count_jobs(jobs)
    label = Text()
    label.append('Waiting: ', style='bold')
    label.append(str(counts.waiting), style='bold yellow')
    label.append('  Running: ', style='bold')
    label.append(str(counts.running), style='bold magenta')
    label.append('  Succeeded: ', style='bold')
    label.append(str(counts.succeeded), style='bold cyan')
    label.append('  Failed: ', style='bold')
    label.append(str(counts.failed), style='bold red' if counts.failed else 'bold')
    label.append('  Skipped: ', style='bold')
    label.append(str(counts.skipped), style='dim' if counts.skipped else 'bold')
    return label


def _failed_job_label(job: JobState) -> Text:
    label = Text(f'{ERROR_MARK} ', style='bold red')
    if job.html_url is None:
        label.append(job.name, style='bold red')
        return label

    label.append(job.name, style=f'bold red link {job.html_url}')
    label.append('  ')
    label.append(job.html_url, style=f'red link {job.html_url}')
    return label


def _count_jobs(jobs: Sequence[JobState]) -> JobCounts:
    waiting = 0
    running = 0
    succeeded = 0
    failed = 0
    skipped = 0
    for job in jobs:
        if job.status != 'completed':
            if job.status == 'in_progress':
                running += 1
            else:
                waiting += 1
        elif job.conclusion == 'success':
            succeeded += 1
        elif job.conclusion == 'skipped':
            skipped += 1
        else:
            failed += 1
    return JobCounts(waiting=waiting, running=running, succeeded=succeeded, failed=failed, skipped=skipped)
