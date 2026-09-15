# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Test support for code that submits Datadog logs."""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Mapping
from pprint import pformat

from datadog_api_client.v2.model.http_log import HTTPLog

type SubmittedLog = dict[str, object]


class FakeLogSubmitter:
    """Record submitted logs with optional failures and blocking."""

    def __init__(self) -> None:
        self.requests: list[list[SubmittedLog]] = []
        self._failures: deque[Exception] = deque()
        self._submission_gate = threading.Event()
        self._submission_gate.set()
        self._submission_started = threading.Semaphore(0)

    @property
    def logs(self) -> list[SubmittedLog]:
        return [log for request in self.requests for log in request]

    def submit_log(self, body: HTTPLog) -> object:
        self._submission_started.release()
        if not self._submission_gate.wait(timeout=5):
            raise RuntimeError('test intake remained blocked')
        if self._failures:
            raise self._failures.popleft()
        self.requests.append([item.to_dict() for item in body.value])
        return {}

    def fail_next(self, error: Exception, *, count: int = 1) -> None:
        if count < 0:
            raise ValueError('count must not be negative')
        self._failures.extend(error for _ in range(count))

    def block_submissions(self) -> None:
        self._submission_gate.clear()

    def resume_submissions(self) -> None:
        self._submission_gate.set()

    def wait_for_submission(self, timeout: float = 5) -> bool:
        return self._submission_started.acquire(timeout=timeout)

    def assert_logs(self, *expected: Mapping[str, object]) -> None:
        actual = self.logs
        expected_logs = [dict(log) for log in expected]
        assert actual == expected_logs, f'expected logs:\n{pformat(expected_logs)}\nactual logs:\n{pformat(actual)}'

    def assert_log_matches(self, expected: Mapping[str, object]) -> SubmittedLog:
        matches = [log for log in self.logs if all(log.get(key) == value for key, value in expected.items())]
        assert len(matches) == 1, (
            f'expected one log matching:\n{pformat(dict(expected))}\nfound {len(matches)} in:\n{pformat(self.logs)}'
        )
        return matches[0]

    def assert_no_logs(self) -> None:
        self.assert_logs()
