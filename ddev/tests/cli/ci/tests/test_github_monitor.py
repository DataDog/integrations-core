# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the Dispatcher's GitHub request and throttle metrics and logs."""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress

import httpx
import pytest
from aiolimiter import AsyncLimiter

from ddev.cli.ci.tests.github_monitor import GitHubMonitor
from ddev.monitoring.metrics import MetricRecord
from ddev.utils.github_async import AsyncGitHubClient
from ddev.utils.github_async.retry import NO_RETRY
from ddev.utils.rate_limiting import (
    BudgetGovernor,
    BudgetSnapshot,
    InstrumentedAsyncLimiter,
    RateLimitWaitAbandoned,
    WaitEvent,
    WaitOutcome,
    WaitReason,
)
from tests.cli.ci.tests.helpers import recording_runtime
from tests.helpers.clock import FakeClock, advance_clock_on_sleep
from tests.helpers.monitoring import RecordingJsonHandler, RecordingSink

NOW = 1_700_000_000.0
RUN_PATH = '/repos/o/r/actions/runs/42'
SIGNATURE = 'sig-secret'
PIPELINE = {'ci.pipeline.id': '12345'}
RUN_PAYLOAD = {'id': 42, 'status': 'completed', 'conclusion': 'success', 'html_url': 'https://github.com/o/r/runs/42'}


def monitored(
    transport: httpx.MockTransport, rate_limiter: InstrumentedAsyncLimiter | None = None
) -> tuple[AsyncGitHubClient, GitHubMonitor, RecordingSink, RecordingJsonHandler]:
    """A client reporting through a runtime whose context holds dimensions the family must not carry.

    That includes a caller's `reason`, `status_code` and `rate_limit_resource` tags, which must never
    stand in for an emission's own.
    """
    monitoring, sink = recording_runtime()
    handler = RecordingJsonHandler()
    monitoring.add_log_handler(handler)
    monitoring.set_run_fields(
        ci_pipeline_id='12345',
        repo='o/r',
        context='pr',
        team='agent-integrations',
        reason='forged',
        status_code='999',
        rate_limit_resource='forged',
    )
    monitor = GitHubMonitor(monitoring.component('github-async', integration='ntp'), now=lambda: NOW)
    client = AsyncGitHubClient('token', rate_limiter=rate_limiter, transport=transport, observer=monitor)
    return client, monitor, sink, handler


def samples(sink: RecordingSink, name: str) -> list[tuple[float, dict[str, str]]]:
    return [(record.value, dict(record.tags)) for record in sink.records_named(name)]


async def test_every_attempt_is_counted_under_the_family_tags_only(monkeypatch: pytest.MonkeyPatch):
    advance_clock_on_sleep(FakeClock(), monkeypatch)
    budget = {
        'x-ratelimit-remaining': '4990',
        'x-ratelimit-limit': '5000',
        'x-ratelimit-reset': str(int(NOW) + 90),
        'x-ratelimit-resource': 'core',
    }
    responses = [httpx.Response(503), httpx.Response(200, json=RUN_PAYLOAD, headers=budget)]
    client, _, sink, handler = monitored(httpx.MockTransport(lambda request: responses.pop(0)))

    await client.get_workflow_run('o', 'r', 42)

    failed = {**PIPELINE, 'http.status_code': '503'}
    succeeded = {**PIPELINE, 'http.status_code': '200'}
    assert samples(sink, 'requests.count') == [(1, failed), (1, succeeded)]
    assert samples(sink, 'requests.fault') == [
        (1, {**failed, 'dispatcher.reason': 'server_error'}),
        (0, {**succeeded, 'dispatcher.reason': 'none'}),
    ]
    assert samples(sink, 'requests.throttled') == [(0, failed), (0, succeeded)]
    assert samples(sink, 'requests.retried') == [(0, PIPELINE), (1, PIPELINE)]
    assert [tags for _, tags in samples(sink, 'requests.duration')] == [failed, succeeded]
    # Only the headers the response sent: the 503 had none, and the 200 sent no `used`.
    core = {**PIPELINE, 'github.rate_limit.resource': 'core'}
    assert [(record.name, record.value, dict(record.tags)) for record in budget_gauges(sink)] == [
        ('requests.rate_limit.remaining', 4990, core),
        ('requests.rate_limit.limit', 5000, core),
        ('requests.rate_limit.reset_in', 90, core),
    ]
    [failure] = [event for event in handler.events if event['level'] == 'error']
    assert failure['event'] == 'GitHub request attempt failed'
    assert (failure['endpoint'], failure['attempt'], failure['status_code']) == (RUN_PATH, 1, 503)
    assert (failure['reason'], failure['terminal'], failure['integration']) == ('server_error', False, 'ntp')
    [completed] = [event for event in handler.events if event['event'] == 'GitHub request completed']
    assert (completed['level'], completed['attempt'], completed['status_code']) == ('debug', 2, 200)


