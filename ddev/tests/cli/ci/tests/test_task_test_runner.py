# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskTestRunner processor."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from ddev.cli.ci.dispatch_run import ResolvedRun
from ddev.cli.ci.tests import messages, task_test_runner
from ddev.cli.ci.tests.dispatcher_attributes import run_fields
from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, TestBatch
from ddev.cli.ci.tests.progress import ExecutionState
from ddev.cli.ci.tests.status import (
    Status,
    conclusion_to_status,
    has_finished_running,
    has_started_running,
    is_queued,
)
from ddev.cli.ci.tests.task_test_runner import (
    CANCEL_REQUEST_TIMEOUT,
    WORKFLOW_INPUTS_LIMIT,
    JobListTooLargeError,
    TaskTestRunner,
    TestRunnerOptions,
)
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.monitoring import ComponentMonitor
from ddev.monitoring.metrics import MetricKind
from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse
from ddev.utils.github_async.models import (
    Artifact,
    WorkflowJob,
    WorkflowJobConclusion,
    WorkflowJobStatus,
    WorkflowRun,
)
from tests.cli.ci.helpers import decode_job_list
from tests.cli.ci.tests.helpers import (
    RecordingBus,
    drain_queue,
    invalid_response_error,
    make_job,
    recording_runtime,
)
from tests.helpers.clock import FakeClock, advance_clock_on_sleep
from tests.helpers.github_async import (
    DEFAULT_DISPATCH_HTML_URL,
    DEFAULT_DURATION_SECONDS,
    DEFAULT_QUEUE_DURATION_SECONDS,
    FakeAsyncGitHubClient,
    make_artifact,
    make_artifacts_list,
    make_response,
    make_workflow_job,
    make_workflow_jobs_list,
    make_workflow_run,
)
from tests.helpers.monitoring import RecordingJsonHandler, RecordingSink, make_monitor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def mock_artifacts(fake: FakeAsyncGitHubClient, artifacts: list[Artifact]):
    fake.mock_response("list_workflow_run_artifacts", make_response(make_artifacts_list(artifacts)))


def make_artifact_for(idx: int, job: BatchJob) -> Artifact:
    """Artifact whose name matches a job's deterministic artifact name (the upload/download contract)."""
    return make_artifact(id=idx, name=job.artifact_name())


def mock_jobs(fake: FakeAsyncGitHubClient, jobs: list[WorkflowJob]):
    fake.mock_response("list_workflow_jobs", make_response(make_workflow_jobs_list(jobs)))


def make_runner(
    client: FakeAsyncGitHubClient,
    tmp_path: Path,
    pytest_args: str = "",
    is_fork: bool = False,
    artifact_client: FakeAsyncGitHubClient | None = None,
    origin_run_url: str | None = None,
    pr_number: int | None = None,
    handler: logging.Handler | None = None,
    run: ResolvedRun | None = None,
    tags: tuple[str, ...] = (),
    monitor: ComponentMonitor | None = None,
) -> TaskTestRunner:
    run = run or ResolvedRun(
        repository="DataDog/integrations-core",
        head_sha="head-sha-aaa",
        checkout_sha="merge-sha-bbb",
        head_branch="a-branch",
        all_targets=False,
        base_branch="master",
        base_sha="base-sha-ccc",
        pr_number=123,
        is_fork=is_fork,
    )
    options = TestRunnerOptions(
        owner=run.owner,
        repo=run.repo,
        workflow_id="test-batch.yaml",
        ref="master",
        run_fields=run_fields(run, tags=tags),
        concurrency_key=run.concurrency_key,
        artifacts_base_path=tmp_path,
        poll_interval_seconds=0.0,
        pytest_args=pytest_args,
        origin_run_url=origin_run_url,
        pr_number=pr_number,
    )
    runner = TaskTestRunner(
        name="task-test-runner",
        client=client,  # type: ignore[arg-type]
        options=options,
        artifact_client=artifact_client or client,  # type: ignore[arg-type]
        monitor=monitor or make_monitor('test-runner', handler=handler),
    )
    runner.bus = RecordingBus()  # type: ignore[assignment]
    return runner


def make_batch(batch_id: str = "batch-err") -> TestBatch:
    return TestBatch(id=batch_id, batch_id=batch_id, job_list=[make_job()], jobs_count=1, integrations=["ntp"])


def finished_messages(runner: TaskTestRunner) -> list[BatchFinished]:
    return [message for message in drain_queue(runner.bus.queue) if isinstance(message, BatchFinished)]


async def run_happy_path(tmp_path: Path) -> tuple[FakeAsyncGitHubClient, BatchFinished]:
    """Run a clean two-job batch through the runner once and return the client and the BatchFinished.

    The two jobs share a target/environment/platform, so their artifact names collide with each other
    and never match the generic ``artifact-N`` uploads: correlation therefore finds no match.

    The batch's message id and its logical ``batch_id`` differ on purpose, so the assertions on the
    workflow input, the check-run name, and the emitted ``BatchFinished`` show which one is used.
    """
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run(html_url="https://github.com/o/r/actions/runs/123"))
    mock_artifacts(fake, [make_artifact(id=1), make_artifact(id=2)])
    runner = make_runner(fake, tmp_path)

    batch = TestBatch(
        id="msg-1",
        batch_id="batch-1",
        job_list=[make_job("j1"), make_job("j2")],
        jobs_count=2,
        integrations=["ntp", "kafka"],
    )
    await runner.process_message(batch)

    submitted = finished_messages(runner)
    assert len(submitted) == 1
    finished = submitted[0]
    return fake, finished


@pytest.mark.asyncio
async def test_healthy_attempts_report_zero_operation_failures(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [make_artifact(id=1), make_artifact(id=2)])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(
        TestBatch(
            id="msg-1",
            batch_id="batch-1",
            job_list=[make_job("j1"), make_job("j2")],
            jobs_count=2,
            integrations=["ntp", "kafka"],
        )
    )

    assert finished_messages(runner)
    counted = {}
    for record in sink.records_named('operations.count'):
        counted[record.tags['dispatcher.operation']] = counted.get(record.tags['dispatcher.operation'], 0) + 1
    assert counted == {"dispatch_batch": 1, "fetch_workflow": 1, "refresh_jobs": 2, "collect_artifacts": 1}
    assert failed_by_operation(sink) == {
        "dispatch_batch": 0,
        "fetch_workflow": 0,
        "refresh_jobs": 0,
        "collect_artifacts": 0,
    }
    assert {record.tags['dispatcher.component'] for record in sink.records_named('operations.count')} == {'test-runner'}
    assert [record.kind.value for record in sink.records_named('artifacts.download.duration')] == ['distribution']


