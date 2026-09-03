# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Builders shared by the Dispatcher batching, gatherer, renderer and run reporter tests."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable, Sequence

from ddev.cli.ci.tests.batching.units import ResolvedEnvironment, TestUnit
from ddev.cli.ci.tests.messages import BatchJob, TestBatch
from ddev.cli.ci.tests.progress import (
    BatchProgress,
    DispatcherProgress,
    ExecutionState,
    JobAttemptProgress,
    JobProgress,
    ProgressError,
)
from ddev.cli.ci.tests.status import Status
from ddev.event_bus.orchestrator import BaseMessage
from ddev.utils.git import ChangedFile, ChangeType
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import IssueComment
from ddev.utils.github_async.models.workflow import WorkflowJobConclusion
from ddev.utils.junit import JUnitCounts, JUnitReport, JUnitResult, JUnitResultKind, JUnitTestCase, JUnitTestSuite
from ddev.utils.platform import PlatformName

DEFAULT_PYTHON_VERSION = "3.13"
DEFAULT_RUNNER_LABELS = ("ubuntu-22.04",)


def env(
    name: str,
    platform: PlatformName = PlatformName.LINUX,
    *,
    python_version: str = DEFAULT_PYTHON_VERSION,
    unit: bool = True,
    e2e: bool = False,
) -> ResolvedEnvironment:
    return ResolvedEnvironment(
        name=name,
        platform=platform,
        python_version=python_version,
        test_available=unit,
        e2e_available=e2e,
    )


def make_unit(
    target: str = "postgres",
    *,
    name: str | None = None,
    platform: PlatformName = PlatformName.LINUX,
    runner_labels: tuple[str, ...] = DEFAULT_RUNNER_LABELS,
    environment: ResolvedEnvironment | None = None,
) -> TestUnit:
    return TestUnit(
        target=target,
        name=name if name is not None else target,
        platform=platform,
        runner_labels=runner_labels,
        environment=environment if environment is not None else env(target, platform),
    )


def make_job(
    name: str = "job-1",
    *,
    target: str = "ntp",
    environment: str = "py3.13",
    platform: PlatformName = PlatformName.LINUX,
    python_version: str = DEFAULT_PYTHON_VERSION,
    runner_labels: tuple[str, ...] = DEFAULT_RUNNER_LABELS,
    unit_tests: bool = True,
    e2e_tests: bool = False,
    agent_image: str | None = None,
) -> BatchJob:
    return BatchJob(
        name=name,
        target=target,
        runner_labels=runner_labels,
        environment=environment,
        platform=platform,
        python_version=python_version,
        unit_tests=unit_tests,
        e2e_tests=e2e_tests,
        agent_image=agent_image,
    )


def make_batch(*batch_jobs: BatchJob, batch_id: str = "batch-01") -> TestBatch:
    job_list = list(batch_jobs) or [make_job()]
    return TestBatch(
        id=batch_id,
        batch_id=batch_id,
        job_list=job_list,
        jobs_count=len(job_list),
        integrations=sorted({job.target for job in job_list}),
    )


def jobs(target: str, count: int) -> list[BatchJob]:
    # Each job carries a distinct environment, as production jobs within an integration do, so
    # names and artifact identities are unique within the target.
    return [make_job(f"{target}-{index}", target=target, environment=f"env-{index}") for index in range(count)]


class FakeManifest:
    def __init__(self, classifier_tags: Sequence[str] = ()):
        self._classifier_tags = list(classifier_tags)

    def get(self, pointer, default=None):
        if pointer == "/tile/classifier_tags":
            return list(self._classifier_tags)
        return default


class FakeIntegration:
    def __init__(
        self,
        name: str,
        *,
        is_testable: bool = True,
        display_name: str | None = None,
        classifier_tags: Sequence[str] = (),
    ):
        self.name = name
        self.is_testable = is_testable
        self.display_name = display_name or name
        self.manifest = FakeManifest(classifier_tags)


class FakeRegistry:
    """Stand-in for ddev's IntegrationRegistry; `get` raises OSError for an unknown name."""

    def __init__(self, integrations: Sequence[FakeIntegration], *, changed: Sequence[str] = ()):
        self._integrations = {integration.name: integration for integration in integrations}
        self._changed = set(changed)

    def get(self, name: str) -> FakeIntegration:
        try:
            return self._integrations[name]
        except KeyError:
            raise OSError(f"Integration does not exist: {name}") from None

    def iter_testable(self, selection: Iterable[str] = ()) -> list[FakeIntegration]:
        # ddev's registry resolves an empty selection to `changed`, so only `all` sees everything
        candidates = (
            self._integrations.values()
            if "all" in selection
            else [integration for integration in self._integrations.values() if integration.name in self._changed]
        )
        return [integration for integration in candidates if integration.is_testable]


def modified(path: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.MODIFIED, path=path)


def renamed(source: str, destination: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.RENAMED, path=destination, previous_path=source)


def copied(source: str, destination: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.COPIED, path=destination, previous_path=source)


class RecordingBus:
    """Stands in for the event bus in processor unit tests, recording what the processor submits."""

    def __init__(self, stopping: bool = False):
        self.queue: asyncio.Queue[BaseMessage] = asyncio.Queue()
        self.stopping = stopping

    def submit_message(self, message: BaseMessage) -> None:
        self.queue.put_nowait(message)