def budget_gauges(sink: RecordingSink) -> list[MetricRecord]:
    return [record for record in sink.records if record.name.startswith('requests.rate_limit.')]


@pytest.mark.parametrize(
    ('resource', 'tagged'),
    [(None, 'unknown'), ('search', 'search')],
    ids=['unnamed', 'another-resource'],
)
async def test_a_failed_response_gauges_its_own_budget_and_logs_no_header(resource: str | None, tagged: str):
    """Budgets GitHub keeps apart stay apart, and an unparseable value is not reported as a number."""
    headers = {
        'x-ratelimit-remaining': '29',
        'x-ratelimit-used': '1',
        'x-ratelimit-limit': 'not-a-number',
        'x-ratelimit-reset': 'nan',
        'location': f'https://storage.example/a?signature={SIGNATURE}',
    }
    if resource is not None:
        headers['x-ratelimit-resource'] = resource
    client, _, sink, handler = monitored(httpx.MockTransport(lambda request: httpx.Response(404, headers=headers)))

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_workflow_run('o', 'r', 42, retry=NO_RETRY)

    budget = {**PIPELINE, 'github.rate_limit.resource': tagged}
    assert [(record.name, record.value, dict(record.tags)) for record in budget_gauges(sink)] == [
        ('requests.rate_limit.remaining', 29, budget),
        ('requests.rate_limit.used', 1, budget),
    ]
    [attempt, terminal] = handler.events
    assert (attempt['method'], attempt['endpoint'], attempt['attempt']) == ('GET', RUN_PATH, 1)
    assert (attempt['status_code'], attempt['reason'], terminal['status_code']) == (404, 'client_error', 404)
    assert SIGNATURE not in json.dumps(handler.events, default=str)


def governed_limiter(monkeypatch: pytest.MonkeyPatch) -> InstrumentedAsyncLimiter:
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    return InstrumentedAsyncLimiter(AsyncLimiter(5000, 3600), budget_governor=BudgetGovernor(now=clock))


@pytest.mark.parametrize(
    ('rejection', 'throttled', 'replayed'),
    [
        pytest.param(httpx.Response(403, headers={'x-ratelimit-remaining': '0'}), 1, True, id='primary-limit'),
        pytest.param(httpx.Response(403, headers={'retry-after': '5'}), 1, True, id='secondary-limit'),
        # Rate limiting by its status alone, which the client does not wait out without headers.
        pytest.param(httpx.Response(429), 1, False, id='unexplained-429'),
        pytest.param(httpx.Response(403), 0, False, id='permission-denied'),
        pytest.param(httpx.Response(500), 0, False, id='server-error'),
    ],
)
async def test_only_an_attempt_github_rejects_for_rate_limiting_counts_as_throttled(
    rejection: httpx.Response, throttled: int, replayed: bool, monkeypatch: pytest.MonkeyPatch
):
    responses = [rejection, httpx.Response(200, json=RUN_PAYLOAD)]
    client, _, sink, _ = monitored(httpx.MockTransport(lambda request: responses.pop(0)), governed_limiter(monkeypatch))

    with suppress(httpx.HTTPStatusError):
        await client.get_workflow_run('o', 'r', 42, retry=NO_RETRY)

    rejected = [(throttled, {**PIPELINE, 'http.status_code': str(rejection.status_code)})]
    succeeded = [(0, {**PIPELINE, 'http.status_code': '200'})] if replayed else []
    assert samples(sink, 'requests.throttled') == rejected + succeeded
    # Throttled or not, a rejection is still GitHub's fault.
    assert samples(sink, 'requests.fault')[0][0] == 1