async def test_polling_intervals_are_measured_between_polls_of_the_same_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A batch's first poll has no predecessor, even when an earlier batch was polled by the same runner.

    The samples are the runner's own, so they carry the run's metric dimensions and its component.
    """
    fake = FakeAsyncGitHubClient()
    mock_artifacts(fake, [])
    fake.mock_response("get_workflow_run", make_workflow_run())
    ticks = iter(range(0, 1000, 10))
    monkeypatch.setattr(task_test_runner, "monotonic", lambda: float(next(ticks)))
    monitoring, sink = recording_runtime()
    monitoring.set_run_fields(ci_pipeline_id="12345", context="pr", team="agent-integrations")
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    for batch_id, polls in (("batch-1", 3), ("batch-2", 2)):
        for _ in range(polls - 1):
            fake.mock_response("get_workflow_run", make_workflow_run(status="in_progress"), once=True)
        await runner.process_message(make_batch(batch_id))

    intervals = sink.records_named("requests.polling_interval")
    assert [record.value for record in intervals] == [10.0, 10.0, 10.0]
    assert {tuple(sorted(record.tags.items())) for record in intervals} == {
        (
            ("ci.pipeline.id", "12345"),
            ("dispatcher.component", "test-runner"),
            ("dispatcher.context", "pr"),
            ("team", "agent-integrations"),
        )
    }
    assert {record.kind for record in intervals} == {MetricKind.DISTRIBUTION}


@pytest.mark.asyncio
async def test_an_accepted_dispatch_counts_the_batch_and_its_jobs(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))
    batch = TestBatch(
        id="msg-1",
        batch_id="batch-1",
        job_list=[make_job("j1"), make_job("j2", target="kafka")],
        jobs_count=2,
        integrations=["ntp", "kafka"],
    )

    await runner.process_message(batch)

    assert [record.value for record in sink.records_named('batches.count')] == [1]
    assert [record.value for record in sink.records_named('batch.jobs.count')] == [2]
    counted = sink.records_named('jobs.count')
    assert [record.value for record in counted] == [1, 1]
    assert [record.tags['dispatcher.batch.job.integration'] for record in counted] == ['ntp', 'kafka']
    assert {record.tags['dispatcher.component'] for record in counted} == {'test-runner'}


@pytest.mark.asyncio
async def test_a_completed_workflow_reports_its_own_running_duration(tmp_path: Path):
    """`batch.duration` is the workflow's running time, not the dispatcher's."""
    fake = FakeAsyncGitHubClient()
    fake.mock_response(
        "get_workflow_run",
        make_workflow_run(),
    )
    mock_artifacts(fake, [])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(make_batch())

    duration = sink.records_named("batch.duration")
    assert [record.value for record in duration] == [DEFAULT_DURATION_SECONDS]
    assert duration[0].kind is MetricKind.DISTRIBUTION


@pytest.mark.asyncio
async def test_a_completed_workflow_without_timing_reports_no_batch_duration(tmp_path: Path):
    """A missing start is omitted, not approximated from another clock."""
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run(run_started_at=None))
    mock_artifacts(fake, [])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(make_batch())

    assert sink.records_named("batch.duration") == []


# ---------------------------------------------------------------------------
# conclusion_to_status
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("conclusion", "expected"),
    [
        ("success", Status.SUCCESS),
        ("skipped", Status.SKIPPED),
        ("failure", Status.FAILURE),
        ("cancelled", Status.FAILURE),
        ("timed_out", Status.FAILURE),
        ("action_required", Status.FAILURE),
        ("neutral", Status.FAILURE),
        (None, Status.FAILURE),
    ],
)
def test_conclusion_to_status(conclusion: str | None, expected: Status):
    result = conclusion_to_status(conclusion)
    assert result is expected
    assert isinstance(result, Status)


@pytest.mark.parametrize(
    ("status", "conclusion", "queued", "started", "finished"),
    [
        pytest.param(WorkflowJobStatus.QUEUED, None, True, False, False, id="queued"),
        pytest.param(WorkflowJobStatus.WAITING, None, True, False, False, id="waiting"),
        pytest.param(WorkflowJobStatus.PENDING, None, True, False, False, id="pending"),
        pytest.param(WorkflowJobStatus.REQUESTED, None, False, False, False, id="requested"),
        pytest.param(WorkflowJobStatus.IN_PROGRESS, None, False, True, False, id="in-progress"),
        pytest.param(WorkflowJobStatus.COMPLETED, WorkflowJobConclusion.SUCCESS, False, True, True, id="success"),
        pytest.param(WorkflowJobStatus.COMPLETED, WorkflowJobConclusion.FAILURE, False, True, True, id="failure"),
        pytest.param(WorkflowJobStatus.COMPLETED, WorkflowJobConclusion.TIMED_OUT, False, True, True, id="timed-out"),
        pytest.param(WorkflowJobStatus.COMPLETED, WorkflowJobConclusion.SKIPPED, False, False, False, id="skipped"),
        pytest.param(WorkflowJobStatus.COMPLETED, WorkflowJobConclusion.CANCELLED, False, False, False, id="cancelled"),
        pytest.param(WorkflowJobStatus.COMPLETED, WorkflowJobConclusion.NEUTRAL, False, False, False, id="neutral"),
    ],
)
def test_a_jobs_state_on_a_runner(
    status: WorkflowJobStatus, conclusion: WorkflowJobConclusion | None, queued: bool, started: bool, finished: bool
):
    """Only a job that ran has timing worth measuring; `requested` is not a wait for a runner."""
    job = make_workflow_job(status=status, conclusion=conclusion)

    assert (is_queued(job), has_started_running(job), has_finished_running(job)) == (queued, started, finished)


# ---------------------------------------------------------------------------
# process_message — happy path (one concern per test)
# ---------------------------------------------------------------------------


async def test_dispatch_publishes_the_link_before_polling(tmp_path: Path):
    client = FakeAsyncGitHubClient()
    runner = make_runner(client, tmp_path)
    get_run = client.get_workflow_run

    async def observe_first_poll(*args: Any, **kwargs: Any) -> GitHubResponse[WorkflowRun]:
        [dispatched] = drain_queue(runner.bus.queue)
        assert isinstance(dispatched, messages.BatchProgressUpdate)
        assert dispatched.run_id == 123
        assert dispatched.workflow_url == DEFAULT_DISPATCH_HTML_URL
        assert dispatched.state is ExecutionState.QUEUED
        return await get_run(*args, **kwargs)

    client.get_workflow_run = observe_first_poll  # type: ignore[method-assign]
    await runner.process_message(make_batch())


def failed_by_operation(sink: RecordingSink) -> dict[str, float]:
    totals: dict[str, float] = {}
    for record in sink.records_named('operations.failed'):
        totals[record.tags['dispatcher.operation']] = totals.get(record.tags['dispatcher.operation'], 0) + record.value
    return totals


async def test_a_jobs_listing_not_yet_visible_after_dispatch_is_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """GitHub answers 404 on a freshly dispatched run's jobs listing until that listing becomes visible."""
    advance_clock_on_sleep(FakeClock(), monkeypatch)
    responses = [
        httpx.Response(404),
        httpx.Response(
            200,
            json=make_workflow_jobs_list([make_workflow_job(name="j1", status=WorkflowJobStatus.QUEUED)]).model_dump(
                mode="json"
            ),
        ),
    ]
    client = AsyncGitHubClient("token", transport=httpx.MockTransport(lambda request: responses.pop(0)))
    monitoring, sink = recording_runtime()
    runner = make_runner(client, tmp_path, monitor=monitoring.component("test-runner"))  # type: ignore[arg-type]

    try:
        jobs = await runner._list_jobs(123, "batch-1", "listing workflow jobs")
    finally:
        await client.aclose()

    assert [job.id for job in jobs] == [1]
    assert failed_by_operation(sink) == {"refresh_jobs": 0}