def drain_queue(queue: asyncio.Queue[BaseMessage]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    while not queue.empty():
        messages.append(queue.get_nowait())
    return messages


# ---------------------------------------------------------------------------
# Progress snapshots, as the renderer and the run reporter see them
# ---------------------------------------------------------------------------

JOB_URL = "https://github.com/o/r/actions/runs/1/job/9"
WORKFLOW_URL = "https://github.com/o/r/actions/runs/121"
TOTAL_JOBS = 10


def batch_job(
    target: str = "redis", environment: str = "py3.12", platform: PlatformName = PlatformName.LINUX
) -> BatchJob:
    """A job as the renderer sees it. Only target, environment and platform reach the output."""
    return make_job(f"{target}-{environment}-{platform}", target=target, environment=environment, platform=platform)


def failing_report(*test_names: str) -> JUnitReport:
    cases = tuple(
        JUnitTestCase(
            classname="tests.test_check",
            name=name,
            time=0.1,
            results=(JUnitResult(kind=JUnitResultKind.FAILURE, message="boom"),),
        )
        for name in test_names
    )
    suite = JUnitTestSuite(
        name="tests",
        reported_counts=JUnitCounts(tests=len(cases), failures=len(cases), errors=0, skipped=0),
        time=1.0,
        timestamp=None,
        hostname=None,
        test_cases=cases,
    )
    return JUnitReport(name="unit", test_suites=(suite,))


def attempt(
    status: Status = Status.SUCCESS,
    *,
    number: int = 1,
    failed_steps: tuple[str, ...] = (),
    reports: tuple[JUnitReport, ...] = (),
    job_url: str | None = JOB_URL,
    error: ProgressError | None = None,
) -> JobAttemptProgress:
    return JobAttemptProgress(
        attempt=number,
        job_id=9,
        status=status,
        conclusion=WorkflowJobConclusion.SUCCESS if status is Status.SUCCESS else WorkflowJobConclusion.FAILURE,
        failed_steps=failed_steps,
        job_url=job_url,
        reports=reports,
        error=error,
    )


def job_progress(*attempts: JobAttemptProgress, target: str = "redis", environment: str = "py3.12") -> JobProgress:
    return JobProgress(job=batch_job(target=target, environment=environment), attempts=attempts)


def batch_progress(
    batch_id: str = "batch-01",
    *jobs_progress: JobProgress,
    state: ExecutionState = ExecutionState.FINISHED,
    status: Status | None = Status.SUCCESS,
    run_id: int | None = 121,
    workflow_url: str | None = WORKFLOW_URL,
    current_attempt: int | None = 1,
    max_attempts: int = 1,
    error: ProgressError | None = None,
) -> BatchProgress:
    return BatchProgress(
        batch_id=batch_id,
        run_id=run_id,
        workflow_url=workflow_url,
        state=state,
        status=status,
        current_attempt=current_attempt,
        max_attempts=max_attempts,
        retries_remaining=0,
        retrying_jobs=(),
        jobs_progress=jobs_progress,
        error=error,
    )


def planned_batch(batch_id: str, job_count: int = 4) -> BatchProgress:
    """A batch that has been planned but not dispatched, so it has no run to link to yet."""
    return batch_progress(
        batch_id,
        *[job_progress(target=f"target-{index}") for index in range(job_count)],
        state=ExecutionState.PLANNED,
        status=None,
        run_id=None,
        workflow_url=None,
        current_attempt=None,
    )


def reported_job(index: int, *, reported: bool) -> JobProgress:
    """One passing job of a uniform batch, either reported or not yet."""
    return JobProgress(
        job=make_job(f"target-{index}-py3.12-linux", target=f"target-{index}", environment="py3.12"),
        attempts=(attempt(),) if reported else (),
    )


def uniform_progress(*, done: bool = False, complete: int = TOTAL_JOBS) -> DispatcherProgress:
    """A snapshot where *complete* of ``TOTAL_JOBS`` jobs have reported.

    The count is what makes one revision's rendered body differ from another's, and the comment never
    prints the revision, so tests identify a snapshot by the count it shows.
    """
    finished = complete == TOTAL_JOBS
    return DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[reported_job(index, reported=index < complete) for index in range(TOTAL_JOBS)],
                state=ExecutionState.FINISHED if finished else ExecutionState.RUNNING,
                status=Status.SUCCESS if finished else None,
            ),
        ),
        done=done,
    )


def failing_progress(*, done: bool = False, test_count: int = 40) -> DispatcherProgress:
    """A snapshot with enough failure detail that the full body is bigger than the minimal one."""
    return DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(
                    attempt(
                        Status.FAILURE,
                        reports=(failing_report(*[f"test_number_{index}" for index in range(test_count)]),),
                    )
                ),
                status=Status.FAILURE,
            ),
        ),
        done=done,
    )


def jobs_reported(body: str) -> int:
    """The completed-job count a rendered comment shows, as a stand-in for the snapshot behind it."""
    match = re.search(r"\*\*(\d+)/\d+ jobs\*\*", body)
    assert match is not None, body
    return int(match.group(1))


def comment_page(*comments: IssueComment) -> GitHubResponse:
    """One page of issue comments, as the paginated client yields it."""
    return GitHubResponse.model_validate({"data": list(comments), "headers": {}})
