# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Reusable metrics helpers for the Dispatcher's processors and its command."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any

from structlog.stdlib import BoundLogger

from ddev.cli.ci.tests.status import Status
from ddev.monitoring.metrics import Metrics


class ResultMetric(StrEnum):
    """Metric result of a batch or job.

    `TIMED_OUT` has no `Status`: a timeout is a failure internally, but its counter stays apart from
    `failed`.
    """

    PASSED = auto()
    FAILED = auto()
    SKIPPED = auto()
    CANCELLED = auto()
    INCONCLUSIVE = auto()
    TIMED_OUT = auto()


_STATUS_RESULTS = {
    Status.SUCCESS: ResultMetric.PASSED,
    Status.FAILURE: ResultMetric.FAILED,
    Status.SKIPPED: ResultMetric.SKIPPED,
    Status.CANCELLED: ResultMetric.CANCELLED,
    Status.INCONCLUSIVE: ResultMetric.INCONCLUSIVE,
}


def result_metric(status: Status, *, timed_out: bool = False) -> ResultMetric:
    """The one mapping from a status, with a timeout split off, to its counter's name."""
    if timed_out:
        return ResultMetric.TIMED_OUT
    return _STATUS_RESULTS[status]


class ExecutionOutcome(StrEnum):
    """Terminal command outcomes, including modes that skip execution.

    `TESTS_FAILED` is a run the Dispatcher carried through whose tests failed. `FAILED` is a run the
    Dispatcher itself could not carry through: a crash, a batch it lost track of or a report it could
    not publish.
    """

    NO_OP = 'no-op'
    PASSED = auto()
    TESTS_FAILED = 'tests-failed'
    FAILED = auto()
    TIMED_OUT = 'timed-out'
    CANCELLED = auto()
    PLANNING_FAILED = 'planning-failed'
    RESOLVED = auto()
    DRY_RUN = 'dry-run'


class Operation(StrEnum):
    """One logical component operation, settled only after retries and fallbacks."""

    DISPATCH_BATCH = auto()
    FETCH_WORKFLOW = auto()
    REFRESH_JOBS = auto()
    COLLECT_ARTIFACTS = auto()
    GATHER_BATCH_RESULTS = auto()
    PUBLISH_REPORT = auto()


@dataclass
class OperationResult:
    """The outcome of one logical operation, including cancellation."""

    failed: bool = False
    cancelled: bool = False


def report_result(metrics: Metrics, family: str, result: ResultMetric, **tags: Any) -> None:
    """Emit every result counter of a family as 0/1, exactly one being 1, so monitors see zeros, not gaps."""
    for candidate in ResultMetric:
        metrics.count(f'{family}.{candidate.value}', int(candidate is result), **tags)


class MetricsHelper:
    """Operation metrics for one component, built from that component's own monitor."""

    def __init__(self, metrics: Metrics, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._metrics = metrics
        self._clock = clock

    def record_operation(self, operation: Operation, *, failed: bool) -> None:
        """Emit one logical operation's outcome after retries and fallbacks settle."""
        self._metrics.count('operations.count', 1, operation=operation)
        self._metrics.count('operations.failed', int(failed), operation=operation)

    def log_failed_operation(
        self,
        operation: Operation,
        logger: BoundLogger,
        message: str,
        *args: Any,
        recovered: bool = False,
        exc_info: bool = False,
        **fields: Any,
    ) -> None:
        """Log a failed operation: an error when it escaped, a warning when the processor recovered.

        Does not record the metric; `record_operation` or `time_operation` does.
        """
        (logger.warning if recovered else logger.error)(
            message, *args, operation=operation, exc_info=exc_info, **fields
        )

    @contextmanager
    def time_operation(self, operation: Operation, *, duration_metric: str) -> Iterator[OperationResult]:
        """Mark recovered failures through `result.failed`; escaped exceptions propagate.

        Cancellation reports elapsed time but not a settled operation outcome.
        """
        result = OperationResult()
        start = self._clock()
        try:
            yield result
        except Exception:
            result.failed = True
            raise
        except BaseException:
            result.cancelled = True
            raise
        finally:
            elapsed = self._clock() - start
            if not result.cancelled:
                self.record_operation(operation, failed=result.failed)
            self._metrics.distribution(duration_metric, elapsed, operation=operation)