async def test_a_dispatch_github_refuses_fails_the_dispatch_operation_only(tmp_path: Path):
    client = FakeAsyncGitHubClient()
    client.mock_response("create_workflow_dispatch", RuntimeError("dispatch refused"))
    monitoring, sink = recording_runtime()
    runner = make_runner(client, tmp_path, monitor=monitoring.component("test-runner"))

    with pytest.raises(RuntimeError, match="dispatch refused"):
        await runner.process_message(make_batch())

    assert sink.records_named("batches.count") == []
    assert sink.records_named("jobs.count") == []
    assert failed_by_operation(sink) == {"dispatch_batch": 1}
    assert [record.value for record in sink.records_named("operations.count")] == [1]


async def test_collection_publishes_outcomes_before_a_cancellable_artifact_request(tmp_path: Path):
    client, artifacts = FakeAsyncGitHubClient(), FakeAsyncGitHubClient()
    batch = make_batch()
    mock_jobs(client, [make_workflow_job(name=batch.job_list[0].name, conclusion=WorkflowJobConclusion.FAILURE)])
    client.mock_response("get_workflow_run", make_workflow_run(conclusion="failure"))
    mock_artifacts(artifacts, [make_artifact(id=1)])
    entered = asyncio.Event()

    async def blocked_download(*args: Any, **kwargs: Any) -> None:
        entered.set()
        await asyncio.Future()

    artifacts.download_artifact = blocked_download  # type: ignore[method-assign]
    monitoring, sink = recording_runtime()
    runner = make_runner(client, tmp_path, artifact_client=artifacts, monitor=monitoring.component("test-runner"))
    task = asyncio.create_task(runner.process_message(batch))
    try:
        async with asyncio.timeout(5):
            await entered.wait()
        published = drain_queue(runner.bus.queue)
        collecting = published[-1]
        assert isinstance(collecting, messages.BatchProgressUpdate)
        assert collecting.state is ExecutionState.ARTIFACT_DOWNLOAD
        assert collecting.status is Status.FAILURE
        assert collecting.jobs[0].conclusion == "failure"
        assert client.last_call("list_workflow_jobs").kwargs["per_page"] == 100
        assert artifacts.last_call("list_workflow_run_artifacts").kwargs["per_page"] == 100
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    # A cancelled download never settled, so it counts as no operation outcome at all, but the
    # time it took is still reported.
    settled = [
        record
        for record in sink.records_named("operations.count")
        if record.tags["dispatcher.operation"] == "collect_artifacts"
    ]
    assert settled == []
    assert [record.kind for record in sink.records_named("artifacts.download.duration")] == [MetricKind.DISTRIBUTION]

    await runner.cancel_dispatched_runs()
    assert client.calls_to("cancel_workflow_run") == []
    assert drain_queue(runner.bus.queue) == []


@pytest.mark.asyncio
async def test_dispatches_workflow_with_job_list_payload(tmp_path: Path):
    fake, _ = await run_happy_path(tmp_path)

    dispatch_calls = fake.calls_to("create_workflow_dispatch")
    assert len(dispatch_calls) == 1
    kwargs = dispatch_calls[0].kwargs
    assert {key: value for key, value in kwargs.items() if key != "inputs"} == {
        "owner": "DataDog",
        "repo": "integrations-core",
        "workflow_id": "test-batch.yaml",
        "ref": "master",
        "timeout": None,
        "return_run_details": True,
    }
    assert kwargs["inputs"]["batch_id"] == "batch-1"
    assert kwargs["inputs"]["checkout_sha"] == "merge-sha-bbb"
    assert kwargs["inputs"]["head_sha"] == "head-sha-aaa"
    assert kwargs["inputs"]["head_branch"] == "a-branch"
    assert kwargs["inputs"]["concurrency_key"] == "pr-123"
    assert kwargs["inputs"]["integrations"] == json.dumps(["ntp", "kafka"])
    assert kwargs["inputs"]["context"] == "pr"
    jobs = decode_job_list(kwargs["inputs"]["job_list"])
    additional_tags = [job.pop("additional_tags") for job in jobs]
    assert jobs == [
        {
            "name": "j1",
            "target": "ntp",
            "runner_labels": ["ubuntu-22.04"],
            "environment": "py3.13",
            "platform": "linux",
            "python_version": "3.13",
            "unit_tests": True,
            "e2e_tests": False,
            "agent_image": None,
            "minimum_base_package": False,
            "coverage": True,
            "artifact_name": "ntp_py3.13_linux",
        },
        {
            "name": "j2",
            "target": "ntp",
            "runner_labels": ["ubuntu-22.04"],
            "environment": "py3.13",
            "platform": "linux",
            "python_version": "3.13",
            "unit_tests": True,
            "e2e_tests": False,
            "agent_image": None,
            "minimum_base_package": False,
            "coverage": True,
            "artifact_name": "ntp_py3.13_linux",
        },
    ]
    common_tags = (
        "dispatcher.base_branch:master,dispatcher.base_sha:base-sha-ccc,dispatcher.batch.id:batch-1,"
        "dispatcher.batch.job.e2e_tests:false,dispatcher.batch.job.environment:py3.13,"
        "dispatcher.batch.job.integration:ntp,dispatcher.batch.job.minimum_base_package:false,"
        "dispatcher.batch.job.name:{name},dispatcher.batch.job.platform:linux,"
        "dispatcher.batch.job.python_version:3.13,dispatcher.batch.job.unit_tests:true,"
        "dispatcher.checkout_sha:merge-sha-bbb,dispatcher.context:pr,dispatcher.pr.number:123,"
        "dispatcher.run.is_fork:false,team:agent-integrations"
    )
    assert additional_tags == [common_tags.format(name="j1"), common_tags.format(name="j2")]


@pytest.mark.parametrize(
    ("run", "tags", "expected_context", "concurrency_key", "has_pr_tags"),
    [
        pytest.param(None, (), "pr", "pr-123", True, id="pull-request"),
        pytest.param(
            ResolvedRun(
                repository="DataDog/integrations-core",
                head_sha="master-sha",
                checkout_sha="master-sha",
                head_branch="master",
                all_targets=False,
            ),
            (),
            "master",
            "master-sha",
            False,
            id="master",
        ),
        pytest.param(
            ResolvedRun(
                repository="DataDog/integrations-core",
                head_sha="agent-sha",
                checkout_sha="agent-sha",
                head_branch="test-agent",
                all_targets=False,
            ),
            ("context:test-agent",),
            "test-agent",
            "agent-sha",
            False,
            id="custom-context",
        ),
    ],
)
def test_run_identity_and_context_reach_workflow_and_job_tags(
    tmp_path: Path,
    run: ResolvedRun | None,
    tags: tuple[str, ...],
    expected_context: str,
    concurrency_key: str,
    has_pr_tags: bool,
):
    runner = make_runner(FakeAsyncGitHubClient(), tmp_path, run=run, tags=tags)

    inputs = runner._build_inputs(make_batch("batch-context"))
    [job] = decode_job_list(inputs["job_list"])
    job_tags = job["additional_tags"].split(",")

    assert inputs["context"] == expected_context
    assert inputs["concurrency_key"] == concurrency_key
    assert inputs["checkout_sha"] == (run.checkout_sha if run else "merge-sha-bbb")
    assert inputs["head_sha"] == (run.head_sha if run else "head-sha-aaa")
    assert inputs["head_branch"] == (run.head_branch if run else "a-branch")
    assert f"dispatcher.context:{expected_context}" in job_tags
    assert ("dispatcher.pr.number:123" in job_tags) is has_pr_tags
    assert ("dispatcher.base_branch:master" in job_tags) is has_pr_tags
    assert not any(tag.startswith(("git.", "dispatcher.head_sha", "dispatcher.head_branch")) for tag in job_tags)


