# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskTestRunner processor."""

from __future__ import annotations

import asyncio
import base64
import gzip
import json
import re
import secrets
from pathlib import Path
from typing import Any

import pytest

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, TestBatch
from ddev.cli.ci.tests.status import Status, conclusion_to_status
from ddev.cli.ci.tests.task_test_runner import (
    CANCEL_REQUEST_TIMEOUT,
    WORKFLOW_INPUTS_LIMIT,
    JobListTooLargeError,
    TaskTestRunner,
    TestRunnerOptions,
)
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import Artifact, ArtifactsList, WorkflowJob, WorkflowJobsList, WorkflowRun
from tests.cli.ci.tests.helpers import RecordingBus, drain_queue, make_job
from tests.helpers.github_async import FakeAsyncGitHubClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def wrap(data: Any) -> GitHubResponse[Any]:
    return GitHubResponse(data=data, headers={})


def decode_job_list(encoded: str) -> list[dict[str, Any]]:
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode())


DEFAULT_URL = object()


def make_artifact(idx: int, expired: bool = False, archive_download_url: Any = DEFAULT_URL) -> Artifact:
    url = f"https://api.github.com/artifact/{idx}/zip" if archive_download_url is DEFAULT_URL else archive_download_url
    return Artifact(
        id=idx,
        name=f"artifact-{idx}",
        size_in_bytes=100,
        url=f"https://api.github.com/artifact/{idx}",
        archive_download_url=url,
        expired=expired,
    )


def make_workflow_run(status: str = "completed", conclusion: str | None = "success") -> WorkflowRun:
    return WorkflowRun(
        id=123,
        name="test-batch",
        status=status,
        conclusion=conclusion if status == "completed" else None,
        html_url="https://github.com/o/r/actions/runs/123",
    )


def artifacts_page(artifacts: list[Artifact]) -> GitHubResponse[ArtifactsList]:
    return wrap(ArtifactsList(total_count=len(artifacts), artifacts=list(artifacts)))


def mock_artifacts(fake: FakeAsyncGitHubClient, artifacts: list[Artifact]):
    fake.mock_response("list_workflow_run_artifacts", artifacts_page(artifacts))


def make_artifact_for(idx: int, job: BatchJob) -> Artifact:
    """Artifact whose name matches a job's deterministic artifact name (the upload/download contract)."""
    artifact = make_artifact(idx)
    return artifact.model_copy(update={"name": job.artifact_name()})


def make_workflow_job(name: str, conclusion: str = "success") -> WorkflowJob:
    return WorkflowJob(id=1, run_id=123, name=name, status="completed", conclusion=conclusion)


def mock_jobs(fake: FakeAsyncGitHubClient, jobs: list[WorkflowJob]):
    fake.mock_response("list_workflow_jobs", wrap(WorkflowJobsList(total_count=len(jobs), jobs=list(jobs))))


def make_runner(
    client: FakeAsyncGitHubClient, tmp_path: Path, pytest_args: str = "", is_fork: bool = False
) -> TaskTestRunner:
    options = TestRunnerOptions(
        owner="DataDog",
        repo="integrations-core",
        workflow_id="test-batch.yaml",
        ref="master",
        base_sha="base-sha-aaa",
        checkout_sha="merge-sha-bbb",
        artifacts_base_path=tmp_path,
        poll_interval_seconds=0.0,
        pytest_args=pytest_args,
        is_fork=is_fork,
    )
    runner = TaskTestRunner(
        name="task-test-runner",
        client=client,  # type: ignore[arg-type]
        options=options,
    )
    runner.bus = RecordingBus()  # type: ignore[assignment]
    return runner


def make_batch(batch_id: str = "batch-err") -> TestBatch:
    return TestBatch(id=batch_id, batch_id=batch_id, job_list=[make_job()], jobs_count=1, integrations=["ntp"])


