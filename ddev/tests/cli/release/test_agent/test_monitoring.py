# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import importlib
from typing import Any

from ddev.cli.release.test_agent.monitoring import (
    DispatchedWorkflow,
    JobState,
    MonitorState,
    WorkflowState,
    collect_monitor_state,
    monitor_workflows,
    render_monitor_panel,
)
from ddev.cli.terminal import Terminal
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import WorkflowJob, WorkflowJobsList, WorkflowRun
from tests.helpers.github_async import FakeAsyncGitHubClient

monitoring_module = importlib.import_module('ddev.cli.release.test_agent.monitoring')


def test_render_monitor_panel_shows_workflow_summary() -> None:
    terminal = Terminal(verbosity=0, enable_color=False, interactive=False)
    state = MonitorState(
        workflows=[
            WorkflowState(
                label='Linux',
                run_id=1,
                status='in_progress',
                conclusion=None,
                html_url='https://github.com/DataDog/integrations-core/actions/runs/1',
                jobs=[
                    JobState(
                        name='test-agent / py3.12',
                        status='in_progress',
                        conclusion=None,
                        html_url='https://github.com/DataDog/integrations-core/actions/runs/1/job/10',
                    )
                ],
            )
        ]
    )

    with terminal.console.capture() as capture:
        terminal.console.print(render_monitor_panel(terminal, ref='7.80.x', poll_interval=30, state=state))

    output = capture.get()
    assert 'Agent test workflow monitor' in output
    assert 'Ref:     7.80.x' in output
    assert 'Polling: every 30s' in output
    assert 'Linux' in output
    assert 'Waiting: 0' in output
    assert 'Running: 1' in output
    assert 'Succeeded: 0' in output
    assert 'Failed: 0' in output
    assert 'Skipped: 0' in output


def test_render_monitor_panel_includes_failed_job_url() -> None:
    terminal = Terminal(verbosity=0, enable_color=False, interactive=False)
    job_url = 'https://github.com/DataDog/integrations-core/actions/runs/2/job/20'
    state = MonitorState(
        workflows=[
            WorkflowState(
                label='Windows',
                run_id=2,
                status='completed',
                conclusion='failure',
                html_url='https://github.com/DataDog/integrations-core/actions/runs/2',
                jobs=[
                    JobState(
                        name='test-agent-windows / py3.12',
                        status='completed',
                        conclusion='failure',
                        html_url=job_url,
                    )
                ],
            )
        ]
    )

    with terminal.console.capture() as capture:
        terminal.console.print(render_monitor_panel(terminal, ref='7.80.x', poll_interval=30, state=state))

    output = capture.get()
    assert 'Windows' in output
    assert 'Failures' in output
    assert 'test-agent-windows / py3.12' in output
    assert 'actions/runs/2/job/' in output
    assert '20' in output


def test_render_monitor_panel_counts_skipped_jobs_without_listing_them() -> None:
    terminal = Terminal(verbosity=0, enable_color=False, interactive=False)
    state = MonitorState(
        workflows=[
            WorkflowState(
                label='Linux',
                run_id=1,
                status='completed',
                conclusion='success',
                html_url='https://github.com/DataDog/integrations-core/actions/runs/1',
                jobs=[
                    JobState('successful job', 'completed', 'success', None),
                    JobState('skipped job', 'completed', 'skipped', None),
                    JobState('failed job', 'completed', 'failure', 'https://github.com/job/failed'),
                ],
            )
        ]
    )

    with terminal.console.capture() as capture:
        terminal.console.print(render_monitor_panel(terminal, ref='7.80.x', poll_interval=30, state=state))

    output = capture.get()
    assert 'Skipped: 1' in output
    assert 'Failed: 1' in output
    assert 'failed job' in output
    assert 'skipped job' not in output
    assert 'successful job' not in output


def test_monitor_state_is_complete_only_when_all_workflows_complete() -> None:
    state = MonitorState(
        workflows=[
            WorkflowState('Linux', 1, 'completed', 'success', 'https://github.com/runs/1', []),
            WorkflowState('Windows', 2, 'in_progress', None, 'https://github.com/runs/2', []),
        ]
    )

    assert not state.is_complete

    completed = MonitorState(
        workflows=[
            WorkflowState('Linux', 1, 'completed', 'success', 'https://github.com/runs/1', []),
            WorkflowState('Windows', 2, 'completed', 'failure', 'https://github.com/runs/2', []),
        ]
    )

    assert completed.is_complete


