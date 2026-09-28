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

from ddev.monitoring.metrics import Metrics


class ExecutionOutcome(StrEnum):
    """Terminal command outcomes, including modes that skip execution."""

    NO_OP = 'no-op'
    PASSED = auto()
    FAILED = auto()
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


class MetricsHelper:
    """Operation metrics for one component, built from that component's own monitor."""

    def __init__(self, metrics: Metrics, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._metrics = metrics
        self._clock = clock

    def record_operation(self, operation: Operation, *, failed: bool) -> None:
        """Emit one logical operation's outcome after retries and fallbacks settle."""
        self._metrics.count('operations.count', 1, operation=operation)
        self._metrics.count('operations.failed', int(failed), operation=operation)

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
