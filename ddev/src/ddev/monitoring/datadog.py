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
from typing import NamedTuple, Protocol

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.http_log import HTTPLog
from datadog_api_client.v2.model.http_log_item import HTTPLogItem

# Datadog's documented intake limits are 1,000 entries and 5 MiB per request, and 1 MiB per log
# (https://docs.datadoghq.com/api/latest/logs/). The handler stays below all three to leave room
# for request encoding overhead.
ENTRY_SIZE_LIMIT = 256 * 1024
REQUEST_ENTRIES_LIMIT = 500
REQUEST_BYTES_LIMIT = 4 * 1024 * 1024

WORKER_POLL_SECONDS = 0.2
DIAGNOSTIC_WINDOW_SECONDS = 60.0

type DiagnosticSink = Callable[[str], None]


class LogSubmitter(Protocol):
    def submit_log(self, body: HTTPLog) -> object: ...


class QueuedLog(NamedTuple):
    item: HTTPLogItem
    size: int


class DatadogLogHandler(logging.Handler):
    """Deliver formatter-produced JSON objects to Datadog Logs without blocking emitters."""

    def __init__(
        self,
        *,
        api_key: str,
        site: str = 'datadoghq.com',
        level: int = logging.DEBUG,
        diagnostics: DiagnosticSink | None = None,
        queue_size: int = 10_000,
        submitter: LogSubmitter | None = None,
    ) -> None:
        super().__init__(level=level)
        self._diagnostics = diagnostics
        self._queue: queue.Queue[QueuedLog | None] = queue.Queue(maxsize=queue_size)
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
        self._close_lock = threading.Lock()
        self._diagnostic_lock = threading.Lock()
        self._diagnostic_at: float | None = None
        self._diagnostic_skipped = 0
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
            size = len(rendered.encode('utf-8'))
        except Exception as error:
            self._diagnose(f'a log could not be formatted and was dropped: {type(error).__name__}: {error}')
            return
        if size > ENTRY_SIZE_LIMIT:
            self._diagnose(f'a {size}-byte log exceeded the {ENTRY_SIZE_LIMIT}-byte entry limit and was dropped')
            return
        try:
            self._queue.put_nowait(QueuedLog(item, size))
        except queue.Full:
            self._diagnose('the export queue is full; logs are being dropped')

    def close(self, timeout: float = 10.0) -> None:
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
            dropped = self._drop_queued_logs()
            self._diagnose(f'export did not finish within its deadline; {dropped} queued log(s) were dropped')
        super().close()

    def _work(self) -> None:
        pending: list[QueuedLog] = []
        pending_bytes = 0
        try:
            while True:
                try:
                    entry = self._queue.get(timeout=WORKER_POLL_SECONDS)
                except queue.Empty:
                    if pending:
                        self._submit(pending)
                        pending = []
                        pending_bytes = 0
                    if self._closed:
                        break
                    continue
                if entry is None:  # Shutdown sentinel.
                    self._submit(pending)
                    break
                if pending and (
                    len(pending) >= REQUEST_ENTRIES_LIMIT or pending_bytes + entry.size > REQUEST_BYTES_LIMIT
                ):
                    self._submit(pending)
                    pending = []
                    pending_bytes = 0
                pending.append(entry)
                pending_bytes += entry.size
                if len(pending) >= REQUEST_ENTRIES_LIMIT or pending_bytes >= REQUEST_BYTES_LIMIT:
                    self._submit(pending)
                    pending = []
                    pending_bytes = 0
        finally:
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

    def _submit(self, entries: list[QueuedLog]) -> None:
        if not entries:
            return
        try:
            self._submitter.submit_log(body=HTTPLog([entry.item for entry in entries]))
        except Exception as error:
            self._diagnose(f'submitting {len(entries)} log(s) failed: {type(error).__name__}: {error}')

    def _close_api_client(self) -> None:
        api_client, self._api_client = self._api_client, None
        if api_client is not None:
            api_client.close()

    @staticmethod
    def _log_item(rendered: str) -> HTTPLogItem:
        attributes = json.loads(rendered)
        if not isinstance(attributes, dict):
            raise TypeError('the formatter must produce a JSON object')
        if not isinstance(attributes.get('message'), str):
            raise TypeError('the formatted JSON object must contain a string message')
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in attributes.items()):
            raise TypeError('Datadog log attributes must be strings')
        return HTTPLogItem(**attributes)

    def _diagnose(self, text: str) -> None:
        """Report delivery failures outside logging, limiting repeated notices."""
        now = time.monotonic()
        with self._diagnostic_lock:
            if self._diagnostic_at is not None and now - self._diagnostic_at < DIAGNOSTIC_WINDOW_SECONDS:
                self._diagnostic_skipped += 1
                return
            self._diagnostic_at = now
            skipped, self._diagnostic_skipped = self._diagnostic_skipped, 0
        if skipped:
            text = f'{text} (plus {skipped} earlier notices suppressed)'
        if self._diagnostics is None:
            return
        try:
            self._diagnostics(text)
        except Exception:
            pass  # Diagnostics cannot interrupt logging.
