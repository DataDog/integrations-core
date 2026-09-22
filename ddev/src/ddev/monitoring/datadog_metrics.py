# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Buffered delivery of metric records to Datadog."""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Mapping
from contextlib import suppress
from math import ceil, isfinite
from typing import NamedTuple, Protocol

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.metrics_api import MetricsApi as MetricsApiV1
from datadog_api_client.v1.model.distribution_point import DistributionPoint
from datadog_api_client.v1.model.distribution_points_payload import DistributionPointsPayload
from datadog_api_client.v1.model.distribution_points_series import DistributionPointsSeries
from datadog_api_client.v2.api.metrics_api import MetricsApi as MetricsApiV2
from datadog_api_client.v2.model.metric_intake_type import MetricIntakeType
from datadog_api_client.v2.model.metric_payload import MetricPayload
from datadog_api_client.v2.model.metric_point import MetricPoint
from datadog_api_client.v2.model.metric_series import MetricSeries

from ddev.monitoring.diagnostics import (
    DiagnosticCategory,
    DiagnosticSink,
    RateLimitedDiagnostics,
    plain_diagnostic_sink,
)
from ddev.monitoring.intake import RequestBatch, SubmissionStopped, submit_intake_batch
from ddev.monitoring.metrics import MetricKind, MetricRecord

REQUEST_SERIES_LIMIT = 50
DISTRIBUTION_REQUEST_SERIES_LIMIT = 100

WORKER_POLL_SECONDS = 0.2
CLOSE_DRAIN_SECONDS = 10.0
FLUSH_INTERVAL_SECONDS = 10.0
COUNT_WINDOW_SECONDS = 10.0
COUNT_WINDOW_SERIES_LIMIT = 10_000

type CountKey = tuple[str, tuple[tuple[str, str], ...]]


class MetricsSubmitter(Protocol):
    def submit_metrics(self, body: MetricPayload) -> object: ...

    def submit_distribution_points(self, body: DistributionPointsPayload) -> object: ...


class DatadogMetricsApis:
    """Submit counts and gauges through v2 and distributions through their v1 endpoint."""

    def __init__(self, client: ApiClient) -> None:
        self._v2 = MetricsApiV2(client)
        self._v1 = MetricsApiV1(client)

    def submit_metrics(self, body: MetricPayload) -> object:
        return self._v2.submit_metrics(body)

    def submit_distribution_points(self, body: DistributionPointsPayload) -> object:
        return self._v1.submit_distribution_points(body)


class CountedMetric(NamedTuple):
    name: str
    tags: Mapping[str, str]
    unit: str | None
    value: float


class QueuedMetric(NamedTuple):
    """A record paired with the clock readings taken atomically at queue acceptance.

    The monotonic reading schedules count windows and the wall reading timestamps count
    points, so window membership follows acceptance even when the emitter was paused
    before it.
    """

    record: MetricRecord
    monotonic: float
    timestamp: int


class CountSeries:
    def __init__(self, value: float, unit: str | None) -> None:
        self.total = value
        self.unit = unit


