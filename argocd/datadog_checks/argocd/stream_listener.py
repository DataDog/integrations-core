# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Persistent listener for the ArgoCD application watch stream (/api/v1/stream/applications)."""

from __future__ import annotations

import json
import threading
from typing import TYPE_CHECKING

from .resources_constants import (
    GENRESOURCES_STREAM_EVENTS_METRIC,
    GENRESOURCES_STREAM_RECONNECTS_METRIC,
    GENRESOURCES_STREAM_UP_METRIC,
)

if TYPE_CHECKING:
    from .check import ArgocdCheck
    from .resources import ArgocdResourceCollector

STREAM_PATH = "/api/v1/stream/applications"
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 60
INITIAL_BACKOFF_SECONDS = 1


class ArgocdApplicationStreamListener:
    """Holds a persistent connection to the ArgoCD application watch stream and emits changes via the collector.

    Each watch event arrives as a line ``{"result": {"type": "ADDED|MODIFIED|DELETED", "application": {...}}}``;
    the embedded application is the same shape as a polled one, so it flows through the collector's existing
    sanitize/allow-list/dedup/submit pipeline unchanged. Runs on a single dedicated daemon thread: the clean
    shutdown path is ``cancel()`` (signal + close the socket) followed by ``join()``; ``daemon=True`` is only a
    backstop for a hard interpreter exit that never calls ``cancel()``.
    """

    def __init__(
        self,
        check: "ArgocdCheck",
        collector: "ArgocdResourceCollector",
        *,
        endpoint: str,
        auth_token: str | None,
        backoff_max_seconds: int,
    ) -> None:
        self.check = check
        self._collector = collector
        self._endpoint = endpoint.rstrip("/")
        self._auth_token = auth_token
        self._backoff_max = max(1, backoff_max_seconds)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._response = None

    def start(self) -> None:
        if self.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="argocd-genresources-stream", daemon=True)
        self._thread.start()

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def cancel(self) -> None:
        """Signal the loop to stop and close the active connection to unblock ``iter_lines``. Does not join."""
        self._stop.set()
        response = self._response
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def _sleep(self, seconds: float) -> None:
        """Interruptible backoff sleep that wakes immediately on cancel()."""
        self._stop.wait(seconds)

    def _run(self) -> None:
        backoff = INITIAL_BACKOFF_SECONDS
        while not self._stop.is_set():
            got_data = False
            try:
                got_data = self._stream_once()
            except Exception as exc:
                if not self._stop.is_set():
                    self.check.log.warning("genresources: application stream error: %s", exc)
            if self._stop.is_set():
                break
            # Back off on every disconnect (clean or error); reset only after a connection that
            # actually delivered data, so a server that closes on connect can't become a hot loop.
            self.check.gauge(GENRESOURCES_STREAM_UP_METRIC, 0)
            self.check.count(GENRESOURCES_STREAM_RECONNECTS_METRIC, 1)
            if got_data:
                backoff = INITIAL_BACKOFF_SECONDS
            self._sleep(backoff)
            if not got_data:
                backoff = min(backoff * 2, self._backoff_max)
        self.check.gauge(GENRESOURCES_STREAM_UP_METRIC, 0)

    def _stream_once(self) -> bool:
        """Open the stream and process events until it ends or stop is signaled; return True if any line arrived."""
        url = self._endpoint + STREAM_PATH
        kwargs: dict = {"stream": True, "timeout": (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)}
        if self._auth_token:
            kwargs["headers"] = {"Authorization": f"Bearer {self._auth_token}"}
        response = self.check.http.get(url, **kwargs)
        self._response = response
        got_data = False
        try:
            response.raise_for_status()
            self.check.gauge(GENRESOURCES_STREAM_UP_METRIC, 1)
            for line in response.iter_lines():
                if self._stop.is_set():
                    break
                if line:
                    got_data = True
                    self._handle_line(line)
        finally:
            self._response = None
            response.close()
        return got_data

    def _handle_line(self, line: bytes) -> None:
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            return
        result = event.get("result") if isinstance(event, dict) else None
        if not isinstance(result, dict):
            return
        application = result.get("application")
        if not isinstance(application, dict):
            return
        self.check.count(GENRESOURCES_STREAM_EVENTS_METRIC, 1)
        if result.get("type") == "DELETED":
            self._collector.forget_application(application)
        else:
            self._collector.emit_stream_application(application)