def test_dispatched_workflow_has_run_metadata() -> None:
    workflow = DispatchedWorkflow(
        label='Linux',
        workflow_id='test-agent.yml',
        run_id=123,
        html_url='https://github.com/DataDog/integrations-core/actions/runs/123',
    )

    assert workflow.run_id == 123


async def test_collect_monitor_state_fetches_workflow_jobs(fake_async_github: FakeAsyncGitHubClient) -> None:
    fake_async_github.mock_response(
        'get_workflow_run',
        WorkflowRun(
            id=123,
            name='test-agent',
            status='completed',
            conclusion='failure',
            html_url='https://github.com/DataDog/integrations-core/actions/runs/123',
        ),
    )
    fake_async_github.mock_response(
        'list_workflow_run_jobs',
        WorkflowJobsList(
            total_count=1,
            jobs=[
                WorkflowJob(
                    id=456,
                    name='test-agent / py3.12',
                    status='completed',
                    conclusion='failure',
                    html_url='https://github.com/DataDog/integrations-core/actions/runs/123/job/456',
                )
            ],
        ),
    )

    state = await collect_monitor_state(
        fake_async_github,
        [
            DispatchedWorkflow(
                label='Linux',
                workflow_id='test-agent.yml',
                run_id=123,
                html_url='https://github.com/DataDog/integrations-core/actions/runs/123',
            )
        ],
    )

    assert state.is_complete
    assert state.workflows[0].conclusion == 'failure'
    assert (
        state.workflows[0].jobs[0].html_url == 'https://github.com/DataDog/integrations-core/actions/runs/123/job/456'
    )


async def test_monitor_workflows_does_not_raise_on_job_failure(fake_async_github: FakeAsyncGitHubClient) -> None:
    terminal = Terminal(verbosity=0, enable_color=False, interactive=False)
    fake_async_github.mock_response(
        'get_workflow_run',
        GitHubResponse(
            data=WorkflowRun(
                id=123,
                name='test-agent',
                status='completed',
                conclusion='failure',
                html_url='https://github.com/DataDog/integrations-core/actions/runs/123',
            ),
            headers={},
        ),
    )
    fake_async_github.mock_response(
        'list_workflow_run_jobs',
        GitHubResponse(
            data=WorkflowJobsList(
                total_count=1,
                jobs=[
                    WorkflowJob(
                        id=456,
                        name='test-agent / py3.12',
                        status='completed',
                        conclusion='failure',
                        html_url='https://github.com/DataDog/integrations-core/actions/runs/123/job/456',
                    )
                ],
            ),
            headers={},
        ),
    )

    await monitor_workflows(
        terminal,
        fake_async_github,
        ref='7.80.x',
        workflows=[
            DispatchedWorkflow(
                label='Linux',
                workflow_id='test-agent.yml',
                run_id=123,
                html_url='https://github.com/DataDog/integrations-core/actions/runs/123',
            )
        ],
        poll_interval=0,
    )


async def test_monitor_workflows_does_not_use_alternate_screen(
    fake_async_github: FakeAsyncGitHubClient, monkeypatch
) -> None:
    terminal = Terminal(verbosity=0, enable_color=True, interactive=True)
    live_kwargs: dict[str, Any] = {}

    class FakeLive:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            live_kwargs.update(kwargs)

        def __enter__(self) -> FakeLive:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def update(self, *args: Any, **kwargs: Any) -> None:
            pass

    monkeypatch.setattr(monitoring_module, 'Live', FakeLive)
    fake_async_github.mock_response(
        'get_workflow_run',
        GitHubResponse(
            data=WorkflowRun(
                id=123,
                name='test-agent',
                status='completed',
                conclusion='success',
                html_url='https://github.com/DataDog/integrations-core/actions/runs/123',
            ),
            headers={},
        ),
    )
    fake_async_github.mock_response(
        'list_workflow_run_jobs',
        GitHubResponse(data=WorkflowJobsList(total_count=0, jobs=[]), headers={}),
    )

    await monitor_workflows(
        terminal,
        fake_async_github,
        ref='7.80.x',
        workflows=[
            DispatchedWorkflow(
                label='Linux',
                workflow_id='test-agent.yml',
                run_id=123,
                html_url='https://github.com/DataDog/integrations-core/actions/runs/123',
            )
        ],
        poll_interval=0,
    )

    assert live_kwargs.get('screen') is not True
    assert live_kwargs['auto_refresh'] is True
    assert live_kwargs['refresh_per_second'] == 10
    assert live_kwargs['vertical_overflow'] == 'crop'