def test_job_tags_keep_caller_values_inside_one_transport_field(tmp_path: Path):
    run = ResolvedRun(
        repository="DataDog/integrations-core",
        head_sha="agent-sha",
        checkout_sha="agent-sha",
        head_branch="test-agent",
        all_targets=False,
    )
    runner = make_runner(FakeAsyncGitHubClient(), tmp_path, run=run, tags=("context:release,candidate\nunsafe\rvalue",))

    inputs = runner._build_inputs(make_batch("batch-context"))
    [job] = decode_job_list(inputs["job_list"])

    assert inputs["context"] == "release,candidate\nunsafe\rvalue"
    assert "dispatcher.context:release_candidate_unsafe_value" in job["additional_tags"].split(",")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("origin_run_url", "pr_number", "expected"),
    [
        (
            "https://github.com/DataDog/integrations-core/actions/runs/456",
            123,
            {
                "origin_run_url": "https://github.com/DataDog/integrations-core/actions/runs/456",
                "pr_number": "123",
            },
        ),
        (None, None, {}),
    ],
)
async def test_optional_navigation_context_reaches_the_batch_workflow(
    tmp_path: Path, origin_run_url: str | None, pr_number: int | None, expected: dict[str, str]
):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path, origin_run_url=origin_run_url, pr_number=pr_number)

    await runner.process_message(make_batch("batch-1"))

    inputs = fake.calls_to("create_workflow_dispatch")[0].kwargs["inputs"]
    assert {key: inputs[key] for key in expected} == expected
    assert ("origin_run_url" in inputs) is (origin_run_url is not None)
    assert ("pr_number" in inputs) is (pr_number is not None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pytest_args", "expected"),
    [
        pytest.param('-m "not flaky"', '-m "not flaky"', id="forwarded-with-quoting-intact"),
        pytest.param("", None, id="omitted-when-unset"),
    ],
)
async def test_pytest_args_reach_the_batch_workflow(tmp_path: Path, pytest_args: str, expected: str | None):
    """Losing these runs tests the caller excluded: `master.yml` passes `-m "not flaky"`."""
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path, pytest_args=pytest_args)

    await runner.process_message(make_batch("batch-1"))

    inputs = fake.calls_to("create_workflow_dispatch")[0].kwargs["inputs"]
    assert inputs.get("pytest_args") == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(("is_fork", "expected"), [(True, "true"), (False, "false")])
async def test_the_batch_is_told_whether_it_is_testing_a_fork(tmp_path: Path, is_fork: bool, expected: str):
    """The batch withholds every credential on this input, so a fork dispatched without it hands a
    fork's code the Datadog key and the Docker credentials. Sent either way, because an absent input
    leaves the workflow on its own default of trusting the commit.
    """
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path, is_fork=is_fork)

    await runner.process_message(make_batch("batch-1"))

    assert fake.calls_to("create_workflow_dispatch")[0].kwargs["inputs"]["is_fork"] == expected


@pytest.mark.asyncio
async def test_a_batch_too_large_to_dispatch_is_refused_before_dispatching(tmp_path: Path):
    """GitHub rejects an oversized dispatch, and a rejected one still opens a check run that
    nothing will ever close, so the batch has to be refused before the request is made.

    Names are random rather than repetitive, so they survive compression and the batch really does
    exceed the limit.
    """
    jobs = [make_job(secrets.token_hex(150)) for _ in range(300)]
    batch = TestBatch(id="big", batch_id="batch-big", job_list=jobs, jobs_count=len(jobs), integrations=["ntp"])
    fake = FakeAsyncGitHubClient()
    runner = make_runner(fake, tmp_path)

    with pytest.raises(JobListTooLargeError, match=str(WORKFLOW_INPUTS_LIMIT)):
        await runner.process_message(batch)

    fake.assert_not_called("create_workflow_dispatch")


@pytest.mark.asyncio
async def test_downloads_all_batch_artifacts(tmp_path: Path):
    fake, _ = await run_happy_path(tmp_path)

    download_calls = fake.calls_to("download_artifact")
    assert len(download_calls) == 2
    assert (download_calls[0].kwargs["archive_download_url"], download_calls[0].kwargs["dest_path"]) == (
        "https://api.github.com/artifact/1/zip",
        tmp_path / "artifact-1",
    )
    assert (download_calls[1].kwargs["archive_download_url"], download_calls[1].kwargs["dest_path"]) == (
        "https://api.github.com/artifact/2/zip",
        tmp_path / "artifact-2",
    )


async def test_lifecycle_log_messages_identify_their_batch_run_and_artifacts(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    mock_artifacts(fake, [make_artifact(id=1)])
    handler = RecordingJsonHandler()
    runner = make_runner(fake, tmp_path, handler=handler)

    await runner.process_message(make_batch("batch-1"))

    messages = [event["event"] for event in handler.events]
    assert "Dispatching batch batch-1 (integrations=1, jobs=1)" in messages
    assert "Batch batch-1 dispatched as workflow run 123" in messages
    assert "Batch batch-1 state changed to artifact_download" in messages
    assert "Workflow run 123 completed: success" in messages
    assert "Collecting artifacts for workflow run 123" in messages
    assert "Downloaded artifact artifact-1" in messages
    assert "Artifacts downloaded for workflow run 123 (count=1)" in messages
    assert "Batch batch-1 workflow results ready: success" in messages


@pytest.mark.asyncio
async def test_emits_batch_finished_with_run_metadata(tmp_path: Path):
    _, finished = await run_happy_path(tmp_path)

    assert finished.id == "msg-1"
    # The logical batch identity is carried explicitly, not inferred from the message id.
    assert finished.batch_id == "batch-1"
    assert finished.status == "success"
    assert finished.run_id == 123
    assert finished.workflow_url == "https://github.com/o/r/actions/runs/123"
    assert finished.artifacts_path == str(tmp_path)


@pytest.mark.asyncio
async def test_batch_finished_records_unmatched_correlation_when_no_match(tmp_path: Path):
    # The two jobs' artifact names collide and don't match the generic artifacts, and there is no
    # jobs API match, so both correlated facets are None while the per-facet file names are recorded.
    _, finished = await run_happy_path(tmp_path)

    assert [r.job.name for r in finished.batch_jobs] == ["j1", "j2"]
    assert all(r.workflow_job is None and r.artifact_name_path is None for r in finished.batch_jobs)

    first = finished.batch_jobs[0]
    base = make_job("j1").artifact_name()
    assert (first.unit_artifact_name, first.e2e_artifact_name, first.coverage_artifact_name) == (
        f"unit-{base}",
        f"e2e-{base}",
        f"coverage-{base}",
    )


@pytest.mark.asyncio
async def test_uses_batch_id_not_message_id_for_correlation(tmp_path: Path):
    # The logical batch identity comes from batch_id; the message id is a separate identity and must
    # not be used for the workflow inputs or the emitted BatchFinished.
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path)

    batch = TestBatch(id="msg-uuid-xyz", batch_id="batch-07", job_list=[make_job()], jobs_count=1, integrations=["ntp"])
    await runner.process_message(batch)

    assert fake.calls_to("create_workflow_dispatch")[0].kwargs["inputs"]["batch_id"] == "batch-07"

    finished = finished_messages(runner)[0]
    assert finished.id == "msg-uuid-xyz"
    assert finished.batch_id == "batch-07"


