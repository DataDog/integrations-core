# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Observable behavior of the buffered Datadog metrics sink."""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Mapping
from typing import Any

import pytest
from datadog_api_client.exceptions import ApiException
from datadog_api_client.v2.model.metric_payload import MetricPayload

import ddev.monitoring.datadog_metrics as datadog_metrics_module
from ddev.monitoring.datadog_metrics import (
    COUNT_WINDOW_SECONDS,
    DISTRIBUTION_REQUEST_SERIES_LIMIT,
    REQUEST_SERIES_LIMIT,
    CountedMetric,
    CountWindow,
    DatadogMetricsSink,
    QueuedMetric,
)
from ddev.monitoring.diagnostics import DiagnosticCategory
from ddev.monitoring.metrics import EMPTY_TAGS, MetricKind, MetricRecord
from tests.helpers.clock import FakeClock
from tests.helpers.datadog import FakeMetricsSubmitter

NAMESPACE = 'agent_integrations.test_dispatcher'
EMITTED_AT = 1_700_000_000


def make_sink(submitter: FakeMetricsSubmitter, diagnostics: list[str], **kwargs: Any) -> DatadogMetricsSink:
    return DatadogMetricsSink(
        api_key='test-api-key',
        namespace=NAMESPACE,
        submitter=submitter,
        diagnostics=diagnostics.append,
        **kwargs,
    )


def record(
    name: str,
    kind: MetricKind = MetricKind.GAUGE,
    value: float = 1,
    tags: Mapping[str, str] = EMPTY_TAGS,
    timestamp: int = EMITTED_AT,
    **kwargs: Any,
) -> MetricRecord:
    return MetricRecord(name=name, kind=kind, value=value, timestamp=timestamp, tags=tags, **kwargs)


def make_window(series_limit: int = 100) -> CountWindow:
    return CountWindow(interval=COUNT_WINDOW_SECONDS, series_limit=series_limit)


def queued(
    name: str,
    value: float = 1,
    *,
    accepted: float = 100.0,
    timestamp: int = EMITTED_AT,
    tags: Mapping[str, str] = EMPTY_TAGS,
    unit: str | None = None,
) -> QueuedMetric:
    """A count increment as the sink queues it: paired clocks read at acceptance."""
    return QueuedMetric(
        record(name, MetricKind.COUNT, value, tags=tags, unit=unit, timestamp=timestamp), accepted, timestamp
    )


class FakeTime:
    """A stand-in for the time module, with manually advanced monotonic and wall clocks."""

    def __init__(self) -> None:
        self.monotonic_clock = FakeClock()
        self.wall_clock = FakeClock(1_700_000_000.0)

    def advance(self, seconds: float) -> None:
        self.monotonic_clock.advance(seconds)
        self.wall_clock.advance(seconds)

    def monotonic(self) -> float:
        return self.monotonic_clock()

    def time(self) -> float:
        return self.wall_clock()


def test_gauge_series_carry_the_record_as_a_v2_payload():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(record('duration', MetricKind.GAUGE, 2.5, unit='second'))
    sink.record(record('heap', MetricKind.GAUGE, 3))
    sink.close()

    [duration, heap] = submitter.series
    assert duration == {
        'metric': f'{NAMESPACE}.duration',
        'type': 3,
        'unit': 'second',
        'points': [{'timestamp': EMITTED_AT, 'value': 2.5}],
    }
    assert heap['points'] == [{'timestamp': EMITTED_AT, 'value': 3.0}]
    assert not submitter.distribution_requests
    assert not diagnostics


def test_distributions_carry_the_record_as_a_v1_payload():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(record('job.seconds', MetricKind.DISTRIBUTION, 12.5))
    sink.close()

    [distribution] = submitter.distributions
    assert distribution == {
        'metric': f'{NAMESPACE}.job.seconds',
        'points': [[float(EMITTED_AT), [12.5]]],
    }
    assert 'unit' not in distribution
    assert not submitter.metric_requests
    assert not diagnostics


