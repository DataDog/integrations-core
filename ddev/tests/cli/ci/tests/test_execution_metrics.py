# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the metrics helper: operation outcomes and operation timing."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from ddev.cli.ci.tests.execution_metrics import MetricsHelper, Operation
from ddev.monitoring.metrics import MetricKind
from tests.cli.ci.tests.helpers import recording_runtime
from tests.helpers.clock import FakeClock
from tests.helpers.monitoring import RecordingSink

OPERATION = 'dispatcher.operation'


def helper_with_sink(clock: Callable[[], float]) -> tuple[MetricsHelper, RecordingSink]:
    monitoring, sink = recording_runtime()
    return MetricsHelper(monitoring.component('test-runner').metrics, clock=clock), sink


def values(sink: RecordingSink, name: str) -> list[float]:
    return [record.value for record in sink.records_named(name)]


@pytest.mark.parametrize('failed', [False, True], ids=['settled-healthy', 'settled-failed'])
def test_record_operation_emits_one_attempt_and_its_settled_outcome(failed: bool):
    metrics, sink = helper_with_sink(FakeClock())

    metrics.record_operation(Operation.DISPATCH_BATCH, failed=failed)

    assert values(sink, 'operations.count') == [1]
    assert values(sink, 'operations.failed') == [int(failed)]
    assert sink.records_named('operations.count')[0].tags[OPERATION] == 'dispatch_batch'


@pytest.mark.parametrize('failed', [False, True], ids=['healthy', 'recovered-failure'])
def test_a_timed_operation_reports_its_elapsed_time_and_outcome_once(failed: bool):
    clock = FakeClock(100.0)
    metrics, sink = helper_with_sink(clock)

    with metrics.time_operation(Operation.COLLECT_ARTIFACTS, duration_metric='artifacts.download.duration') as result:
        result.failed = failed
        clock.advance(37.5)

    duration = sink.records_named('artifacts.download.duration')
    assert values(sink, 'artifacts.download.duration') == [37.5]
    assert duration[0].kind is MetricKind.DISTRIBUTION
    assert duration[0].tags[OPERATION] == 'collect_artifacts'
    assert values(sink, 'operations.count') == [1]
    assert values(sink, 'operations.failed') == [int(failed)]


def test_an_escaped_exception_fails_the_operation_and_propagates_unchanged():
    clock = FakeClock(100.0)
    metrics, sink = helper_with_sink(clock)

    error = RuntimeError('boom')
    with (
        pytest.raises(RuntimeError) as exc_info,
        metrics.time_operation(Operation.COLLECT_ARTIFACTS, duration_metric='artifacts.download.duration'),
    ):
        clock.advance(5.0)
        raise error

    assert exc_info.value is error
    assert values(sink, 'operations.count') == [1]
    assert values(sink, 'operations.failed') == [1]
    assert values(sink, 'artifacts.download.duration') == [5.0]


def test_cancellation_propagates_without_settling_the_operation():
    clock = FakeClock(100.0)
    metrics, sink = helper_with_sink(clock)

    with (
        pytest.raises(KeyboardInterrupt),
        metrics.time_operation(Operation.COLLECT_ARTIFACTS, duration_metric='artifacts.download.duration'),
    ):
        clock.advance(3.0)
        raise KeyboardInterrupt

    assert sink.records_named('operations.count') == []
    assert sink.records_named('operations.failed') == []
    assert values(sink, 'artifacts.download.duration') == [3.0]