# ---------------------------------------------------------------------------
# process_message — queued, running and queue-wait metrics
# ---------------------------------------------------------------------------


def batch_with(job: BatchJob, batch_id: str = "batch-1") -> TestBatch:
    return TestBatch(id=batch_id, batch_id=batch_id, job_list=[job], jobs_count=1, integrations=[job.target])


async def test_queued_and_running_gauges_track_each_poll_and_settle_at_zero(tmp_path: Path):
    """The gauges follow the batch's jobs through the polls and settle at zero once it completes."""
    fake = FakeAsyncGitHubClient()
    for run_status in ("in_progress", "in_progress", "completed"):
        fake.mock_response("get_workflow_run", make_workflow_run(status=run_status), once=True)
    job = make_job()
    for job_status in (WorkflowJobStatus.QUEUED, WorkflowJobStatus.IN_PROGRESS, WorkflowJobStatus.COMPLETED):
        listing = make_response(make_workflow_jobs_list([make_workflow_job(name=job.name, status=job_status)]))
        fake.mock_response("list_workflow_jobs", listing, once=True)
    mock_artifacts(fake, [])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(batch_with(job, batch_id="batch-07"))

    queued = sink.records_named("jobs.queued")
    running = sink.records_named("jobs.running")
    assert [record.value for record in queued] == [1, 0, 0]
    assert [record.value for record in running] == [0, 1, 0]
    assert {record.kind for record in queued + running} == {MetricKind.GAUGE}
    # The batch is part of each series' identity, so concurrent batches of one run do not overwrite each other.
    assert {
        (record.tags["dispatcher.batch.job.platform"], record.tags["dispatcher.batch.id"])
        for record in queued + running
    } == {("linux", "batch-07")}


async def test_a_completed_workflow_ends_its_gauges_at_zero_when_the_final_listing_fails(tmp_path: Path):
    """The poll that sees the workflow complete is the batch series' last point, so it must not repeat a stale job."""
    fake = FakeAsyncGitHubClient()
    for run_status in ("in_progress", "completed"):
        fake.mock_response("get_workflow_run", make_workflow_run(status=run_status), once=True)
    job = make_job()
    running = make_workflow_job(name=job.name, status=WorkflowJobStatus.IN_PROGRESS)
    fake.mock_response("list_workflow_jobs", make_response(make_workflow_jobs_list([running])), once=True)
    fake.mock_response("list_workflow_jobs", RuntimeError("listing unavailable"))
    mock_artifacts(fake, [])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(batch_with(job))

    assert [record.value for record in sink.records_named("jobs.running")] == [1, 0]
    assert [record.value for record in sink.records_named("jobs.queued")] == [0, 0]


async def test_workflow_jobs_the_batch_did_not_plan_are_not_counted(tmp_path: Path):
    """Setup and teardown jobs also wait for runners, but they are not the tests the batch dispatched."""
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_jobs(fake, [make_workflow_job(name="setup", status=WorkflowJobStatus.QUEUED)])
    mock_artifacts(fake, [])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(batch_with(make_job("j1")))

    assert [record.value for record in sink.records_named("jobs.queued")] == [0]


async def test_queue_duration_is_emitted_once_per_job_attempt_across_polls_and_reconcile(tmp_path: Path):
    """Repeated observations of one job attempt yield one sample, wherever it is first seen."""
    fake = FakeAsyncGitHubClient()
    for run_status in ("in_progress", "completed"):
        fake.mock_response("get_workflow_run", make_workflow_run(status=run_status), once=True)
    job = make_job()
    running = make_workflow_job(name=job.name, status=WorkflowJobStatus.IN_PROGRESS)
    fake.mock_response("list_workflow_jobs", make_response(make_workflow_jobs_list([running])), once=True)
    completed = make_workflow_job(name=job.name)
    fake.mock_response("list_workflow_jobs", make_response(make_workflow_jobs_list([completed])), once=True)
    mock_artifacts(fake, [])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(batch_with(job))

    samples = sink.records_named("job.queue.duration")
    assert [record.value for record in samples] == [DEFAULT_QUEUE_DURATION_SECONDS]
    assert samples[0].kind is MetricKind.DISTRIBUTION
    assert samples[0].tags["dispatcher.batch.job.integration"] == "ntp"
    assert samples[0].tags["dispatcher.batch.job.platform"] == "linux"
    assert {record.tags["dispatcher.component"] for record in samples} == {"test-runner"}


async def test_a_job_first_seen_completed_at_reconcile_still_reports_its_queue_wait(tmp_path: Path):
    """A short job can finish between two polls, so the reconcile listing is a last chance to sample it."""
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run(), once=True)
    job = make_job()
    fake.mock_response("list_workflow_jobs", make_response(make_workflow_jobs_list()), once=True)
    settled = make_response(make_workflow_jobs_list([make_workflow_job(name=job.name)]))
    fake.mock_response("list_workflow_jobs", settled, once=True)
    mock_artifacts(fake, [])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(batch_with(job))

    assert [record.value for record in sink.records_named("job.queue.duration")] == [DEFAULT_QUEUE_DURATION_SECONDS]


async def test_a_job_that_never_ran_reports_no_queue_wait(tmp_path: Path):
    """A job cancelled before a runner picked it up has no wait to report."""
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    job = make_job()
    mock_jobs(fake, [make_workflow_job(name=job.name, conclusion=WorkflowJobConclusion.CANCELLED)])
    mock_artifacts(fake, [])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(batch_with(job))

    assert sink.records_named("job.queue.duration") == []


async def test_a_rerun_gets_its_own_queue_wait_sample(tmp_path: Path):
    """A rerun is a new job attempt with a new ID, so its own wait is a new sample."""
    fake = FakeAsyncGitHubClient()
    for run_status in ("in_progress", "completed"):
        fake.mock_response("get_workflow_run", make_workflow_run(status=run_status), once=True)
    job = make_job()
    first_attempt = make_workflow_job(id=1, name=job.name, status=WorkflowJobStatus.IN_PROGRESS)
    fake.mock_response("list_workflow_jobs", make_response(make_workflow_jobs_list([first_attempt])), once=True)
    rerun = make_workflow_job(id=2, name=job.name)
    fake.mock_response("list_workflow_jobs", make_response(make_workflow_jobs_list([rerun])), once=True)
    mock_artifacts(fake, [])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(batch_with(job))

    samples = sink.records_named("job.queue.duration")
    assert [record.value for record in samples] == [DEFAULT_QUEUE_DURATION_SECONDS, DEFAULT_QUEUE_DURATION_SECONDS]


