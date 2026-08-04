# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the aggregate progress objects the gatherer publishes to the PR updater.

These types are pure data: no GitHub calls, no filesystem. What is worth testing is the derived
reporting rules the design doc pins down — a logical job's history can be sparse, only its latest
execution counts, and a planned job with no execution yet is not complete.
"""

from __future__ import annotations

import dataclasses

import pytest

from ddev.cli.ci.tests.messages import BatchJob, Platform
from ddev.cli.ci.tests.progress import (
    BatchProgress,
    DispatcherProgress,
    ExecutionState,
    JobAttemptProgress,
    JobProgress,
)
from ddev.cli.ci.tests.status import Status
from ddev.utils.junit import JUnitCounts, JUnitReport, JUnitResult, JUnitResultKind, JUnitTestCase, JUnitTestSuite

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _batch_job(name: str = "j1", target: str = "ntp") -> BatchJob:
    return BatchJob(
        name=name,
        target=target,
        runner="ubuntu-latest",
        environment="py3.13",
        platform=Platform.LINUX,
        unit_tests=True,
        e2e_tests=False,
    )


def _attempt(attempt: int = 1, status: Status | None = Status.SUCCESS, **overrides) -> JobAttemptProgress:
    defaults = {
        "attempt": attempt,
        "job_id": 8100 + attempt,
        "status": status,
        "conclusion": None if status is None else str(status),
        "failed_steps": (),
        "job_url": f"https://github.com/o/r/actions/runs/1/job/{8100 + attempt}",
        "reports": (),
    }
    defaults.update(overrides)
    return JobAttemptProgress(**defaults)


def _case(name: str, kind: JUnitResultKind | None) -> JUnitTestCase:
    results = () if kind is None else (JUnitResult(kind=kind),)
    return JUnitTestCase(classname="tests.test_check", name=name, time=0.1, results=results)


def _report(*cases: JUnitTestCase, suites: int = 1) -> JUnitReport:
    counts = JUnitCounts(tests=len(cases), failures=0, errors=0, skipped=0)
    suite = JUnitTestSuite(name="pytest", reported_counts=counts, time=1.0, timestamp=None, hostname=None)
    return JUnitReport(
        name="pytest",
        test_suites=tuple(dataclasses.replace(suite, test_cases=cases) for _ in range(suites)),
    )


def _job(*attempts: JobAttemptProgress, name: str = "j1", target: str = "ntp") -> JobProgress:
    return JobProgress(job=_batch_job(name, target), attempts=attempts)


def _batch(*jobs: JobProgress, batch_id: str = "batch-01", **overrides) -> BatchProgress:
    defaults = {
        "batch_id": batch_id,
        "run_id": 1,
        "workflow_url": "https://github.com/o/r/actions/runs/1",
        "state": ExecutionState.FINISHED,
        "status": Status.SUCCESS,
        "current_attempt": 1,
        "max_attempts": 1,
        "retries_remaining": 0,
        "retrying_jobs": (),
        "jobs": jobs,
    }
    defaults.update(overrides)
    return BatchProgress(**defaults)


# ---------------------------------------------------------------------------
# JobProgress
# ---------------------------------------------------------------------------


def test_latest_is_none_without_attempts() -> None:
    job = _job()
    assert job.latest is None
    assert job.retry_count == 0


def test_latest_is_the_last_attempt() -> None:
    job = _job(_attempt(1, Status.FAILURE), _attempt(2, Status.SUCCESS))
    assert job.latest is not None
    assert job.latest.attempt == 2
    assert job.latest.status == Status.SUCCESS
    assert job.retry_count == 1


def test_retry_count_is_execution_count_minus_one_over_a_sparse_history() -> None:
    # A logical job may execute in attempts 1 and 3 without executing in attempt 2: retry count is
    # execution count minus one, never ``run_attempt - 1``.
    job = _job(_attempt(1, Status.FAILURE), _attempt(3, Status.SUCCESS))
    assert job.retry_count == 1
    assert job.latest is not None
    assert job.latest.attempt == 3


def test_failed_tests_flattens_failures_and_errors_across_suites() -> None:
    attempt = _attempt(
        status=Status.FAILURE,
        reports=(
            _report(
                _case("test_ok", None),
                _case("test_bad", JUnitResultKind.FAILURE),
                _case("test_boom", JUnitResultKind.ERROR),
                _case("test_skip", JUnitResultKind.SKIPPED),
                suites=2,
            ),
        ),
    )
    assert [case.name for case in attempt.failed_tests] == ["test_bad", "test_boom"] * 2


def test_failed_tests_is_empty_without_reports() -> None:
    assert _attempt().failed_tests == []


# ---------------------------------------------------------------------------
# DispatcherProgress counters
# ---------------------------------------------------------------------------


def test_counters_use_only_the_latest_attempt() -> None:
    # The retried job failed on attempt 1 and passed on attempt 2: it counts once, as passed.
    progress = DispatcherProgress(
        batches=(_batch(_job(_attempt(1, Status.FAILURE), _attempt(2, Status.SUCCESS))),),
        done=True,
    )
    assert (progress.passed, progress.failed, progress.skipped) == (1, 0, 0)
    assert progress.complete == 1
    assert progress.total == 1


def test_counters_sum_across_batches_and_statuses() -> None:
    progress = DispatcherProgress(
        batches=(
            _batch(
                _job(_attempt(status=Status.SUCCESS), name="j1"),
                _job(_attempt(status=Status.FAILURE), name="j2"),
                batch_id="batch-01",
            ),
            _batch(
                _job(_attempt(status=Status.SKIPPED), name="j3"),
                _job(_attempt(status=Status.SUCCESS), name="j4"),
                batch_id="batch-02",
            ),
        ),
        done=True,
    )
    assert (progress.passed, progress.failed, progress.skipped) == (2, 1, 1)
    assert (progress.complete, progress.total) == (4, 4)


def test_planned_jobs_count_toward_total_but_not_complete() -> None:
    progress = DispatcherProgress(
        batches=(
            _batch(_job(_attempt(status=Status.SUCCESS), name="j1"), batch_id="batch-01"),
            _batch(
                _job(name="j2"),
                _job(name="j3"),
                batch_id="batch-02",
                state=ExecutionState.PLANNED,
                status=None,
                run_id=None,
                workflow_url=None,
                current_attempt=None,
            ),
        ),
        done=False,
    )
    assert (progress.passed, progress.failed, progress.skipped) == (1, 0, 0)
    assert progress.complete == 1
    assert progress.total == 3


def test_an_attempt_without_an_outcome_is_not_complete() -> None:
    # An in-flight execution has no normalized status yet, so it cannot be counted anywhere.
    progress = DispatcherProgress(batches=(_batch(_job(_attempt(status=None)), status=None),), done=False)
    assert (progress.passed, progress.failed, progress.skipped, progress.complete) == (0, 0, 0, 0)
    assert progress.total == 1


def test_empty_progress_counts_zero() -> None:
    progress = DispatcherProgress(batches=(), done=False)
    assert (progress.passed, progress.failed, progress.skipped, progress.complete, progress.total) == (0, 0, 0, 0, 0)


# ---------------------------------------------------------------------------
# Immutability and defaults
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("instance", "field_name", "value"),
    [
        (_attempt(), "status", Status.FAILURE),
        (_job(), "attempts", ()),
        (_batch(), "state", ExecutionState.PLANNED),
        (DispatcherProgress(batches=(), done=False), "done", True),
    ],
    ids=["attempt", "job", "batch", "dispatcher"],
)
def test_progress_objects_are_immutable(instance: object, field_name: str, value: object) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, field_name, value)


def test_error_defaults_to_none() -> None:
    assert _attempt().error is None
    assert _batch().error is None
