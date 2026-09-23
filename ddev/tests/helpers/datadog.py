# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Test support for code that submits Datadog logs and metrics."""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Mapping
from pprint import pformat

from datadog_api_client.v1.model.distribution_points_payload import DistributionPointsPayload
from datadog_api_client.v2.model.http_log import HTTPLog
from datadog_api_client.v2.model.metric_payload import MetricPayload

type SubmittedLog = dict[str, object]
type SubmittedSeries = dict[str, object]


class SubmissionRecorder:
    """Failure and blocking controls shared by fake submitters."""

    def __init__(self) -> None:
        self._failures: deque[Exception] = deque()
        self._submission_gate = threading.Event()
        self._submission_gate.set()
        self._submission_started = threading.Semaphore(0)

    def begin_submission(self) -> None:
        self._submission_started.release()
        if not self._submission_gate.wait(timeout=5):
            raise RuntimeError('test intake remained blocked')
        if self._failures:
            raise self._failures.popleft()

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


class FakeLogSubmitter(SubmissionRecorder):
    """Record submitted logs with optional failures and blocking."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[list[SubmittedLog]] = []

    @property
    def logs(self) -> list[SubmittedLog]:
        return [log for request in self.requests for log in request]

    def submit_log(self, body: HTTPLog) -> object:
        self.begin_submission()
        self.requests.append([item.to_dict() for item in body.value])
        return {}

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


class FakeMetricsSubmitter(SubmissionRecorder):
    """Record submitted metrics with optional failures and blocking."""

    def __init__(self) -> None:
        super().__init__()
        self.metric_requests: list[list[SubmittedSeries]] = []
        self.distribution_requests: list[list[SubmittedSeries]] = []

    @property
    def series(self) -> list[SubmittedSeries]:
        return [series for request in self.metric_requests for series in request]

    @property
    def distributions(self) -> list[SubmittedSeries]:
        return [series for request in self.distribution_requests for series in request]

    def submit_metrics(self, body: MetricPayload) -> object:
        self.begin_submission()
        self.metric_requests.append([series.to_dict() for series in body.series])
        return {}

    def submit_distribution_points(self, body: DistributionPointsPayload) -> object:
        self.begin_submission()
        self.distribution_requests.append([series.to_dict() for series in body.series])
        return {}