# ---------------------------------------------------------------------------
# process_message — correlation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_correlates_batch_jobs(tmp_path: Path):
    # A failed multi-job run where j1 passed and j2 failed: each batch_jobs entry must carry its
    # own true per-job status and its artifact directory, resolved by the job's artifact name.
    # The two jobs differ in an artifact-relevant field (environment) so their base names differ.
    j1, j2 = make_job("j1", environment="py3.13"), make_job("j2", environment="py3.12")
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run(conclusion="failure"))
    mock_artifacts(fake, [make_artifact_for(1, j1), make_artifact_for(2, j2)])
    mock_jobs(
        fake, [make_workflow_job(name="j1"), make_workflow_job(name="j2", conclusion=WorkflowJobConclusion.FAILURE)]
    )
    runner = make_runner(fake, tmp_path)

    await runner.process_message(
        TestBatch(id="batch-c", batch_id="batch-c", job_list=[j1, j2], jobs_count=2, integrations=["ntp"])
    )

    finished = finished_messages(runner)[0]
    assert finished.status == "failure"

    results = {r.job.name: r for r in finished.batch_jobs}
    assert set(results) == {"j1", "j2"}
    # Passing job is not marked failed; each carries its true workflow-run conclusion.
    assert results["j1"].workflow_job is not None and results["j1"].workflow_job.conclusion == "success"
    assert results["j2"].workflow_job is not None and results["j2"].workflow_job.conclusion == "failure"
    # Each job's single artifact folder is resolved by its base artifact name (no heuristic matching).
    assert results["j1"].artifact_name_path == str(tmp_path / j1.artifact_name())
    assert results["j2"].artifact_name_path == str(tmp_path / j2.artifact_name())
    # The per-facet file names inside each folder are recorded from the base artifact name.
    assert results["j1"].unit_artifact_name == f"unit-{j1.artifact_name()}"
    assert results["j2"].coverage_artifact_name == f"coverage-{j2.artifact_name()}"


@pytest.mark.asyncio
async def test_process_message_batch_job_without_workflow_match(tmp_path: Path):
    # A job present in the batch but absent from the workflow-run API response still yields a
    # well-formed entry: its artifact is located but workflow_job is None.
    job = make_job("j1")
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [make_artifact_for(1, job)])
    # list_workflow_jobs defaults to an empty page.
    runner = make_runner(fake, tmp_path)

    await runner.process_message(
        TestBatch(id="batch-d", batch_id="batch-d", job_list=[job], jobs_count=1, integrations=["ntp"])
    )

    finished = finished_messages(runner)[0]
    [result] = finished.batch_jobs
    assert result.job == job
    assert result.workflow_job is None
    assert result.artifact_name_path == str(tmp_path / job.artifact_name())


@pytest.mark.asyncio
async def test_process_message_batch_job_without_artifacts(tmp_path: Path):
    # A job with no artifacts on disk still yields a well-formed entry with artifact_name_path None.
    job = make_job("j1")
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [])
    mock_jobs(fake, [make_workflow_job(name="j1")])
    runner = make_runner(fake, tmp_path)

    await runner.process_message(
        TestBatch(id="batch-e", batch_id="batch-e", job_list=[job], jobs_count=1, integrations=["ntp"])
    )

    finished = finished_messages(runner)[0]
    [result] = finished.batch_jobs
    assert result.workflow_job is not None and result.workflow_job.conclusion == "success"
    assert result.artifact_name_path is None


# ---------------------------------------------------------------------------
# process_message — conclusions and resilience
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_emits_batch_finished_when_listing_jobs_fails(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [])
    fake.mock_response("list_workflow_jobs", RuntimeError("boom-list-jobs"))
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    # A failure listing jobs must not abort the batch: BatchFinished is still emitted, each
    # correlated job carrying no workflow job.
    await runner.process_message(make_batch())

    finished = finished_messages(runner)[0]
    assert finished.status == "success"
    assert all(result.workflow_job is None for result in finished.batch_jobs)
    assert [
        record.value
        for record in sink.records_named("operations.failed")
        if record.tags["dispatcher.operation"] == "refresh_jobs"
    ] == [1, 1]


@pytest.mark.parametrize(
    ("conclusion", "expected"),
    [
        pytest.param("failure", Status.FAILURE, id="failure"),
        pytest.param("skipped", Status.SKIPPED, id="skipped"),
        pytest.param(None, Status.FAILURE, id="missing-conclusion"),
    ],
)
@pytest.mark.asyncio
async def test_process_message_reports_completed_workflow_status(
    tmp_path: Path, conclusion: str | None, expected: Status
):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run(conclusion=conclusion))
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path)

    await runner.process_message(make_batch())

    [finished] = finished_messages(runner)
    assert finished.status is expected


@pytest.mark.asyncio
async def test_process_message_polls_until_completed(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    # Initial get + polls until "completed"; FIFO one-shots replay in order.
    for status in ("queued", "in_progress", "in_progress", "completed"):
        fake.mock_response("get_workflow_run", make_workflow_run(status=status), once=True)
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path)

    await runner.process_message(
        TestBatch(id="batch-3", batch_id="batch-3", job_list=[make_job()], jobs_count=1, integrations=["ntp"])
    )

    assert len(fake.calls_to("get_workflow_run")) == 4
    submitted = finished_messages(runner)
    assert len(submitted) == 1
    assert submitted[0].status == "success"


async def test_final_results_use_jobs_available_after_artifact_collection(tmp_path: Path):
    client = FakeAsyncGitHubClient()
    batch = make_batch()
    job = batch.job_list[0]
    client.mock_response("get_workflow_run", make_workflow_run(status="in_progress"), once=True)
    mock_jobs(
        client,
        [make_workflow_job(name=job.name, status=WorkflowJobStatus.IN_PROGRESS)],
    )
    mock_artifacts(client, [make_artifact_for(1, job)])
    download_artifact = client.download_artifact

    async def download_with_settled_job(archive_download_url: str, dest_path: Path, **kwargs: Any) -> None:
        await download_artifact(archive_download_url, dest_path, **kwargs)
        mock_jobs(client, [make_workflow_job(name=job.name)])

    client.download_artifact = download_with_settled_job  # type: ignore[method-assign]
    runner = make_runner(client, tmp_path)

    await runner.process_message(batch)

    [finished] = finished_messages(runner)
    result = finished.batch_jobs[0]
    assert result.workflow_job is not None
    assert result.workflow_job.conclusion is WorkflowJobConclusion.SUCCESS


