# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for operation counters, durations and settle log lines."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext

import pytest

from ddev.cli.ci.tests.execution_metrics import (
    MetricsHelper,
    Operation,
    OperationState,
    ResultMetric,
    report_result,
)
from ddev.monitoring.metrics import MetricKind, MetricRecord
from tests.cli.ci.tests.helpers import recording_runtime
from tests.helpers.clock import FakeClock
from tests.helpers.monitoring import RecordingJsonHandler, RecordingSink

OPERATION = 'dispatcher.operation'
RESULT = 'dispatcher.operation.result'


def settled_helper(clock: FakeClock) -> tuple[MetricsHelper, RecordingSink, RecordingJsonHandler]:
    handler = RecordingJsonHandler()
    monitoring, sink = recording_runtime(handler)
    return MetricsHelper(monitoring.component('test-runner'), clock=clock), sink, handler


def values(sink: RecordingSink, name: str) -> list[float]:
    return [record.value for record in sink.records_named(name)]


def durations(sink: RecordingSink, operation: Operation) -> list[MetricRecord]:
    return [record for record in sink.records_named('operation.duration') if record.tags[OPERATION] == operation.value]


def test_report_result_emits_the_whole_family_with_exactly_one_1():
    """Dense 0/1 counters, so a monitor sees zeros where an outcome did not land, not gaps."""
    monitoring, sink = recording_runtime()

    report_result(monitoring.component('test-runner').metrics, 'jobs', ResultMetric.TIMED_OUT, target='ntp')

    for result in ResultMetric:
        assert values(sink, f'jobs.{result.value}') == [int(result is ResultMetric.TIMED_OUT)]
    assert sink.records_named('jobs.timed_out')[0].tags['dispatcher.batch.job.target'] == 'ntp'


def test_success_settles_counters_duration_and_info_line():
    clock = FakeClock(100.0)
    metrics, sink, handler = settled_helper(clock)

    with metrics.operation(Operation.FETCH_WORKFLOW):
        clock.advance(37.5)

    assert values(sink, 'operations.count') == [1]
    assert values(sink, 'operations.failed') == [0]
    [duration] = durations(sink, Operation.FETCH_WORKFLOW)
    assert (duration.kind, duration.value) == (MetricKind.DISTRIBUTION, 37.5)
    assert duration.tags[RESULT] == 'success'
    [event] = handler.events
    assert event['level'] == 'info'
    assert event['event'] == 'Operation fetch_workflow succeeded in 37.5s'
    assert event['operation'] == 'fetch_workflow'
    assert event['operation_result'] == 'success'
    assert event['operation_duration_seconds'] == 37.5
    assert event['component'] == 'test-runner'


def test_recovered_failure_settles_one_warning_with_traceback():
    clock = FakeClock(100.0)
    metrics, sink, handler = settled_helper(clock)

    with metrics.operation(Operation.REFRESH_JOBS) as op:
        clock.advance(2.5)
        try:
            raise RuntimeError('boom')
        except RuntimeError:
            op.fail('Failed to list workflow jobs for run %s', 123, exc_info=True)

    assert values(sink, 'operations.count') == [1]
    assert values(sink, 'operations.failed') == [1]
    [duration] = durations(sink, Operation.REFRESH_JOBS)
    assert duration.value == 2.5
    assert duration.tags[RESULT] == 'failure'
    [event] = handler.events
    assert event['level'] == 'warning'
    assert event['event'] == 'Failed to list workflow jobs for run 123'
    assert event['operation_result'] == 'failure'
    assert 'exception' in event


def test_each_recovered_cause_is_listed_on_one_warning():
    """Causes sharing a field name keep their own values."""
    clock = FakeClock(100.0)
    metrics, sink, handler = settled_helper(clock)

    with metrics.operation(Operation.COLLECT_ARTIFACTS) as op:
        clock.advance(4.0)
        op.fail('Failed to download %s artifacts for workflow run %s', 2, 123, failure_count=2)
        op.fail('Failed to download %s artifact for workflow run %s', 1, 456, failure_count=1)

    assert values(sink, 'operations.failed') == [1]
    [event] = handler.events
    assert event['level'] == 'warning'
    assert event['event'] == (
        'Failed to download 2 artifacts for workflow run 123; Failed to download 1 artifact for workflow run 456'
    )
    assert event['operation_failures'] == [
        {'message': 'Failed to download 2 artifacts for workflow run 123', 'failure_count': 2},
        {'message': 'Failed to download 1 artifact for workflow run 456', 'failure_count': 1},
    ]


@pytest.mark.parametrize(
    ('record_failure', 'message'),
    [
        pytest.param(True, 'Failed to fetch workflow run 123 for batch batch-1', id='recorded-failure'),
        pytest.param(False, 'Operation fetch_workflow failed: boom', id='unrecorded-failure'),
    ],
)
def test_escaped_exception_settles_failure_and_one_error(record_failure: bool, message: str):
    clock = FakeClock(100.0)
    metrics, sink, handler = settled_helper(clock)
    error = RuntimeError('boom')

    with (
        pytest.raises(RuntimeError) as exc_info,
        metrics.operation(Operation.FETCH_WORKFLOW) as op,
    ):
        clock.advance(5.0)
        if record_failure:
            op.fail('Failed to fetch workflow run %s for batch %s', 123, 'batch-1')
        raise error

    assert exc_info.value is error
    assert values(sink, 'operations.count') == [1]
    assert values(sink, 'operations.failed') == [1]
    [duration] = durations(sink, Operation.FETCH_WORKFLOW)
    assert duration.value == 5.0
    assert duration.tags[RESULT] == 'failure'
    [event] = handler.events
    assert event['level'] == 'error'
    assert event['event'] == message
    assert event['operation_result'] == 'failure'
    assert 'exception' in event


def abandon(op: OperationState) -> None:
    op.abandon()


def cancel(_op: OperationState) -> None:
    raise KeyboardInterrupt


@pytest.mark.parametrize(
    ('unsettle', 'error'),
    [
        pytest.param(abandon, None, id='abandoned-mid-flight'),
        pytest.param(cancel, KeyboardInterrupt, id='cancelled'),
    ],
)
def test_abandoned_or_cancelled_operation_records_nothing(
    unsettle: Callable[[OperationState], None], error: type[BaseException] | None
):
    clock = FakeClock(100.0)
    metrics, sink, handler = settled_helper(clock)

    with (
        pytest.raises(error) if error is not None else nullcontext(),
        metrics.operation(Operation.COLLECT_ARTIFACTS) as op,
    ):
        clock.advance(3.0)
        unsettle(op)

    assert sink.records == []
    assert handler.events == []