def test_counts_within_one_collection_window_leave_as_one_summed_point():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(record('jobs', MetricKind.COUNT, 1, tags={'environment': 'py3.13'}, unit='job'))
    sink.record(record('jobs', MetricKind.COUNT, 1, tags={'environment': 'py3.13'}, unit='job'))
    sink.record(record('jobs', MetricKind.COUNT, 3, tags={'environment': 'py3.13'}, unit='job'))
    sink.close()

    [jobs] = submitter.series
    assert jobs['metric'] == f'{NAMESPACE}.jobs'
    assert jobs['type'] == 1
    assert jobs['unit'] == 'job'
    assert jobs['tags'] == ['environment:py3.13']
    [point] = jobs['points']
    assert point['value'] == 5.0
    # The point states the window it covers; Datadog requires an interval of at least one second.
    assert jobs['interval'] >= 1
    assert not diagnostics


def test_counts_with_unspecified_and_specified_units_aggregate_into_one_series():
    submitter = FakeMetricsSubmitter()
    sink = make_sink(submitter, [])

    sink.record(record('jobs', MetricKind.COUNT, 1))
    sink.record(record('jobs', MetricKind.COUNT, 8, unit='job'))
    sink.close()

    [jobs] = submitter.series
    assert jobs['unit'] == 'job'
    assert jobs['points'][0]['value'] == 9.0


def test_a_window_opens_on_its_first_accepted_increment_and_closes_on_its_deadline():
    window = make_window()

    assert window.closes_at is None
    assert window.add(queued('jobs', 1, accepted=100.0)) is None

    assert window.closes_at == 100.0 + COUNT_WINDOW_SECONDS
    assert not window.expired(100.0 + COUNT_WINDOW_SECONDS - 0.01)
    assert window.expired(100.0 + COUNT_WINDOW_SECONDS)

    timestamp, interval, [counted] = window.close()
    assert (timestamp, interval) == (EMITTED_AT, 10)
    assert counted == CountedMetric('jobs', {}, None, 1.0)


def test_a_partial_window_closes_with_its_actual_duration():
    window = make_window()
    window.add(queued('jobs', 2, accepted=200.0, timestamp=EMITTED_AT + 100))

    timestamp, interval, [counted] = window.close(now=203.0)

    assert (timestamp, interval) == (EMITTED_AT + 100, 3)
    assert counted.value == 2.0


def test_series_accumulate_by_name_and_tags():
    window = make_window()
    for entry in (
        queued('jobs', 1, accepted=100.0),
        queued('jobs', 2, accepted=100.0, tags={'environment': 'py3.13'}),
        queued('builds', 3, accepted=100.0),
        queued('jobs', 4, accepted=100.0),
    ):
        assert window.add(entry) is None

    _, _, counted = window.close()
    assert sorted(counted, key=lambda item: (item.name, sorted(item.tags.items()))) == [
        CountedMetric('builds', {}, None, 3.0),
        CountedMetric('jobs', {}, None, 5.0),
        CountedMetric('jobs', {'environment': 'py3.13'}, None, 2.0),
    ]


def test_a_series_adopts_a_specified_unit_and_rejects_conflicting_ones():
    window = make_window()
    for entry in (
        queued('jobs', 1, accepted=100.0),
        queued('jobs', 2, unit='job', accepted=100.0),
        queued('jobs', 3, accepted=100.0),
    ):
        assert window.add(entry) is None

    rejected = window.add(queued('jobs', 4, unit='second', accepted=100.0))

    assert rejected is not None
    assert rejected[0] is DiagnosticCategory.CONVERSION
    assert 'conflicting units' in rejected[1]
    _, _, [counted] = window.close()
    assert (counted.value, counted.unit) == (6.0, 'job')


def test_an_increment_that_overflows_the_total_is_refused():
    window = make_window()
    window.add(queued('jobs', 1e308, accepted=100.0))

    rejected = window.add(queued('jobs', 1e308, accepted=100.0))

    assert rejected is not None
    assert rejected[0] is DiagnosticCategory.CONVERSION
    _, _, [counted] = window.close()
    assert counted.value == 1e308


