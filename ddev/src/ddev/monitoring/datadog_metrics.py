# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""A buffered metrics sink delivering finalized records to Datadog Metrics."""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Callable
from contextlib import suppress
from math import isfinite
from typing import Any, Protocol

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

from ddev.monitoring.diagnostics import DiagnosticSink, RateLimitedDiagnostics
from ddev.monitoring.metrics import MetricKind, MetricRecord

# Datadog's documented intake limits are 512,000 bytes per metrics request and 3,200,000 bytes per
# distribution-points request (https://docs.datadoghq.com/api/latest/metrics/). The byte limits
# below stay under them to leave room for request encoding overhead, and the series limits keep
# one request cheap to build.
REQUEST_BYTES_LIMIT = 400 * 1024
DISTRIBUTION_REQUEST_BYTES_LIMIT = 3 * 1024 * 1024
REQUEST_SERIES_LIMIT = 50
DISTRIBUTION_REQUEST_SERIES_LIMIT = 100

WORKER_POLL_SECONDS = 0.2
CLOSE_DRAIN_SECONDS = 10.0


class MetricsSubmitter(Protocol):
    def submit_metrics(self, body: MetricPayload) -> object: ...

    def submit_distribution_points(self, body: DistributionPointsPayload) -> object: ...


class DatadogMetricsApis:
    """The v2 and v1 metric submissions over one API client."""

    def __init__(self, client: ApiClient) -> None:
        self._v2 = MetricsApiV2(client)
        self._v1 = MetricsApiV1(client)

    def submit_metrics(self, body: MetricPayload) -> object:
        return self._v2.submit_metrics(body)

    def submit_distribution_points(self, body: DistributionPointsPayload) -> object:
        return self._v1.submit_distribution_points(body)


class PendingSeries:
    """Series queued for one endpoint, flushed before a new entry could exceed a limit."""

    def __init__(self, submit: Callable[[list[Any]], None], *, series_limit: int, bytes_limit: int) -> None:
        self._submit = submit
        self._series_limit = series_limit
        self._bytes_limit = bytes_limit
        self._models: list[Any] = []
        self._bytes = 0

    def add(self, model: Any, size: int) -> None:
        if self._models and (len(self._models) >= self._series_limit or self._bytes + size > self._bytes_limit):
            self.flush()
        self._models.append(model)
        self._bytes += size

    def flush(self) -> None:
        models, self._models = self._models, []
        self._bytes = 0
        if models:
            self._submit(models)