def abandoning_limiter() -> InstrumentedAsyncLimiter:
    governor = BudgetGovernor(max_wait_seconds=1)
    governor.observe(BudgetSnapshot(retry_after=3600))
    return InstrumentedAsyncLimiter(AsyncLimiter(100, 1), budget_governor=governor)


@pytest.mark.parametrize(
    ('transport', 'rate_limiter', 'error', 'sent'),
    [
        pytest.param(
            httpx.MockTransport(lambda request: httpx.Response(404)), None, httpx.HTTPStatusError, 1, id="not-found"
        ),
        pytest.param(
            httpx.MockTransport(lambda request: httpx.Response(200)),
            abandoning_limiter(),
            RateLimitWaitAbandoned,
            0,
            id="abandoned-before-send",
        ),
    ],
)
async def test_a_request_that_fails_for_good_is_logged_once_as_terminal(
    transport: httpx.MockTransport,
    rate_limiter: InstrumentedAsyncLimiter | None,
    error: type[Exception],
    sent: int,
):
    client, _, sink, handler = monitored(transport, rate_limiter)

    with pytest.raises(error):
        await client.get_workflow_run('o', 'r', 42)

    # One sample per send, and none for the terminal failure or for a wait that never sent.
    assert len(sink.records_named('requests.count')) == len(sink.records_named('requests.throttled')) == sent
    [terminal] = [event for event in handler.events if event.get('terminal')]
    assert (terminal['level'], terminal['endpoint'], terminal['attempts']) == ('error', RUN_PATH, sent)
    assert terminal['error'].startswith(error.__name__)
    # Nothing was sent to fail, so an abandoned wait adds no HTTP reason and the log keeps the context's.
    expected = ('client_error', 404) if sent else ('forged', '999')
    assert (terminal['reason'], terminal['status_code']) == expected


@pytest.mark.parametrize(
    ('error', 'fault', 'reason', 'logged'),
    [
        pytest.param(
            httpx.ConnectError('refused'),
            1,
            'transport',
            [('error', 'GitHub request attempt failed'), ('error', 'GitHub request failed')],
            id='transport-failure',
        ),
        # The caller's own cancellation was sent, but it is neither GitHub's fault nor a failure.
        pytest.param(asyncio.CancelledError(), 0, 'cancelled', [('debug', 'GitHub request cancelled')], id='cancelled'),
    ],
)
async def test_a_send_without_a_response_has_elapsed_time_but_no_status(
    error: BaseException, fault: int, reason: str, logged: list[tuple[str, str]]
):
    def unanswered(request: httpx.Request) -> httpx.Response:
        raise error

    client, _, sink, handler = monitored(httpx.MockTransport(unanswered))

    with pytest.raises(type(error)):
        await client.get_workflow_run('o', 'r', 42, retry=NO_RETRY)

    assert samples(sink, 'requests.count') == [(1, PIPELINE)]
    assert samples(sink, 'requests.fault') == [(fault, {**PIPELINE, 'dispatcher.reason': reason})]
    assert samples(sink, 'requests.throttled') == [(0, PIPELINE)]
    assert samples(sink, 'requests.retried') == [(0, PIPELINE)]
    assert [tags for _, tags in samples(sink, 'requests.duration')] == [PIPELINE]
    assert [(event['level'], event['event']) for event in handler.events] == logged
    assert handler.events[0]['reason'] == reason


@pytest.mark.parametrize('outcome', [WaitOutcome.COMPLETED, WaitOutcome.ABANDONED, WaitOutcome.CANCELLED])
def test_a_throttle_wait_reports_its_actual_time_and_keeps_the_requested_one_in_the_log(outcome: WaitOutcome):
    _, monitor, sink, handler = monitored(httpx.MockTransport(lambda request: httpx.Response(200)))

    monitor.rate_limit_event(
        WaitEvent(reason=WaitReason.EXHAUSTED, elapsed_seconds=12.5, outcome=outcome, requested_seconds=51.0)
    )

    assert samples(sink, 'throttle.wait.duration') == [(12.5, {**PIPELINE, 'dispatcher.reason': 'exhausted'})]
    [event] = handler.events
    assert (event['outcome'], event['elapsed_seconds'], event['requested_seconds']) == (outcome, 12.5, 51.0)