def test_a_count_that_cannot_be_converted_does_not_discard_its_window_neighbors():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(record('broken', MetricKind.COUNT, 1, unit=42))  # type: ignore[arg-type]
    sink.record(record('valid', MetricKind.COUNT, 2))
    sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.valid']
    assert [series['points'][0]['value'] for series in submitter.series] == [2.0]
    assert any('broken' in notice and 'could not be converted' in notice for notice in diagnostics)


def test_completed_windows_leave_as_separate_points_with_distinct_timestamps(monkeypatch: pytest.MonkeyPatch):
    fake = FakeTime()
    monkeypatch.setattr(datadog_metrics_module, 'time', fake)
    monkeypatch.setattr(datadog_metrics_module, 'REQUEST_SERIES_LIMIT', 1)
    submitter = FakeMetricsSubmitter()
    sink = make_sink(submitter, [], flush_interval=60)

    try:
        sink.record(record('jobs', MetricKind.COUNT, 1))
        sink.record(record('checkpoint'))
        # The following gauge proves the worker opened the count window before time advances.
        assert submitter.wait_for_submission()
        fake.advance(COUNT_WINDOW_SECONDS)
        # Accepted at the first window's deadline, the second increment rolls it over.
        sink.record(record('jobs', MetricKind.COUNT, 2))
    finally:
        sink.close()

    [first, second] = [series for series in submitter.series if series['metric'] == f'{NAMESPACE}.jobs']
    assert first['points'] == [{'timestamp': EMITTED_AT, 'value': 1.0}]
    assert first['interval'] == 10
    assert second['points'] == [{'timestamp': EMITTED_AT + 10, 'value': 2.0}]
    assert second['interval'] == 1


def test_counts_queued_while_intake_blocks_keep_their_acceptance_windows(
    monkeypatch: pytest.MonkeyPatch,
):
    """Intake latency must not merge increments accepted in separate windows."""
    fake = FakeTime()
    monkeypatch.setattr(datadog_metrics_module, 'time', fake)
    submitter = FakeMetricsSubmitter()
    submitter.block_submissions()
    sink = make_sink(submitter, [], flush_interval=60)

    for index in range(REQUEST_SERIES_LIMIT):
        sink.record(record(f'heap.{index}'))
    # The worker is blocked inside the synchronous intake call while increments queue up.
    assert submitter.wait_for_submission()
    sink.record(record('jobs', MetricKind.COUNT, 1))
    fake.advance(COUNT_WINDOW_SECONDS)
    sink.record(record('jobs', MetricKind.COUNT, 2))
    fake.advance(COUNT_WINDOW_SECONDS)
    sink.record(record('jobs', MetricKind.COUNT, 3))
    submitter.resume_submissions()
    sink.close()

    windows = [series for series in submitter.series if series['metric'] == f'{NAMESPACE}.jobs']
    assert [(series['points'], series['interval']) for series in windows] == [
        ([{'timestamp': EMITTED_AT, 'value': 1.0}], 10),
        ([{'timestamp': EMITTED_AT + 10, 'value': 2.0}], 10),
        ([{'timestamp': EMITTED_AT + 20, 'value': 3.0}], 1),
    ]