async def run_happy_path(tmp_path: Path) -> tuple[FakeAsyncGitHubClient, BatchFinished]:
    """Run a clean two-job batch through the runner once and return the client and the BatchFinished.

    The two jobs share a target/environment/platform, so their artifact names collide with each other
    and never match the generic ``artifact-N`` uploads: correlation therefore finds no match.

    The batch's message id and its logical ``batch_id`` differ on purpose, so the assertions on the
    workflow input, the check-run name, and the emitted ``BatchFinished`` show which one is used.
    """
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(fake, [make_artifact(1), make_artifact(2)])
    runner = make_runner(fake, tmp_path)

    batch = TestBatch(
        id="msg-1",
        batch_id="batch-1",
        job_list=[make_job("j1"), make_job("j2")],
        jobs_count=2,
        integrations=["ntp", "kafka"],
    )
    await runner.process_message(batch)

    submitted = drain_queue(runner.bus.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    return fake, finished


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


# ---------------------------------------------------------------------------
# process_message — happy path (one concern per test)
# ---------------------------------------------------------------------------


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
    assert kwargs["inputs"]["integrations"] == json.dumps(["ntp", "kafka"])
    assert decode_job_list(kwargs["inputs"]["job_list"]) == [
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
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
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
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
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
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path)

    batch = TestBatch(id="msg-uuid-xyz", batch_id="batch-07", job_list=[make_job()], jobs_count=1, integrations=["ntp"])
    await runner.process_message(batch)

    assert fake.calls_to("create_workflow_dispatch")[0].kwargs["inputs"]["batch_id"] == "batch-07"

    finished = drain_queue(runner.bus.queue)[0]
    assert isinstance(finished, BatchFinished)
    assert finished.id == "msg-uuid-xyz"
    assert finished.batch_id == "batch-07"


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
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "failure"))
    mock_artifacts(fake, [make_artifact_for(1, j1), make_artifact_for(2, j2)])
    mock_jobs(fake, [make_workflow_job("j1", "success"), make_workflow_job("j2", "failure")])
    runner = make_runner(fake, tmp_path)

    await runner.process_message(
        TestBatch(id="batch-c", batch_id="batch-c", job_list=[j1, j2], jobs_count=2, integrations=["ntp"])
    )

    finished = drain_queue(runner.bus.queue)[0]
    assert isinstance(finished, BatchFinished)
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
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(fake, [make_artifact_for(1, job)])
    # list_workflow_jobs defaults to an empty page.
    runner = make_runner(fake, tmp_path)

    await runner.process_message(
        TestBatch(id="batch-d", batch_id="batch-d", job_list=[job], jobs_count=1, integrations=["ntp"])
    )

    finished = drain_queue(runner.bus.queue)[0]
    assert isinstance(finished, BatchFinished)
    [result] = finished.batch_jobs
    assert result.job == job
    assert result.workflow_job is None
    assert result.artifact_name_path == str(tmp_path / job.artifact_name())


@pytest.mark.asyncio
async def test_process_message_batch_job_without_artifacts(tmp_path: Path):
    # A job with no artifacts on disk still yields a well-formed entry with artifact_name_path None.
    job = make_job("j1")
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(fake, [])
    mock_jobs(fake, [make_workflow_job("j1", "success")])
    runner = make_runner(fake, tmp_path)

    await runner.process_message(
        TestBatch(id="batch-e", batch_id="batch-e", job_list=[job], jobs_count=1, integrations=["ntp"])
    )

    finished = drain_queue(runner.bus.queue)[0]
    assert isinstance(finished, BatchFinished)
    [result] = finished.batch_jobs
    assert result.workflow_job is not None and result.workflow_job.conclusion == "success"
    assert result.artifact_name_path is None