@pytest.mark.parametrize("last_listing", ["empty", "failed", "stale"])
async def test_final_results_preserve_only_completed_observations(tmp_path: Path, last_listing: str):
    client = FakeAsyncGitHubClient()
    batch = make_batch()
    batch.job_list.append(make_job("unfinished", environment="py3.12"))
    batch.jobs_count = len(batch.job_list)
    completed_job = make_workflow_job(name=batch.job_list[0].name)
    unfinished_job = make_workflow_job(id=2, name="unfinished", status=WorkflowJobStatus.IN_PROGRESS)
    client.mock_response("get_workflow_run", make_workflow_run(status="in_progress"), once=True)
    client.mock_response("list_workflow_jobs", make_workflow_jobs_list([completed_job, unfinished_job]), once=True)
    if last_listing == "failed":
        client.mock_response("list_workflow_jobs", RuntimeError("listing unavailable"))
    elif last_listing == "stale":
        mock_jobs(
            client,
            [make_workflow_job(name=completed_job.name, status=WorkflowJobStatus.IN_PROGRESS), unfinished_job],
        )
    runner = make_runner(client, tmp_path)

    await runner.process_message(batch)

    published = drain_queue(runner.bus.queue)
    updates = [message for message in published if isinstance(message, messages.BatchProgressUpdate)]
    assert updates[-1].jobs[0].conclusion is WorkflowJobConclusion.SUCCESS
    assert updates[-1].jobs[1].status is WorkflowJobStatus.IN_PROGRESS
    finished = published[-1]
    assert isinstance(finished, BatchFinished)
    assert finished.batch_jobs[0].workflow_job.conclusion is WorkflowJobConclusion.SUCCESS
    assert finished.batch_jobs[1].workflow_job is None


@pytest.mark.parametrize(
    "unavailable",
    [
        pytest.param(make_artifact(id=2, expired=True), id="expired"),
        pytest.param(make_artifact(id=2, archive_download_url=None), id="missing-url"),
    ],
)
@pytest.mark.asyncio
async def test_unavailable_artifacts_degrade_collection(tmp_path: Path, unavailable: Artifact):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [make_artifact(id=1), unavailable])
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(
        TestBatch(id="batch-4", batch_id="batch-4", job_list=[make_job()], jobs_count=1, integrations=["ntp"])
    )

    download_calls = fake.calls_to("download_artifact")
    assert len(download_calls) == 1
    assert download_calls[0].kwargs["archive_download_url"] == "https://api.github.com/artifact/1/zip"
    assert failed_by_operation(sink)["collect_artifacts"] == 1
    assert [finished.status for finished in finished_messages(runner)] == [Status.SUCCESS]


@pytest.mark.asyncio
async def test_process_message_emits_batch_finished_when_listing_artifacts_fails(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    fake.mock_response("list_workflow_run_artifacts", RuntimeError("boom-list-artifacts"))
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    # A failure listing artifacts must not abort the batch: exactly one BatchFinished is still
    # emitted, with the workflow's real conclusion.
    await runner.process_message(make_batch())

    submitted = finished_messages(runner)
    assert len(submitted) == 1
    finished = submitted[0]
    assert finished.status == "success"
    assert failed_by_operation(sink) == {
        "dispatch_batch": 0,
        "fetch_workflow": 0,
        "refresh_jobs": 0,
        "collect_artifacts": 1,
    }
    assert [record.kind for record in sink.records_named("artifacts.download.duration")] == [MetricKind.DISTRIBUTION]


@pytest.mark.asyncio
async def test_download_failure_for_one_artifact_does_not_abort_others(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run())
    mock_artifacts(fake, [make_artifact(id=1), make_artifact(id=2), make_artifact(id=3)])
    fake.mock_response(
        "download_artifact",
        RuntimeError("download failure for artifact 2"),
        archive_download_url="https://api.github.com/artifact/2/zip",
    )
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    await runner.process_message(make_batch())

    # All three were attempted; the failure for #2 didn't abort #3.
    urls = [call.kwargs["archive_download_url"] for call in fake.calls_to("download_artifact")]
    assert urls == [
        "https://api.github.com/artifact/1/zip",
        "https://api.github.com/artifact/2/zip",
        "https://api.github.com/artifact/3/zip",
    ]
    submitted = finished_messages(runner)
    assert len(submitted) == 1
    assert submitted[0].status == "success"
    assert failed_by_operation(sink)["collect_artifacts"] == 1
    assert [record.kind for record in sink.records_named("artifacts.download.duration")] == [MetricKind.DISTRIBUTION]


# ---------------------------------------------------------------------------
# Unparsable responses
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("failure_point", "operation", "workflow_running", "cancelled_runs", "operation_failures", "durations"),
    [
        # The dispatch response could not be parsed, so a dispatched run's ID is unknown and
        # nothing is tracked to cancel.
        pytest.param(
            "create_workflow_dispatch",
            "dispatching the batch",
            False,
            [],
            {"dispatch_batch": 1},
            [],
            id="dispatch-response",
        ),
        pytest.param(
            "get_workflow_run",
            "polling workflow status",
            True,
            [123],
            {"dispatch_batch": 0, "fetch_workflow": 1},
            [],
            id="poll-response",
        ),
        # Jobs are refreshed on every poll, so the page can fail while the workflow is still going.
        pytest.param(
            "list_workflow_jobs",
            "listing workflow jobs",
            True,
            [123],
            {"dispatch_batch": 0, "fetch_workflow": 0, "refresh_jobs": 1},
            [],
            id="jobs-page",
        ),
        pytest.param(
            "list_workflow_jobs",
            "listing workflow jobs",
            False,
            [],
            {"dispatch_batch": 0, "fetch_workflow": 0, "refresh_jobs": 1},
            [DEFAULT_DURATION_SECONDS],
            id="completed-jobs-page",
        ),
        # Artifacts are collected after completion, when the run is already released.
        pytest.param(
            "list_workflow_run_artifacts",
            "listing workflow artifacts",
            False,
            [],
            {"dispatch_batch": 0, "fetch_workflow": 0, "refresh_jobs": 0, "collect_artifacts": 1},
            [DEFAULT_DURATION_SECONDS],
            id="artifact-page",
        ),
    ],
)
@pytest.mark.asyncio
async def test_an_unparsable_response_stops_the_batch_and_keeps_its_run_cancellable(
    tmp_path: Path,
    failure_point: str,
    operation: str,
    workflow_running: bool,
    cancelled_runs: list[int],
    operation_failures: dict[str, float],
    durations: list[float],
):
    """An invalid response stops the batch without losing a known unfinished run."""
    fake = FakeAsyncGitHubClient()
    if workflow_running:
        fake.mock_response("get_workflow_run", make_workflow_run(status="in_progress"))
    fake.mock_response(failure_point, invalid_response_error())
    monitoring, sink = recording_runtime()
    runner = make_runner(fake, tmp_path, monitor=monitoring.component("test-runner"))

    # Bound the test if an invalid response is retried indefinitely.
    with pytest.raises(FatalProcessingError, match=f"Invalid GitHub response while {operation}"):
        async with asyncio.timeout(5):
            await runner.process_message(make_batch())

    assert finished_messages(runner) == []
    assert failed_by_operation(sink) == operation_failures
    assert [record.value for record in sink.records_named('batch.duration')] == durations

    await runner.cancel_dispatched_runs()
    cancelled = [call.kwargs["run_id"] for call in fake.calls_to("cancel_workflow_run")]
    assert cancelled == cancelled_runs