def test_a_count_paused_before_acceptance_joins_the_window_that_accepts_it(monkeypatch: pytest.MonkeyPatch):
    """Window membership follows acceptance: a paused emitter must not pull its
    increment back into a window whose deadline passed while it was paused."""
    fake = FakeTime()
    monkeypatch.setattr(datadog_metrics_module, 'time', fake)
    submitter = FakeMetricsSubmitter()
    sink = make_sink(submitter, [], flush_interval=60)
    paused = threading.Event()
    release = threading.Event()

    def produce(constructed: MetricRecord) -> None:
        paused.set()
        assert release.wait(5)
        sink.record(constructed)

    producer: threading.Thread | None = None
    try:
        sink.record(record('jobs', MetricKind.COUNT, 1))
        fake.advance(8)
        # Constructed before the boundary with the wall time of that instant, so only
        # acceptance-time capture can keep it out of the first window.
        producer = threading.Thread(
            target=produce, args=(record('jobs', MetricKind.COUNT, 3, timestamp=int(fake.time())),)
        )
        producer.start()
        assert paused.wait(5)
        fake.advance(4)  # The paused increment's window deadline passed while it was paused.
        # The +2 overtakes the paused emitter: accepted first, it opens the second window.
        sink.record(record('jobs', MetricKind.COUNT, 2))
        release.set()
        producer.join(5)
    finally:
        release.set()
        if producer is not None:
            producer.join(5)
        sink.close()

    windows = [series for series in submitter.series if series['metric'] == f'{NAMESPACE}.jobs']
    assert [(series['points'], series['interval']) for series in windows] == [
        ([{'timestamp': EMITTED_AT, 'value': 1.0}], 10),
        ([{'timestamp': EMITTED_AT + 12, 'value': 5.0}], 1),
    ]


def test_an_expired_window_waits_for_a_producer_inside_its_acceptance(monkeypatch: pytest.MonkeyPatch):
    """A producer between its clock capture and its enqueue holds the acceptance lock,
    so the idle expiry must not close the window from an empty poll observed earlier."""
    fake = FakeTime()
    monkeypatch.setattr(datadog_metrics_module, 'time', fake)
    poll_held = threading.Event()
    release_poll = threading.Event()
    empty_raised = threading.Event()
    producer_paused = threading.Event()
    release_producer = threading.Event()

    class ProbingQueue(queue.Queue):
        """Hold the worker inside one empty poll and pause a producer after its capture."""

        holding = False

        def get(self, block: bool = True, timeout: float | None = None) -> QueuedMetric | None:
            # A held poll only starts on an empty queue, so the window-opening increment
            # was already drained when the worker parks here.
            if block and self.holding and self.empty():
                poll_held.set()
                assert release_poll.wait(5)
                empty_raised.set()
                raise queue.Empty
            return super().get(block=block, timeout=timeout)

        def put_nowait(self, item: QueuedMetric | None) -> None:
            if item is not None and item.record.value == 2:
                producer_paused.set()
                assert release_producer.wait(5)
            super().put_nowait(item)

    monkeypatch.setattr(datadog_metrics_module.queue, 'Queue', ProbingQueue)
    submitter = FakeMetricsSubmitter()
    sink = make_sink(submitter, [], flush_interval=60)
    producer: threading.Thread | None = None
    try:
        sink.record(record('jobs', MetricKind.COUNT, 1))
        ProbingQueue.holding = True
        # The worker drained the window-opening increment and is parked inside one empty poll.
        assert poll_held.wait(5)
        fake.advance(5)
        producer = threading.Thread(target=sink.record, args=(record('jobs', MetricKind.COUNT, 2),))
        producer.start()
        assert producer_paused.wait(5)
        fake.advance(10)  # Past the window deadline while the producer holds the lock.
        release_poll.set()
        # The worker now acts on an empty poll observed while the producer holds the lock.
        assert empty_raised.wait(5)
    finally:
        release_poll.set()
        release_producer.set()
        if producer is not None:
            producer.join(5)
        sink.close()

    windows = [series for series in submitter.series if series['metric'] == f'{NAMESPACE}.jobs']
    assert [(series['points'], series['interval']) for series in windows] == [
        ([{'timestamp': EMITTED_AT, 'value': 3.0}], 10),
    ]


def test_a_batch_flush_while_the_count_window_is_open_never_emits_partial_counts():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics, flush_interval=60.0)

    for _ in range(4):
        sink.record(record('jobs', MetricKind.COUNT, 1))
    # The batch reaches its capacity and leaves while the count window stays open.
    for index in range(REQUEST_SERIES_LIMIT):
        sink.record(record(f'heap.{index}'))
    assert submitter.wait_for_submission()

    flushed = [series for request in submitter.metric_requests for series in request]
    assert all(not series['metric'].endswith('.jobs') for series in flushed)
    sink.close()

    jobs = [series for request in submitter.metric_requests for series in request if series['metric'].endswith('.jobs')]
    assert len(jobs) == 1
    [point] = jobs[0]['points']
    assert point['value'] == 4.0
    assert not diagnostics


