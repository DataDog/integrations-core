# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""A buffered logging handler for Datadog Logs."""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from collections.abc import Callable
from contextlib import suppress
from typing import Protocol

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.http_log import HTTPLog
from datadog_api_client.v2.model.http_log_item import HTTPLogItem

from ddev.monitoring.diagnostics import DiagnosticCategory, RateLimitedDiagnostics, plain_diagnostic_sink
from ddev.monitoring.intake import RequestBatch, SubmissionStopped, submit_intake_batch

# Datadog's documented intake limit is 1,000 entries per request; the handler stays below it.
# Payload size is the server's call, answered by bisection when it rejects a request.
REQUEST_ENTRIES_LIMIT = 500

WORKER_POLL_SECONDS = 0.2


class LogSubmitter(Protocol):
    def submit_log(self, body: HTTPLog) -> object: ...


class DatadogLogHandler(logging.Handler):
    """Deliver formatter-produced JSON objects to Datadog Logs without blocking emitters."""

    def __init__(
        self,
        *,
        api_key: str,
        site: str = 'datadoghq.com',
        level: int = logging.DEBUG,
        diagnostics: Callable[[str], None] | None = None,
        queue_size: int = 10_000,
        submitter: LogSubmitter | None = None,
    ) -> None:
        super().__init__(level=level)
        self._diagnostics = RateLimitedDiagnostics(plain_diagnostic_sink(diagnostics))
        self._queue: queue.Queue[HTTPLogItem | None] = queue.Queue(maxsize=queue_size)
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
            self._api_client: ApiClient | None = ApiClient(configuration)
            self._submitter: LogSubmitter = LogsApi(self._api_client)
        else:
            self._api_client = None
            self._submitter = submitter
        self._closed = False
        self._drain_deadline: float | None = None
        self._close_lock = threading.Lock()
        self._worker = threading.Thread(target=self._work, name='datadog-log-handler', daemon=True)
        try:
            self._worker.start()
        except Exception:
            self._close_api_client()
            raise

    def emit(self, record: logging.LogRecord) -> None:
        if self._closed:
            return
        try:
            rendered = self.format(record)
            item = self._log_item(rendered)
        except Exception as error:
            self._diagnostics.report(
                DiagnosticCategory.CONVERSION,
                f'a log could not be formatted and was dropped: {type(error).__name__}: {error}',
            )
            return
        # Acceptance and enqueue are one critical section, so an accepted log always lands ahead
        # of the shutdown sentinel rather than stranded behind it.
        with self._close_lock:
            if self._closed:
                return
            try:
                self._queue.put_nowait(item)
                return
            except queue.Full:
                pass
        self._diagnostics.report(DiagnosticCategory.QUEUE_FULL, 'the export queue is full; logs are being dropped')

    def close(self, timeout: float = 10.0) -> None:
        """Stop accepting records and drain the queue within *timeout*."""
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
        self._worker.join(timeout=max(0.0, timeout))
        if self._worker.is_alive():
            dropped = self._drop_queued_logs()
            self._diagnostics.report(
                DiagnosticCategory.DEADLINE,
                f'export did not finish within its deadline; {dropped} queued log(s) were dropped',
            )
        self._diagnostics.summarize()
        super().close()

    def _work(self) -> None:
        pending = RequestBatch(self._submit, item_limit=REQUEST_ENTRIES_LIMIT)
        try:
            while True:
                try:
                    entry = self._queue.get(timeout=WORKER_POLL_SECONDS)
                except queue.Empty:
                    # An empty observation is stale the moment a log is accepted behind it:
                    # that log sits ahead of the sentinel, so the worker must recheck the
                    # queue under the lock that accepted it before exiting.
                    with self._close_lock:
                        shutdown = self._closed and self._queue.empty()
                    if shutdown:
                        break
                    pending.flush()
                    continue
                if entry is None:  # Shutdown sentinel.
                    break
                pending.add(entry)
        finally:
            pending.flush()
            self._close_api_client()

    def _drop_queued_logs(self) -> int:
        dropped = 0
        while True:
            try:
                entry = self._queue.get_nowait()
            except queue.Empty:
                return dropped
            if entry is not None:
                dropped += 1

    def _submissions_stopped(self) -> bool:
        deadline = self._drain_deadline
        return deadline is not None and time.monotonic() >= deadline

    def _send_logs(self, items: list[HTTPLogItem]) -> None:
        self._submitter.submit_log(body=HTTPLog(items))

    def _submit(self, items: list[HTTPLogItem]) -> None:
        try:
            submit_intake_batch(
                items,
                self._send_logs,
                on_rejected=self._rejected_log,
                should_stop=self._submissions_stopped,
            )
        except SubmissionStopped:
            self._diagnostics.report(
                DiagnosticCategory.DEADLINE,
                'the shutdown deadline stopped log submission; the remaining logs were dropped',
            )
        except Exception as error:
            self._diagnostics.report(
                DiagnosticCategory.SUBMISSION,
                f'submitting {len(items)} log(s) failed: {type(error).__name__}: {error}',
            )

    def _rejected_log(self, item: HTTPLogItem) -> None:
        self._diagnostics.report(
            DiagnosticCategory.OVERSIZED,
            'the API rejected a log as too large on its own and it was dropped',
        )

    def _close_api_client(self) -> None:
        api_client, self._api_client = self._api_client, None
        if api_client is None:
            return
        try:
            api_client.close()
        except Exception as error:
            self._diagnostics.report(
                DiagnosticCategory.CLIENT_CLOSE,
                f'closing the logs API client failed: {type(error).__name__}: {error}',
            )

    @staticmethod
    def _log_item(rendered: str) -> HTTPLogItem:
        attributes = json.loads(rendered)
        if not isinstance(attributes, dict):
            raise TypeError('the formatter must produce a JSON object')
        if not isinstance(attributes.get('message'), str):
            raise TypeError('the formatted JSON object must contain a string message')
        # The SDK schema types undeclared log attributes as strings, while Logs intake accepts JSON values.
        return HTTPLogItem(_check_type=False, **attributes)