class CountWindow:
    """Emit one total per series/window because Datadog overwrites duplicate timestamps.

    A window opens at its first accepted increment and timestamps itself with that
    increment's acceptance wall time, so delivery delays cannot merge increments accepted
    in different windows. Units are metadata, not series identity; conflicting units
    cannot form separate totals.
    """

    def __init__(self, *, interval: float, series_limit: int) -> None:
        self._interval = interval
        self._series_limit = series_limit
        self._series: dict[CountKey, CountSeries] = {}
        self._opened: float | None = None
        self._timestamp = 0

    @property
    def closes_at(self) -> float | None:
        return None if self._opened is None else self._opened + self._interval

    def expired(self, now: float) -> bool:
        return self._opened is not None and now - self._opened >= self._interval

    def add(self, queued: QueuedMetric) -> tuple[DiagnosticCategory, str] | None:
        """Accumulate one increment, or return how the increment is refused."""
        record = queued.record
        if self._opened is None:
            self._opened = queued.monotonic
            self._timestamp = queued.timestamp
        key: CountKey = (record.name, tuple(sorted(record.tags.items())))
        series = self._series.get(key)
        if series is None:
            if len(self._series) >= self._series_limit:
                return (
                    DiagnosticCategory.QUEUE_FULL,
                    'the count collection window is full; increments for new metric series are being dropped',
                )
            self._series[key] = CountSeries(record.value, record.unit)
            return None
        if record.unit is not None and series.unit is not None and record.unit != series.unit:
            return (
                DiagnosticCategory.CONVERSION,
                f'metric {record.name!r} received counts with conflicting units; the increment was dropped',
            )
        total = series.total + record.value
        if not isfinite(total):
            return (
                DiagnosticCategory.CONVERSION,
                f'metric {record.name!r} counts summed to a non-finite value; the increment was dropped',
            )
        if record.unit is not None:
            series.unit = record.unit
        series.total = total
        return None

    def close(self, now: float | None = None) -> tuple[int, int, list[CountedMetric]]:
        """Drain totals with the nominal interval, or elapsed seconds for a partial shutdown window."""
        if self._opened is None:
            return (0, 0, [])
        seconds = max(1, ceil(self._interval if now is None else now - self._opened))
        timestamp = self._timestamp
        counted = [
            CountedMetric(name, dict(tags), series.unit, series.total) for (name, tags), series in self._series.items()
        ]
        self._series = {}
        self._opened = None
        self._timestamp = 0
        return timestamp, seconds, counted