def test_the_count_window_drops_new_series_beyond_its_capacity(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(datadog_metrics_module, 'COUNT_WINDOW_SERIES_LIMIT', 2)
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(record('a', MetricKind.COUNT, 1))
    sink.record(record('b', MetricKind.COUNT, 1))
    sink.record(record('c', MetricKind.COUNT, 1))
    sink.record(record('a', MetricKind.COUNT, 1))
    sink.close()

    delivered = {series['metric']: series['points'][0]['value'] for series in submitter.series}
    assert delivered == {f'{NAMESPACE}.a': 2.0, f'{NAMESPACE}.b': 1.0}
    assert any('count collection window is full' in notice for notice in diagnostics)


def test_records_keep_their_emission_timestamp_and_tags_across_the_queue():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)
    queued = record('heap', tags={'environment': 'py3.13', 'agent_image': 'datadog/agent:latest'})

    sink.record(queued)
    sink.close()

    [series] = submitter.series
    assert series['points'][0]['timestamp'] == queued.timestamp
    assert series['tags'] == ['agent_image:datadog/agent:latest', 'environment:py3.13']
    assert not diagnostics


def test_an_empty_namespace_leaves_metric_names_untouched():
    submitter = FakeMetricsSubmitter()
    sink = DatadogMetricsSink(api_key='test-api-key', submitter=submitter)

    sink.record(record('jobs'))
    sink.close()

    [series] = submitter.series
    assert series['metric'] == 'jobs'


def test_series_are_batched_under_the_request_limits_and_drained_on_close():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    for index in range(REQUEST_SERIES_LIMIT + 10):
        sink.record(record(f'jobs.{index}', MetricKind.COUNT))
    for index in range(DISTRIBUTION_REQUEST_SERIES_LIMIT + 10):
        sink.record(record(f'seconds.{index}', MetricKind.DISTRIBUTION))
    sink.close()
    sink.close()

    assert len(submitter.series) == REQUEST_SERIES_LIMIT + 10
    assert all(len(request) <= REQUEST_SERIES_LIMIT for request in submitter.metric_requests)
    assert len(submitter.distributions) == DISTRIBUTION_REQUEST_SERIES_LIMIT + 10
    assert all(len(request) <= DISTRIBUTION_REQUEST_SERIES_LIMIT for request in submitter.distribution_requests)
    assert not diagnostics


@pytest.mark.parametrize(
    'invalid',
    [
        record(''),
        record('jobs', value=float('inf')),
        record('jobs', value=float('nan')),
    ],
    ids=['empty-name', 'infinite-value', 'nan-value'],
)
def test_invalid_records_are_dropped_with_a_diagnostic_and_delivery_continues(invalid):
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(invalid)
    sink.record(record('valid'))
    sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.valid']
    assert not submitter.distribution_requests
    assert diagnostics


def test_a_rejected_request_is_split_until_the_api_accepts_it():
    submitter = FakeMetricsSubmitter()
    submitter.fail_next(ApiException(status=413, reason='Payload Too Large'))
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    for index in range(4):
        sink.record(record(f'heap.{index}'))
    sink.close()

    assert len(submitter.series) == 4
    assert all(len(request) <= 2 for request in submitter.metric_requests)
    assert not diagnostics


def test_a_series_the_api_rejects_alone_is_dropped_without_losing_its_siblings():
    class RejectsBlobSeries(FakeMetricsSubmitter):
        def submit_metrics(self, body: MetricPayload) -> object:
            self.begin_submission()
            if any('blob:' in tag for series in body.series for tag in getattr(series, 'tags', None) or []):
                raise ApiException(status=413, reason='Payload Too Large')
            self.metric_requests.append([series.to_dict() for series in body.series])
            return {}

    submitter = RejectsBlobSeries()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(record('fine-1'))
    sink.record(record('fine-2'))
    sink.record(record('huge', tags={'blob': 'x' * 600_000}))
    sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.fine-1', f'{NAMESPACE}.fine-2']
    assert any('too large on its own' in notice for notice in diagnostics)


