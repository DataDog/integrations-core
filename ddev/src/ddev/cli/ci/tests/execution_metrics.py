# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Reusable metrics helpers for the Dispatcher's processors and its command."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Any

from ddev.cli.ci.tests.status import Status
from ddev.monitoring import ComponentMonitor
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

    RESOLVE_RUN = auto()
    RESOLVE_CHANGES = auto()
    BUILD_PLAN = auto()
    DISPATCH_BATCH = auto()
    FETCH_WORKFLOW = auto()
    REFRESH_JOBS = auto()
    COLLECT_ARTIFACTS = auto()
    GATHER_BATCH_RESULTS = auto()
    PUBLISH_REPORT = auto()


class OperationResult(StrEnum):
    SUCCESS = auto()
    FAILURE = auto()


@dataclass
class OperationFailure:
    """One recorded cause of a failed operation."""

    message: str
    args: tuple[Any, ...] = ()
    fields: dict[str, Any] = field(default_factory=dict)
    # Captured in `fail`, where the exception is still being handled.
    exc_info: Any = None

    def render(self) -> str:
        return self.message % self.args if self.args else self.message

    def entry(self) -> dict[str, Any]:
        return {'message': self.render(), **self.fields}


@dataclass
class OperationState:
    """State of one operation, settled by `MetricsHelper.operation`."""

    failures: list[OperationFailure] = field(default_factory=list)
    abandoned: bool = False

    @property
    def failed(self) -> bool:
        return bool(self.failures)

    def fail(self, message: str, *args: Any, exc_info: bool = False, **fields: Any) -> None:
        """Mark the operation failed. Each cause is listed on the one settle log line."""
        self.failures.append(OperationFailure(message, args, fields, sys.exc_info() if exc_info else None))

    def abandon(self) -> None:
        """Record nothing for this operation."""
        self.abandoned = True


def report_result(metrics: Metrics, family: str, result: ResultMetric, **tags: Any) -> None:
    """Emit every result counter of a family as 0/1, exactly one being 1, so monitors see zeros, not gaps."""
    for candidate in ResultMetric:
        metrics.count(f'{family}.{candidate.value}', int(candidate is result), **tags)


class MetricsHelper:
    """Operation counters, durations and settle log lines for one component."""

    def __init__(self, monitor: ComponentMonitor, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._metrics = monitor.metrics
        self._logger = monitor.logger
        self._clock = clock

    @contextmanager
    def operation(self, operation: Operation) -> Iterator[OperationState]:
        """Settle counters, duration and one log line when the body ends.

        An escaped `Exception` fails the operation and propagates. Cancellation and other
        `BaseException`s settle nothing.
        """
        state = OperationState()
        start = self._clock()
        try:
            yield state
        except Exception as error:
            self._settle(operation, state, start, escaped=error)
            raise
        else:
            self._settle(operation, state, start)

    def _settle(
        self, operation: Operation, state: OperationState, start: float, *, escaped: Exception | None = None
    ) -> None:
        if state.abandoned:
            return
        failed = escaped is not None or state.failed
        result = OperationResult.FAILURE if failed else OperationResult.SUCCESS
        elapsed = self._clock() - start
        fields: dict[str, Any] = {
            'operation': operation,
            'operation_result': result,
            'operation_duration_seconds': elapsed,
        }
        metrics = self._metrics
        metrics.count('operations.count', 1, operation=operation)
        metrics.count('operations.failed', int(failed), operation=operation)
        metrics.distribution('operation.duration', elapsed, operation=operation, operation_result=result)
        if not failed:
            self._logger.info('Operation %s succeeded in %gs', operation.value, elapsed, **fields)
            return
        failures = state.failures
        if failures:
            message = '; '.join(failure.render() for failure in failures)
            fields['operation_failures'] = [failure.entry() for failure in failures]
        elif escaped is not None and str(escaped):
            message = f'Operation {operation.value} failed: {escaped}'
        else:
            message = f'Operation {operation.value} failed'
        if escaped is not None:
            self._logger.error(message, exc_info=True, **fields)
        else:
            exc_info = next((failure.exc_info for failure in failures if failure.exc_info is not None), False)
            self._logger.warning(message, exc_info=exc_info, **fields)