# ---------------------------------------------------------------------------
# process_message — conclusions and resilience
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_emits_batch_finished_when_listing_jobs_fails(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(fake, [])
    fake.mock_response("list_workflow_jobs", RuntimeError("boom-list-jobs"))
    runner = make_runner(fake, tmp_path)

    # A failure listing jobs must not abort the batch: BatchFinished is still emitted, each
    # correlated job carrying no workflow job.
    await runner.process_message(make_batch())

    finished = drain_queue(runner.bus.queue)[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "success"
    assert all(result.workflow_job is None for result in finished.batch_jobs)


@pytest.mark.asyncio
async def test_process_message_failure_path(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "failure"))
    mock_artifacts(fake, [make_artifact(1)])
    runner = make_runner(fake, tmp_path)

    await runner.process_message(
        TestBatch(id="batch-2", batch_id="batch-2", job_list=[make_job()], jobs_count=1, integrations=["ntp"])
    )

    submitted = drain_queue(runner.bus.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "failure"


@pytest.mark.asyncio
async def test_process_message_skipped_conclusion(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "skipped"))
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path)

    await runner.process_message(make_batch())

    submitted = drain_queue(runner.bus.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "skipped"


@pytest.mark.asyncio
async def test_process_message_polls_until_completed(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    # Initial get + polls until "completed"; FIFO one-shots replay in order.
    for status in ("queued", "in_progress", "in_progress", "completed"):
        fake.mock_response("get_workflow_run", make_workflow_run(status, "success"), once=True)
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path)

    await runner.process_message(
        TestBatch(id="batch-3", batch_id="batch-3", job_list=[make_job()], jobs_count=1, integrations=["ntp"])
    )

    assert len(fake.calls_to("get_workflow_run")) == 4
    submitted = drain_queue(runner.bus.queue)
    assert len(submitted) == 1
    assert isinstance(submitted[0], BatchFinished)
    assert submitted[0].status == "success"


@pytest.mark.asyncio
async def test_process_message_skips_expired_artifacts(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(
        fake,
        [
            make_artifact(1),
            make_artifact(2, expired=True),
            make_artifact(3, archive_download_url=None),
        ],
    )
    runner = make_runner(fake, tmp_path)

    await runner.process_message(
        TestBatch(id="batch-4", batch_id="batch-4", job_list=[make_job()], jobs_count=1, integrations=["ntp"])
    )

    # Only the non-expired artifact with a download URL should be fetched.
    download_calls = fake.calls_to("download_artifact")
    assert len(download_calls) == 1
    assert download_calls[0].kwargs["archive_download_url"] == "https://api.github.com/artifact/1/zip"


@pytest.mark.asyncio
async def test_process_message_null_conclusion(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", None))
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path)

    await runner.process_message(make_batch())

    # A null GitHub conclusion maps to a "failure" BatchFinished and a "neutral" check run.
    submitted = drain_queue(runner.bus.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "failure"


@pytest.mark.asyncio
async def test_process_message_emits_batch_finished_when_listing_artifacts_fails(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    fake.mock_response("list_workflow_run_artifacts", RuntimeError("boom-list-artifacts"))
    runner = make_runner(fake, tmp_path)

    # A failure listing artifacts must not abort the batch: exactly one BatchFinished is still
    # emitted, with the workflow's real conclusion.
    await runner.process_message(make_batch())

    submitted = drain_queue(runner.bus.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "success"


@pytest.mark.asyncio
async def test_download_failure_for_one_artifact_does_not_abort_others(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(fake, [make_artifact(1), make_artifact(2), make_artifact(3)])
    fake.mock_response(
        "download_artifact",
        RuntimeError("download failure for artifact 2"),
        archive_download_url="https://api.github.com/artifact/2/zip",
    )
    runner = make_runner(fake, tmp_path)

    await runner.process_message(make_batch())

    # All three were attempted; the failure for #2 didn't abort #3.
    urls = [call.kwargs["archive_download_url"] for call in fake.calls_to("download_artifact")]
    assert urls == [
        "https://api.github.com/artifact/1/zip",
        "https://api.github.com/artifact/2/zip",
        "https://api.github.com/artifact/3/zip",
    ]
    submitted = drain_queue(runner.bus.queue)
    assert len(submitted) == 1
    assert isinstance(submitted[0], BatchFinished)
    assert submitted[0].status == "success"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("failure_point", ["create_workflow_dispatch", "get_workflow_run"])
@pytest.mark.asyncio
async def test_a_batch_that_failed_before_finishing_emits_nothing(tmp_path: Path, failure_point: str):
    """A half-run batch must not reach the gatherer: a `BatchFinished` here would report jobs that
    never ran as absent results.
    """
    fake = FakeAsyncGitHubClient()
    fake.mock_response(failure_point, RuntimeError(f"boom-{failure_point}"))
    runner = make_runner(fake, tmp_path)

    with pytest.raises(RuntimeError, match=f"boom-{failure_point}"):
        await runner.process_message(make_batch())

    assert drain_queue(runner.bus.queue) == []


@pytest.mark.asyncio
async def test_a_batch_that_failed_mid_poll_stays_cancellable(tmp_path: Path):
    """The run is still going when the poll dies, so it has to stay in flight: dropping it here
    leaves a few hundred jobs burning runner minutes with nothing left to reap them.
    """
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("queued"), once=True)
    fake.mock_response("get_workflow_run", RuntimeError("boom-mid-poll"), once=True)
    runner = make_runner(fake, tmp_path)

    with pytest.raises(RuntimeError, match="boom-mid-poll"):
        await runner.process_message(make_batch())

    await runner.cancel_dispatched_runs()
    assert [call.kwargs["run_id"] for call in fake.calls_to("cancel_workflow_run")] == [123]


async def test_a_run_that_finished_on_its_own_is_not_cancelled(tmp_path: Path):
    """Nothing to cancel once a run reached a terminal state, and asking wastes a call.

    Under cancellation the budget is a few seconds shared by every cleanup call, so spending one on a
    run that is already done costs one that is not.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("get_workflow_run", wrap(make_workflow_run()))
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
    client.mock_response("get_workflow_run", wrap(make_workflow_run(status="in_progress", conclusion=None)))
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
    client.mock_response("get_workflow_run", wrap(make_workflow_run(status="in_progress", conclusion=None)))
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


def test_a_dispatched_job_carries_exactly_the_keys_the_workflow_accepts():
    """`test-batch.yml` fails a batch whose jobs do not carry exactly these keys, so a new `BatchJob`
    field that is not added there stops every batch in `setup` rather than reaching a runner.

    The key list is read out of the workflow so the two cannot drift apart silently.
    """
    workflow = Path(__file__).parents[5] / ".github" / "workflows" / "test-batch.yml"
    block = re.search(r"# matrix-keys-begin\n(.*?)# matrix-keys-end", workflow.read_text(encoding="utf-8"), re.DOTALL)
    assert block is not None, "the key list markers are gone from test-batch.yml"
    expected = set(re.findall(r'"([a-z0-9_]+)"', block.group(1)))

    assert set(TaskTestRunner._job_input(make_job())) == expected