def test_the_flush_deadline_delivers_a_batch_while_records_are_still_queued(monkeypatch: pytest.MonkeyPatch):
    class PacedQueue(queue.Queue[QueuedMetric | None]):
        step = threading.Semaphore(0)
        waiting = threading.Semaphore(0)
        paced = True

        def get(self, block: bool = True, timeout: float | None = None) -> QueuedMetric | None:
            if block and self.paced:
                self.waiting.release()
                assert self.step.acquire(timeout=5), 'the test did not release the next queued record'
            return super().get(block=block, timeout=timeout)

    fake = FakeTime()
    monkeypatch.setattr(datadog_metrics_module, 'time', fake)
    monkeypatch.setattr(datadog_metrics_module.queue, 'Queue', PacedQueue)
    submitter = FakeMetricsSubmitter()
    sink = make_sink(submitter, [], flush_interval=0.05)

    for index in range(10):
        sink.record(record(f'heap.{index}'))
    try:
        assert PacedQueue.waiting.acquire(timeout=5)
        PacedQueue.step.release()
        assert PacedQueue.waiting.acquire(timeout=5)
        fake.advance(0.06)
        PacedQueue.step.release()
        assert submitter.wait_for_submission(), 'no flush happened while records were still queued'
    finally:
        PacedQueue.paced = False
        PacedQueue.step.release()
        sink.close()

    assert len(submitter.series) == 10
    assert [series['metric'] for series in submitter.metric_requests[0]] == [f'{NAMESPACE}.heap.0']


def test_a_low_volume_stream_flushes_at_its_configured_deadline():
    """One queued record is submitted by the deadline, without waiting for a full queue poll."""
    submitter = FakeMetricsSubmitter()
    sink = make_sink(submitter, [], flush_interval=0.05)

    sink.record(record('heap'))
    assert submitter.wait_for_submission(timeout=0.15)
    sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.heap']


@pytest.mark.parametrize(
    'flush_interval',
    [0, -1, float('nan'), float('inf'), float('-inf')],
    ids=['zero', 'negative', 'nan', 'positive-infinity', 'negative-infinity'],
)
def test_an_invalid_flush_interval_is_rejected_without_creating_a_client(
    flush_interval: float, monkeypatch: pytest.MonkeyPatch
):
    clients = []

    class FakeApiClient:
        def __init__(self, _configuration: object) -> None:
            clients.append(self)

    monkeypatch.setattr(datadog_metrics_module, 'ApiClient', FakeApiClient)

    with pytest.raises(ValueError, match='flush_interval must be a positive number of seconds'):
        DatadogMetricsSink(api_key='test-api-key', flush_interval=flush_interval)

    assert not clients


def test_a_full_queue_drops_metrics_instead_of_blocking_the_emitter():
    submitter = FakeMetricsSubmitter()
    submitter.block_submissions()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics, queue_size=2, flush_interval=0.05)

    sink.record(record('first'))
    assert submitter.wait_for_submission()
    for index in range(50):
        sink.record(record(f'extra.{index}'))

    assert any('queue is full' in notice for notice in diagnostics)
    submitter.resume_submissions()
    sink.close()


def test_submission_failures_do_not_stop_the_worker():
    submitter = FakeMetricsSubmitter()
    submitter.fail_next(RuntimeError('intake unavailable'))
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics, flush_interval=0.05)

    sink.record(record('first'))
    assert submitter.wait_for_submission()
    sink.record(record('second'))
    sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.second']
    assert any('failed' in notice for notice in diagnostics)