class DatadogMetricsSink:
    """Deliver finalized metric records to Datadog without blocking emitters."""

    def __init__(
        self,
        *,
        api_key: str,
        namespace: str = '',
        site: str = 'datadoghq.com',
        diagnostics: DiagnosticSink | None = None,
        queue_size: int = 10_000,
        submitter: MetricsSubmitter | None = None,
    ) -> None:
        self._namespace = namespace
        self._queue: queue.Queue[MetricRecord | None] = queue.Queue(maxsize=queue_size)
        # Ownership state comes first so a failure while building the real submitter can clean up.
        self._diagnostics = RateLimitedDiagnostics(diagnostics)
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
        self._close_lock = threading.Lock()
        self._worker = threading.Thread(target=self._work, name='datadog-metrics-sink', daemon=True)
        try:
            self._worker.start()
        except Exception:
            self._close_api_client()
            raise

    def record(self, record: MetricRecord) -> None:
        if self._closed:
            return
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            self._diagnostics.report('the metrics export queue is full; metrics are being dropped')

    def close(self, timeout: float = CLOSE_DRAIN_SECONDS) -> None:
        """Stop accepting records and drain the queue within *timeout*."""
        if timeout < 0:
            raise ValueError('timeout must not be negative')
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
        with suppress(queue.Full):
            self._queue.put_nowait(None)
        self._worker.join(timeout=max(0.0, timeout))
        if self._worker.is_alive():
            dropped = self._drop_queued_records()
            self._diagnostics.report(
                f'metric export did not finish within its deadline; {dropped} queued metric(s) were dropped'
            )

    def _work(self) -> None:
        metrics = PendingSeries(
            self._submit_metrics, series_limit=REQUEST_SERIES_LIMIT, bytes_limit=REQUEST_BYTES_LIMIT
        )
        distributions = PendingSeries(
            self._submit_distributions,
            series_limit=DISTRIBUTION_REQUEST_SERIES_LIMIT,
            bytes_limit=DISTRIBUTION_REQUEST_BYTES_LIMIT,
        )
        try:
            while True:
                try:
                    record = self._queue.get(timeout=WORKER_POLL_SECONDS)
                except queue.Empty:
                    metrics.flush()
                    distributions.flush()
                    if self._closed:
                        break
                    continue
                if record is None:  # Shutdown sentinel.
                    metrics.flush()
                    distributions.flush()
                    break
                model, size = self._build(record)
                if model is None:
                    continue
                if record.kind is MetricKind.DISTRIBUTION:
                    distributions.add(model, size)
                else:
                    metrics.add(model, size)
        finally:
            self._close_api_client()

    def _build(self, record: MetricRecord) -> tuple[MetricSeries | DistributionPointsSeries | None, int]:
        try:
            reason = self._invalid_reason(record)
            if reason is not None:
                self._diagnostics.report(reason)
                return None, 0
            tags = [f'{name}:{value}' for name, value in sorted(record.tags.items())]
            if record.kind is MetricKind.DISTRIBUTION:
                series: MetricSeries | DistributionPointsSeries = DistributionPointsSeries(
                    metric=self._metric_name(record),
                    points=[DistributionPoint([record.timestamp, [record.value]])],
                    **({'tags': tags} if tags else {}),
                )
            else:
                kwargs: dict[str, Any] = {
                    'metric': self._metric_name(record),
                    'points': [MetricPoint(timestamp=record.timestamp, value=record.value)],
                    'type': MetricIntakeType.COUNT if record.kind is MetricKind.COUNT else MetricIntakeType.GAUGE,
                }
                if record.kind is MetricKind.COUNT:
                    # The v2 intake requires the window a count value covers.
                    kwargs['interval'] = record.interval if record.interval is not None else 1
                if record.unit is not None:
                    kwargs['unit'] = record.unit
                if tags:
                    kwargs['tags'] = tags
                series = MetricSeries(**kwargs)
            size = len(json.dumps(series.to_dict(), separators=(',', ':'), default=str).encode('utf-8'))
        except Exception as error:
            self._diagnostics.report(
                f'metric {record.name!r} could not be converted for submission: {type(error).__name__}: {error}'
            )
            return None, 0
        limit = (
            DISTRIBUTION_REQUEST_BYTES_LIMIT if isinstance(series, DistributionPointsSeries) else REQUEST_BYTES_LIMIT
        )
        if size > limit:
            self._diagnostics.report(
                f'a {size}-byte series for metric {record.name!r} exceeded the {limit}-byte request limit '
                'and was dropped'
            )
            return None, 0
        return series, size

    def _metric_name(self, record: MetricRecord) -> str:
        return f'{self._namespace}.{record.name}' if self._namespace else record.name

    @staticmethod
    def _invalid_reason(record: MetricRecord) -> str | None:
        # The intake would reject these, so they are dropped locally with a diagnostic instead.
        if not record.name:
            return 'a metric record without a name was dropped before submission'
        if not isfinite(record.value):
            return f'metric {record.name!r} has a non-finite value and was dropped before submission'
        if record.kind is MetricKind.COUNT and record.interval is not None and record.interval < 1:
            return f'metric {record.name!r} has a count interval below one second and was dropped before submission'
        return None

    def _submit_metrics(self, models: list[MetricSeries]) -> None:
        try:
            self._submitter.submit_metrics(body=MetricPayload(series=models))
        except Exception as error:
            self._diagnostics.report(f'submitting {len(models)} metric(s) failed: {type(error).__name__}: {error}')

    def _submit_distributions(self, models: list[DistributionPointsSeries]) -> None:
        try:
            self._submitter.submit_distribution_points(body=DistributionPointsPayload(series=models))
        except Exception as error:
            self._diagnostics.report(
                f'submitting {len(models)} distribution(s) failed: {type(error).__name__}: {error}'
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
            self._diagnostics.report(f'closing the metrics API client failed: {type(error).__name__}: {error}')
