# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Observable behavior of the buffered Datadog metrics sink."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Mapping
from typing import Any, cast

import pytest

import ddev.monitoring.datadog_metrics as datadog_metrics_module
from ddev.monitoring.datadog_metrics import (
    DISTRIBUTION_REQUEST_BYTES_LIMIT,
    DISTRIBUTION_REQUEST_SERIES_LIMIT,
    REQUEST_BYTES_LIMIT,
    REQUEST_SERIES_LIMIT,
    DatadogMetricsSink,
)
from ddev.monitoring.metrics import EMPTY_TAGS, MetricKind, MetricRecord
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
    kind: MetricKind = MetricKind.COUNT,
    value: float = 1,
    tags: Mapping[str, str] = EMPTY_TAGS,
    **kwargs: Any,
) -> MetricRecord:
    return MetricRecord(name=name, kind=kind, value=value, timestamp=EMITTED_AT, tags=tags, **kwargs)


def test_count_and_gauge_series_carry_the_record_as_a_v2_payload():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(record('jobs', MetricKind.COUNT, 3, interval=60, unit='job'))
    sink.record(record('duration', MetricKind.GAUGE, 2.5))
    sink.record(record('defaults', MetricKind.COUNT, 7, interval=None))
    sink.close()

    [jobs, duration, defaults] = submitter.series
    assert jobs == {
        'metric': f'{NAMESPACE}.jobs',
        'type': 1,
        'interval': 60,
        'unit': 'job',
        'points': [{'timestamp': EMITTED_AT, 'value': 3.0}],
    }
    assert duration == {
        'metric': f'{NAMESPACE}.duration',
        'type': 3,
        'points': [{'timestamp': EMITTED_AT, 'value': 2.5}],
    }
    # A count without an explicit window still states one, as the v2 intake requires.
    assert defaults['interval'] == 1
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


def test_records_keep_their_emission_timestamp_and_tags_across_the_queue():
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)
    queued = record('jobs', tags={'environment': 'py3.13', 'agent_image': 'datadog/agent:latest'})

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
        sink.record(record(f'jobs.{index}'))
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
    ('kind', 'limit'),
    [
        (MetricKind.COUNT, REQUEST_BYTES_LIMIT),
        (MetricKind.GAUGE, REQUEST_BYTES_LIMIT),
        (MetricKind.DISTRIBUTION, DISTRIBUTION_REQUEST_BYTES_LIMIT),
    ],
    ids=['counts', 'gauges', 'distributions'],
)
def test_requests_stay_below_the_intake_byte_limits(kind, limit):
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    for index in range(9):
        sink.record(record(f'blobby.{index}', kind, tags={'blob': 'x' * (limit // 4)}))
    sink.close()

    requests = submitter.distribution_requests if kind is MetricKind.DISTRIBUTION else submitter.metric_requests
    assert len(requests) >= 2
    assert all(len(json.dumps(request, separators=(',', ':')).encode()) < limit for request in requests)
    assert not diagnostics


@pytest.mark.parametrize(
    ('invalid', 'notice'),
    [
        (record(''), 'without a name'),
        (record('jobs', value=float('inf')), 'non-finite'),
        (record('jobs', value=float('nan')), 'non-finite'),
        (record('jobs', interval=0), 'below one second'),
    ],
    ids=['empty-name', 'infinite-value', 'nan-value', 'zero-interval'],
)
def test_invalid_records_are_dropped_with_a_diagnostic_and_delivery_continues(invalid, notice):
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(invalid)
    sink.record(record('valid'))
    sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.valid']
    assert not submitter.distribution_requests
    assert any(notice in text for text in diagnostics)


@pytest.mark.parametrize(
    'malformed',
    [
        record('jobs', value=cast('float', 'oops')),
        record('jobs', interval=cast('int', 'soon')),
    ],
    ids=['non-numeric-value', 'incomparable-interval'],
)
def test_an_unexpectedly_malformed_record_is_dropped_without_stopping_the_worker(malformed: MetricRecord):
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(malformed)
    sink.record(record('valid'))
    sink.close()

    assert [series['metric'] for series in submitter.series] == [f'{NAMESPACE}.valid']
    assert not submitter.distribution_requests
    assert any('could not be converted for submission' in notice for notice in diagnostics)


@pytest.mark.parametrize(
    ('kind', 'limit'),
    [
        (MetricKind.COUNT, REQUEST_BYTES_LIMIT),
        (MetricKind.DISTRIBUTION, DISTRIBUTION_REQUEST_BYTES_LIMIT),
    ],
    ids=['metrics', 'distributions'],
)
def test_an_oversized_series_is_dropped_with_a_notice(kind, limit):
    submitter = FakeMetricsSubmitter()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics)

    sink.record(record('huge', kind, tags={'blob': 'x' * (limit + 10)}))
    sink.close()

    assert not submitter.series
    assert not submitter.distributions
    assert any('exceeded the' in notice for notice in diagnostics)


def test_a_full_queue_drops_metrics_instead_of_blocking_the_emitter():
    submitter = FakeMetricsSubmitter()
    submitter.block_submissions()
    diagnostics: list[str] = []
    sink = make_sink(submitter, diagnostics, queue_size=2)

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
    sink = make_sink(submitter, diagnostics)

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

    sink.record(record('first'))
    sink.close()

    assert [series['metric'] for series in submitter.series] == []


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
    sink = make_sink(submitter, diagnostics)
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