def test_a_failing_diagnostics_callback_cannot_break_delivery():
    submitter = FakeMetricsSubmitter()
    submitter.fail_next(RuntimeError('intake unavailable'), count=100)

    def broken_diagnostics(text: str) -> None:
        raise RuntimeError('the diagnostics channel is down')

    sink = DatadogMetricsSink(
        api_key='test-api-key',
        namespace=NAMESPACE,
        submitter=submitter,
        diagnostics=broken_diagnostics,
    )

    sink.record(record('first', MetricKind.COUNT))
    sink.close()

    assert [series['metric'] for series in submitter.series] == []


def test_a_record_racing_close_is_delivered_not_stranded_behind_the_worker(monkeypatch: pytest.MonkeyPatch):
    """A record accepted while shutdown runs must land ahead of the sentinel, where the worker
    still delivers it (see the review of
    https://github.com/DataDog/integrations-core/pull/25274#discussion_r4061350829)."""
    seen_first = threading.Event()
    released = threading.Event()
    closed = threading.Event()

    class GatedPutQueue(queue.Queue):
        """Hold the first accepted record inside its check-then-enqueue window."""

        def put_nowait(self, item: object) -> None:
            if not seen_first.is_set():
                seen_first.set()
                assert released.wait(5)
            super().put_nowait(item)

    monkeypatch.setattr(datadog_metrics_module.queue, 'Queue', GatedPutQueue)
    submitter = FakeMetricsSubmitter()
    sink = make_sink(submitter, [])

    racing = threading.Thread(target=sink.record, args=(record('racing'),))
    racing.start()
    assert seen_first.wait(5)

    def run_close() -> None:
        try:
            sink.close()
        finally:
            closed.set()

    closing = threading.Thread(target=run_close)
    closing.start()
    try:
        # With acceptance serialized, shutdown waits on the record's critical section; without
        # it, close finishes here and releasing the record strands it behind the sentinel.
        closed.wait(0.5)
    finally:
        released.set()

    racing.join(5)
    closing.join(5)
    assert not closing.is_alive()
    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.racing']


def test_shutdown_drains_the_queue_when_the_sentinel_cannot_be_enqueued(monkeypatch: pytest.MonkeyPatch):
    """close() swallows a full-queue sentinel failure, so the worker must exit on a
    drained closed queue instead of waiting for a sentinel that never entered it."""

    class SentinelBlockedQueue(queue.Queue):
        def put_nowait(self, item: QueuedMetric | None) -> None:
            if item is None:
                raise queue.Full
            super().put_nowait(item)

    monkeypatch.setattr(datadog_metrics_module.queue, 'Queue', SentinelBlockedQueue)
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(record('first'))
    sink.record(record('second'))
    sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.first', f'{NAMESPACE}.second']
    assert not diagnostics


def test_a_record_accepted_after_a_stale_empty_poll_is_drained_at_shutdown(monkeypatch: pytest.MonkeyPatch):
    """An empty-queue observation that predates an acceptance must not end the worker:
    the accepted record sits ahead of the sentinel, and exiting skips both."""
    empty_observed = threading.Event()
    resume_worker = threading.Event()
    sentinel_queued = threading.Event()

    class StaleEmptyQueue(queue.Queue):
        """Hold the worker between its empty observation and the Empty it acts on."""

        observing = True

        def get(self, block: bool = True, timeout: float | None = None) -> QueuedMetric | None:
            if self.observing:
                try:
                    return super().get(block=False)
                except queue.Empty:
                    self.observing = False
                    empty_observed.set()
                    assert resume_worker.wait(5)
                    raise
            return super().get(block=block, timeout=timeout)

        def put_nowait(self, item: QueuedMetric | None) -> None:
            super().put_nowait(item)
            if item is None:
                sentinel_queued.set()

    monkeypatch.setattr(datadog_metrics_module.queue, 'Queue', StaleEmptyQueue)
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)
    closing: threading.Thread | None = None
    try:
        assert empty_observed.wait(5)
        sink.record(record('accepted'))
        closing = threading.Thread(target=sink.close)
        closing.start()
        assert sentinel_queued.wait(5)
    finally:
        resume_worker.set()
        if closing is not None:
            closing.join(5)
        sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.accepted']
    assert not diagnostics


