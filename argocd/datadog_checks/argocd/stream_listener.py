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
    auth_headers,
)

if TYPE_CHECKING:
    from datadog_checks.base.utils.http_protocol import HTTPClient, HTTPResponse

    from .check import ArgocdCheck
    from .resources import ArgocdResourceCollector

STREAM_PATH = "/api/v1/stream/applications"
CONNECT_TIMEOUT_SECONDS = 10
INITIAL_BACKOFF_SECONDS = 1


class ArgocdApplicationStreamListener:
    """Holds a persistent connection to the ArgoCD application watch stream and emits changes via the collector.

    Each watch event arrives as a line ``{"result": {"type": "ADDED|MODIFIED|DELETED", "application": {...}}}``;
    the embedded application is the same shape as a polled one, so it flows through the collector's existing
    sanitize/allow-list/dedup/submit pipeline unchanged. Runs on a single dedicated daemon thread. The clean
    shutdown path is ``cancel()`` (signal the loop and close the socket to unblock ``iter_lines``); it does not
    block, and callers may ``join()`` afterwards to wait. ``daemon=True`` is only a backstop for a hard
    interpreter exit that never calls ``cancel()``.

    Metrics (``count``) and generic resources (``submit_generic_resource`` via the collector) are submitted
    directly from this thread; the Datadog aggregator tolerates concurrent submission (same pattern as
    ``DBMAsyncJob``), and submitting inline is what makes stream updates near-real-time.
    """

    def __init__(
        self,
        check: "ArgocdCheck",
        collector: "ArgocdResourceCollector",
        *,
        endpoint: str,
        auth_token: str | None,
        backoff_max_seconds: int,
        read_timeout_seconds: int,
        http: "HTTPClient",
    ) -> None:
        self.check = check
        self._collector = collector
        self._http = http
        self._endpoint = endpoint.rstrip("/")
        self._auth_token = auth_token
        self._backoff_max = max(1, backoff_max_seconds)
        self._read_timeout = max(1, read_timeout_seconds)
        self._stop = threading.Event()
        self._connected = threading.Event()
        self._thread: threading.Thread | None = None
        self._response: HTTPResponse | None = None

    def start(self) -> None:
        if self.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="argocd-genresources-stream", daemon=True)
        self._thread.start()

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def is_connected(self) -> bool:
        """True while the watch stream is open; read from the check thread to emit the stream.up gauge."""
        return self._connected.is_set()

    def cancel(self) -> None:
        """Signal the loop to stop and close the active connection to unblock ``iter_lines``. Does not block."""
        self._stop.set()
        # If cancel lands in the narrow window between _stream_once's get() returning and its
        # ``self._response = response``, we see None and skip close(); the thread still exits on its next
        # _stop check, at worst after the read timeout. Bounded shutdown latency on a daemon thread, not a leak.
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
            got_data = self._stream_once()  # never raises; it reports connection errors as a False return
            if self._stop.is_set():
                break
            # Back off on every disconnect (clean or error); reset only after a connection that
            # actually delivered data, so a server that closes on connect can't become a hot loop.
            self.check.count(GENRESOURCES_STREAM_RECONNECTS_METRIC, 1)
            if got_data:
                backoff = INITIAL_BACKOFF_SECONDS
            self._sleep(backoff)
            if not got_data:
                backoff = min(backoff * 2, self._backoff_max)

    def _stream_once(self) -> bool:
        """Open the stream and process events until it ends, errors, or stop is signaled.

        Catches connection errors internally (the supervisor loop never sees them) and returns whether any
        line arrived before the connection ended -- including when it ended by raising -- so a connection
        that actually delivered data resets the backoff regardless of how it dropped.
        """
        url = self._endpoint + STREAM_PATH
        kwargs: dict = {
            "stream": True,
            "timeout": (CONNECT_TIMEOUT_SECONDS, self._read_timeout),
        }
        # Pass a dedicated genresources token only when set, via extra_headers (merges with configured
        # headers). Omit it otherwise: even an empty extra_headers makes RequestsWrapper snapshot the default
        # headers before its auth_token handler writes the inherited token, which would drop that auth.
        headers = auth_headers(self._auth_token)
        if headers:
            kwargs["extra_headers"] = headers
        got_data = False
        response = None
        try:
            response = self._http.get(url, **kwargs)
            self._response = response
            response.raise_for_status()
            self._connected.set()
            for line in response.iter_lines():
                if self._stop.is_set():
                    break
                if line:
                    got_data = True
                    try:
                        self._handle_line(line)
                    except Exception:
                        self.check.log.warning("genresources: failed to handle stream line", exc_info=True)
        except Exception as exc:
            if not self._stop.is_set():
                self.check.log.warning("genresources: application stream error: %s", exc)
        finally:
            self._connected.clear()
            self._response = None
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
        return got_data

    def _handle_line(self, line: bytes) -> None:
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            self.check.log.debug("genresources: ignoring malformed stream frame", exc_info=True)
            return
        result = event.get("result") if isinstance(event, dict) else None
        if not isinstance(result, dict):
            return
        application = result.get("application")
        if not isinstance(application, dict):
            return
        self.check.count(GENRESOURCES_STREAM_EVENTS_METRIC, 1)
        event_type = result.get("type")
        if event_type == "DELETED":
            self._collector.forget_application(application)
        elif event_type in ("ADDED", "MODIFIED"):
            self._collector.emit_stream_application(application)