@pytest.mark.asyncio
async def test_an_unparsable_response_reason_is_a_single_bounded_line(tmp_path: Path):
    """The failure summary must identify the operation and run without including unbounded details."""
    unparsable = ValidationError.from_exception_data(
        title="WorkflowRun",
        line_errors=[
            {
                "type": "value_error",
                "loc": ("body", "html_url"),
                "input": "not-a-url",
                "ctx": {"error": ValueError("line one\nline two\n" + "x" * 500)},
            }
        ],
    )
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", unparsable)
    runner = make_runner(fake, tmp_path)

    with pytest.raises(FatalProcessingError, match="batch-err") as exc_info:
        await runner.process_message(make_batch())

    reason = str(exc_info.value)
    assert "\n" not in reason
    assert len(reason) <= 300
    assert "Invalid GitHub response while polling workflow status" in reason
    assert "batch-err" in reason
    assert "run 123" in reason
    assert "WorkflowRun" in reason


@pytest.mark.asyncio
async def test_every_validation_error_is_logged_once_with_its_field(tmp_path: Path):
    """All invalid fields must be visible from a single response failure."""
    unparsable = ValidationError.from_exception_data(
        title="WorkflowJobsList",
        line_errors=[
            {
                "type": "enum",
                "loc": ("jobs", 0, "steps", 1, "status"),
                "input": "paused",
                "ctx": {"expected": "'queued', 'in_progress', 'completed' or 'pending'"},
            },
            {
                "type": "missing",
                "loc": ("jobs", 2, "id"),
                "input": {"name": "a job without an id"},
            },
        ],
    )
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run(status="in_progress"))
    fake.mock_response("list_workflow_jobs", unparsable)
    handler = RecordingJsonHandler()
    runner = make_runner(fake, tmp_path, handler=handler)

    with pytest.raises(FatalProcessingError, match="batch-err") as exc_info:
        await runner.process_message(make_batch())

    reason = str(exc_info.value)
    assert "2 validation errors" in reason
    assert "WorkflowJobsList" in reason
    assert "See logs for details." in reason
    assert exc_info.value.__cause__ is unparsable
    log_text = '\n'.join(event['event'] for event in handler.events)
    assert "listing workflow jobs" in log_text
    assert "batch-err" in log_text
    assert "run 123" in log_text
    assert log_text.count("jobs.0.steps.1.status") == 1
    assert "paused" in log_text
    assert "Input should be 'queued', 'in_progress', 'completed' or 'pending'" in log_text
    assert log_text.count("jobs.2.id") == 1
    assert "Field required" in log_text


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("failure_point", ["create_workflow_dispatch", "get_workflow_run"])
@pytest.mark.asyncio
async def test_failed_execution_keeps_only_known_dispatch_progress(tmp_path: Path, failure_point: str):
    """An interrupted execution retains its run link without claiming collected results."""
    fake = FakeAsyncGitHubClient()
    fake.mock_response(failure_point, RuntimeError(f"boom-{failure_point}"))
    runner = make_runner(fake, tmp_path)

    with pytest.raises(RuntimeError, match=f"boom-{failure_point}"):
        await runner.process_message(make_batch())

    published = drain_queue(runner.bus.queue)
    if failure_point == "create_workflow_dispatch":
        assert published == []
    else:
        [dispatched] = published
        assert isinstance(dispatched, messages.BatchProgressUpdate)
        assert dispatched.workflow_url == DEFAULT_DISPATCH_HTML_URL
        assert dispatched.state is ExecutionState.QUEUED


@pytest.mark.asyncio
async def test_a_batch_that_failed_mid_poll_stays_cancellable(tmp_path: Path):
    """The run is still going when the poll dies, so it has to stay in flight: dropping it here
    leaves a few hundred jobs burning runner minutes with nothing left to reap them.
    """
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run(status="queued"), once=True)
    fake.mock_response("get_workflow_run", RuntimeError("boom-mid-poll"), once=True)
    runner = make_runner(fake, tmp_path)

    with pytest.raises(RuntimeError, match="boom-mid-poll"):
        await runner.process_message(make_batch())

    await runner.cancel_dispatched_runs()
    assert [call.kwargs["run_id"] for call in fake.calls_to("cancel_workflow_run")] == [123]


async def test_cancellation_reporting_identifies_the_batch_and_run_it_stops(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run(status="queued"), once=True)
    fake.mock_response("get_workflow_run", RuntimeError("boom-mid-poll"), once=True)
    handler = RecordingJsonHandler()
    runner = make_runner(fake, tmp_path, handler=handler)

    with pytest.raises(RuntimeError, match="boom-mid-poll"):
        await runner.process_message(make_batch())

    await runner.cancel_dispatched_runs()

    cancelled = [
        event for event in handler.events if event["event"] == "Workflow run 123 for batch batch-err cancelled"
    ]
    assert [(event["batch_id"], event["run_id"]) for event in cancelled] == [("batch-err", 123)]


async def test_a_run_that_finished_on_its_own_is_not_cancelled(tmp_path: Path):
    """Nothing to cancel once a run reached a terminal state, and asking wastes a call.

    Under cancellation the budget is a few seconds shared by every cleanup call, so spending one on a
    run that is already done costs one that is not.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("get_workflow_run", make_response(make_workflow_run()))
    mock_artifacts(client, [])
    mock_jobs(client, [])
    runner = make_runner(client, tmp_path)
    runner.bus = RecordingBus()  # type: ignore[assignment]

    await runner.process_message(make_batch(batch_id="batch-1"))
    await runner.cancel_dispatched_runs()

    assert client.calls_to("cancel_workflow_run") == []


async def test_cancelling_a_run_does_not_wait_out_the_clients_default_timeout(tmp_path: Path):
    """A GitHub that accepts the connection then stalls must not consume the whole teardown budget.

    The retry policy's timeout bounds the ladder, not an attempt in flight, so without a per-request
    timeout this inherits the client's 30s default. The process is killed after roughly ten, so one
    stalled call would mean no run is cancelled at all.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("get_workflow_run", make_response(make_workflow_run(status="in_progress")))
    runner = make_runner(client, tmp_path)
    runner.bus = RecordingBus()  # type: ignore[assignment]

    task = asyncio.create_task(runner.process_message(make_batch(batch_id="batch-1")))
    # `get_workflow_run` is the first call after the run is recorded in flight, so it is the point
    # from which there is something for the cleanup to cancel.
    async with asyncio.timeout(5):
        while not client.calls_to("get_workflow_run"):
            await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    await runner.cancel_dispatched_runs()

    assert client.last_call("cancel_workflow_run").kwargs["timeout"] == CANCEL_REQUEST_TIMEOUT


async def test_a_run_still_going_when_the_batch_is_cancelled_is_cancelled_too(tmp_path: Path):
    """A dispatched run outlives the process that asked for it and keeps burning runner minutes.

    The run is dropped from the in-flight set only once it is known to have finished, so a batch
    cancelled mid-flight is still there for the cleanup to find.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("get_workflow_run", make_response(make_workflow_run(status="in_progress")))
    runner = make_runner(client, tmp_path)
    runner.bus = RecordingBus()  # type: ignore[assignment]

    task = asyncio.create_task(runner.process_message(make_batch(batch_id="batch-1")))
    await asyncio.sleep(0)
    # Bounded, so a regression that never reaches the in-flight state fails here instead of spinning
    # until the CI job's own timeout, which reports nothing useful.
    async with asyncio.timeout(5):
        while not client.calls_to("get_workflow_run"):
            await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    await runner.cancel_dispatched_runs()

    assert [call.kwargs["run_id"] for call in client.calls_to("cancel_workflow_run")] == [123]