def test_the_owned_api_client_is_closed_after_the_worker_stops(monkeypatch: pytest.MonkeyPatch):
    clients = []
    submitter = FakeMetricsSubmitter()

    class FakeApiClient:
        def __init__(self, _configuration: object) -> None:
            self.closed = False
            clients.append(self)

        def close(self) -> None:
            self.closed = True

    def make_submitter(_client: FakeApiClient) -> FakeMetricsSubmitter:
        return submitter

    monkeypatch.setattr(datadog_metrics_module, 'ApiClient', FakeApiClient)
    monkeypatch.setattr(datadog_metrics_module, 'DatadogMetricsApis', make_submitter)
    sink = DatadogMetricsSink(api_key='test-api-key', namespace=NAMESPACE)

    sink.record(record('delivered'))
    sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.delivered']
    assert clients[0].closed


def test_a_failing_apis_constructor_closes_the_partial_client_without_masking_the_error(
    monkeypatch: pytest.MonkeyPatch,
):
    clients = []

    class FailingCloseClient:
        def __init__(self, _configuration: object) -> None:
            self.closed = False
            clients.append(self)

        def close(self) -> None:
            self.closed = True
            raise RuntimeError('client teardown failed')

    def failing_apis(_client: FailingCloseClient) -> object:
        raise RuntimeError('the apis constructor failed')

    monkeypatch.setattr(datadog_metrics_module, 'ApiClient', FailingCloseClient)
    monkeypatch.setattr(datadog_metrics_module, 'DatadogMetricsApis', failing_apis)
    diagnostics: list[str] = []

    with pytest.raises(RuntimeError, match='the apis constructor failed'):
        DatadogMetricsSink(api_key='test-api-key', namespace=NAMESPACE, diagnostics=diagnostics.append)

    assert clients[0].closed
    assert any('closing the metrics API client failed' in notice for notice in diagnostics)


def test_a_failing_owned_client_close_is_diagnosed_without_escaping_the_worker(monkeypatch: pytest.MonkeyPatch):
    unhandled: list[object] = []
    monkeypatch.setattr(threading, 'excepthook', lambda args: unhandled.append(args))
    submitter = FakeMetricsSubmitter()

    class FailingCloseClient:
        def __init__(self, _configuration: object) -> None:
            pass

        def close(self) -> None:
            raise RuntimeError('client teardown failed')

    monkeypatch.setattr(datadog_metrics_module, 'ApiClient', FailingCloseClient)
    monkeypatch.setattr(datadog_metrics_module, 'DatadogMetricsApis', lambda _client: submitter)
    diagnostics: list[str] = []
    sink = DatadogMetricsSink(api_key='test-api-key', namespace=NAMESPACE, diagnostics=diagnostics.append)

    sink.record(record('delivered'))
    sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.delivered']
    assert any('closing the metrics API client failed' in notice for notice in diagnostics)
    assert not unhandled


def test_shutdown_returns_at_its_deadline_while_intake_is_blocked():
    submitter = FakeMetricsSubmitter()
    submitter.block_submissions()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics, flush_interval=0.05)
    sink.record(record('blocked'))
    assert submitter.wait_for_submission()

    started = time.monotonic()
    sink.close(timeout=0.01)
    elapsed = time.monotonic() - started

    assert elapsed < 0.5
    assert any('deadline' in notice for notice in diagnostics)
    submitter.resume_submissions()


def test_a_negative_shutdown_timeout_is_rejected_without_closing_the_sink():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    with pytest.raises(ValueError, match='timeout must not be negative'):
        sink.close(timeout=-1)

    sink.record(record('delivered after invalid close'))
    sink.close()
    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.delivered after invalid close']
    assert not diagnostics


def test_records_after_close_are_dropped():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)
    sink.close()

    sink.record(record('too late'))

    assert not submitter.series
    assert not diagnostics