class DatadogMetricsSink:
    """Queue metric records and submit bounded batches without blocking emitters."""

    def __init__(
        self,
        *,
        api_key: str,
        namespace: str = '',
        site: str = 'datadoghq.com',
        diagnostics: Callable[[str], None] | None = None,
        queue_size: int = 10_000,
        flush_interval: float = FLUSH_INTERVAL_SECONDS,
        submitter: MetricsSubmitter | None = None,
    ) -> None:
        if not isfinite(flush_interval) or flush_interval <= 0:
            raise ValueError('flush_interval must be a positive number of seconds')
        self._namespace = namespace
        self._queue: queue.Queue[QueuedMetric | None] = queue.Queue(maxsize=queue_size)
        self._flush_interval = flush_interval
        self._diagnostics = RateLimitedDiagnostics(plain_diagnostic_sink(diagnostics))
        self._api_client: ApiClient | None = None
        self._submitter: MetricsSubmitter
        if submitter is None:
            configuration = Configuration(
                api_key={'apiKeyAuth': api_key},
                server_index=0,
                server_variables={'site': site},
                request_timeout=(5.0, 15.0),
                enable_retry=True,
                max_retries=2,
                retry_backoff_factor=2.0,
            )
            self._api_client = ApiClient(configuration)
            try:
                self._submitter = DatadogMetricsApis(self._api_client)
            except Exception:
                self._close_api_client()
                raise
        else:
            self._submitter = submitter
        self._closed = False
        self._drain_deadline: float | None = None
        self._close_lock = threading.Lock()
        self._worker = threading.Thread(target=self._work, name='datadog-metrics-sink', daemon=True)
        try:
            self._worker.start()
        except Exception:
            self._close_api_client()
            raise

    @property
    def diagnostics(self) -> DiagnosticSink | None:
        # The rate limiter itself is the sink: emission failures and worker failures share one window.
        return self._diagnostics

    @diagnostics.setter
    def diagnostics(self, sink: DiagnosticSink | None) -> None:
        self._diagnostics.sink = sink

    def record(self, record: MetricRecord) -> None:
        # Acceptance, its clock pair, and the enqueue are one critical section: an accepted
        # record always lands ahead of the shutdown sentinel and is windowed by the instant
        # of acceptance, not by record construction.
        with self._close_lock:
            if self._closed:
                return
            try:
                self._queue.put_nowait(QueuedMetric(record, time.monotonic(), int(time.time())))
                return
            except queue.Full:
                pass
        self._diagnostics.report(
            DiagnosticCategory.QUEUE_FULL,
            'the metrics export queue is full; metrics are being dropped',
        )

    def close(self, timeout: float = CLOSE_DRAIN_SECONDS) -> None:
        """Stop accepting records and wait up to *timeout* for queued delivery."""
        if timeout < 0:
            raise ValueError('timeout must not be negative')
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
            # Submissions may continue until this deadline, not merely until close began.
            self._drain_deadline = time.monotonic() + timeout
            with suppress(queue.Full):
                self._queue.put_nowait(None)
        self._worker.join(timeout=timeout)
        if self._worker.is_alive():
            dropped = self._drop_queued_records()
            self._diagnostics.report(
                DiagnosticCategory.DEADLINE,
                f'metric export did not finish within its deadline; {dropped} queued metric(s) were dropped',
            )
        self._diagnostics.summarize()

    def _work(self) -> None:
        metrics = RequestBatch(self._submit_metrics, item_limit=REQUEST_SERIES_LIMIT)
        distributions = RequestBatch(self._submit_distributions, item_limit=DISTRIBUTION_REQUEST_SERIES_LIMIT)
        counts = CountWindow(interval=COUNT_WINDOW_SECONDS, series_limit=COUNT_WINDOW_SERIES_LIMIT)
        flush_at = time.monotonic() + self._flush_interval
        try:
            while True:
                now = time.monotonic()
                wait = min(WORKER_POLL_SECONDS, max(flush_at - now, 0.0))
                closes_at = counts.closes_at
                if closes_at is not None:
                    wait = min(wait, max(closes_at - now, 0.0))
                try:
                    queued = self._queue.get(timeout=wait)
                except queue.Empty:
                    # An empty observation is stale the moment a producer accepts behind it,
                    # and a producer between its clock capture and its enqueue holds the
                    # acceptance lock, so the idle decisions are made under that lock.
                    with self._close_lock:
                        if not self._queue.empty():
                            continue
                        now = time.monotonic()
                        shutdown = self._closed
                    if counts.expired(now):
                        self._add_counted(metrics, counts.close())
                    if shutdown:
                        break
                    if now >= flush_at:
                        metrics.flush()
                        distributions.flush()
                        flush_at = now + self._flush_interval
                    continue
                if queued is None:  # Shutdown sentinel.
                    if counts.expired(time.monotonic()):
                        self._add_counted(metrics, counts.close())
                    break
                now = time.monotonic()
                # Acceptance order is the queue order, so rollover follows acceptance time:
                # no increment accepted into the open window can still sit behind this record.
                closes_at = counts.closes_at
                if closes_at is not None and queued.monotonic >= closes_at:
                    self._add_counted(metrics, counts.close())
                if now >= flush_at:
                    metrics.flush()
                    distributions.flush()
                    flush_at = now + self._flush_interval
                self._add(queued, metrics, distributions, counts)
        finally:
            self._add_counted(metrics, counts.close(time.monotonic()))
            metrics.flush()
            distributions.flush()
            self._close_api_client()

    def _add(
        self,
        queued: QueuedMetric,
        metrics: RequestBatch[MetricSeries],
        distributions: RequestBatch[DistributionPointsSeries],
        counts: CountWindow,
    ) -> None:
        record = queued.record
        try:
            reason = self._invalid_reason(record)
            if reason is not None:
                self._diagnostics.report(DiagnosticCategory.CONVERSION, reason)
                return
            if record.kind is MetricKind.DISTRIBUTION:
                distributions.add(self._distribution_series(record))
            elif record.kind is MetricKind.COUNT:
                rejected = counts.add(queued)
                if rejected is not None:
                    category, message = rejected
                    self._diagnostics.report(category, message)
            else:
                metrics.add(self._metric_series(record))
        except Exception as error:
            self._diagnostics.report(
                DiagnosticCategory.CONVERSION,
                f'metric {record.name!r} could not be converted for submission: {type(error).__name__}: {error}',
            )

    def _add_counted(self, metrics: RequestBatch[MetricSeries], closed: tuple[int, int, list[CountedMetric]]) -> None:
        timestamp, interval, counted = closed
        for total in counted:
            # One failed conversion must not take its window siblings or the worker's cleanup down.
            try:
                metrics.add(self._count_series(total, timestamp, interval))
            except Exception as error:
                self._diagnostics.report(
                    DiagnosticCategory.CONVERSION,
                    f'metric {total.name!r} could not be converted for submission: {type(error).__name__}: {error}',
                )

    def _metric_series(self, record: MetricRecord) -> MetricSeries:
        series = MetricSeries(
            metric=self._metric_name(record.name),
            type=MetricIntakeType.GAUGE,
            points=[MetricPoint(timestamp=record.timestamp, value=record.value)],
        )
        if record.unit is not None:
            series.unit = record.unit
        tags = self._tags(record.tags)
        if tags:
            series.tags = tags
        return series

    def _count_series(self, counted: CountedMetric, timestamp: int, interval: int) -> MetricSeries:
        series = MetricSeries(
            metric=self._metric_name(counted.name),
            type=MetricIntakeType.COUNT,
            interval=interval,
            points=[MetricPoint(timestamp=timestamp, value=counted.value)],
        )
        if counted.unit is not None:
            series.unit = counted.unit
        tags = self._tags(counted.tags)
        if tags:
            series.tags = tags
        return series

    def _distribution_series(self, record: MetricRecord) -> DistributionPointsSeries:
        series = DistributionPointsSeries(
            metric=self._metric_name(record.name),
            points=[DistributionPoint([record.timestamp, [record.value]])],
        )
        tags = self._tags(record.tags)
        if tags:
            series.tags = tags
        return series

    def _metric_name(self, name: str) -> str:
        return f'{self._namespace}.{name}' if self._namespace else name

    @staticmethod
    def _tags(tags: Mapping[str, str]) -> list[str]:
        return [f'{tag}:{value}' for tag, value in sorted(tags.items())]

    @staticmethod
    def _invalid_reason(record: MetricRecord) -> str | None:
        if not record.name:
            return 'a metric record without a name was dropped before submission'
        if not isfinite(record.value):
            return f'metric {record.name!r} has a non-finite value and was dropped before submission'
        return None

    def _submissions_stopped(self) -> bool:
        deadline = self._drain_deadline
        return deadline is not None and time.monotonic() >= deadline

    def _send_metrics(self, series: list[MetricSeries]) -> None:
        self._submitter.submit_metrics(body=MetricPayload(series=series))

    def _send_distributions(self, series: list[DistributionPointsSeries]) -> None:
        self._submitter.submit_distribution_points(body=DistributionPointsPayload(series=series))

    def _submit_metrics(self, series: list[MetricSeries]) -> None:
        try:
            submit_intake_batch(
                series,
                self._send_metrics,
                on_rejected=self._rejected_series,
                should_stop=self._submissions_stopped,
            )
        except SubmissionStopped:
            self._diagnostics.report(
                DiagnosticCategory.DEADLINE,
                'the shutdown deadline stopped metric submission; the remaining series were dropped',
            )
        except Exception as error:
            self._diagnostics.report(
                DiagnosticCategory.SUBMISSION,
                f'submitting {len(series)} metric series failed: {type(error).__name__}: {error}',
            )

    def _submit_distributions(self, series: list[DistributionPointsSeries]) -> None:
        try:
            submit_intake_batch(
                series,
                self._send_distributions,
                on_rejected=self._rejected_series,
                should_stop=self._submissions_stopped,
            )
        except SubmissionStopped:
            self._diagnostics.report(
                DiagnosticCategory.DEADLINE,
                'the shutdown deadline stopped distribution submission; the remaining series were dropped',
            )
        except Exception as error:
            self._diagnostics.report(
                DiagnosticCategory.SUBMISSION,
                f'submitting {len(series)} distribution series failed: {type(error).__name__}: {error}',
            )

    def _rejected_series(self, series: MetricSeries | DistributionPointsSeries) -> None:
        self._diagnostics.report(
            DiagnosticCategory.OVERSIZED,
            f'the API rejected a series for metric {series.metric!r} as too large on its own and it was dropped',
        )

    def _drop_queued_records(self) -> int:
        dropped = 0
        while True:
            try:
                entry = self._queue.get_nowait()
            except queue.Empty:
                return dropped
            if entry is not None:
                dropped += 1

    def _close_api_client(self) -> None:
        api_client, self._api_client = self._api_client, None
        if api_client is None:
            return
        try:
            api_client.close()
        except Exception as error:
            self._diagnostics.report(
                DiagnosticCategory.CLIENT_CLOSE,
                f'closing the metrics API client failed: {type(error).__name__}: {error}',
            )
