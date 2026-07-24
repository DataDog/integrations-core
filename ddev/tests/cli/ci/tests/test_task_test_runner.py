# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskTestRunner processor."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, Platform, TestBatch
from ddev.cli.ci.tests.status import Status, conclusion_to_status
from ddev.cli.ci.tests.task_test_runner import TaskTestRunner, TestRunnerOptions
from ddev.event_bus.orchestrator import BaseMessage
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import (
    Artifact,
    ArtifactsList,
    WorkflowJob,
    WorkflowJobsList,
    WorkflowRun,
)
from tests.helpers.github_async import FakeAsyncGitHubClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def wrap(data: Any) -> GitHubResponse[Any]:
    return GitHubResponse(data=data, headers={})


def make_job(name: str = "job-1", environment: str = "py3.13") -> BatchJob:
    return BatchJob(
        name=name,
        target="ntp",
        runner_labels=("ubuntu-latest",),
        environment=environment,
        platform=Platform.LINUX,
        unit_tests=True,
        e2e_tests=False,
    )


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


def make_runner(client: FakeAsyncGitHubClient, tmp_path: Path) -> TaskTestRunner:
    options = TestRunnerOptions(
        owner="DataDog",
        repo="integrations-core",
        workflow_id="test-batch.yaml",
        ref="master",
        base_sha="base-sha-aaa",
        checkout_sha="merge-sha-bbb",
        artifacts_base_path=tmp_path,
        poll_interval_seconds=0.0,
    )
    runner = TaskTestRunner(
        name="task-test-runner",
        client=client,  # type: ignore[arg-type]
        options=options,
    )
    runner.queue = asyncio.Queue()
    return runner


def drain_queue(queue: asyncio.Queue[BaseMessage]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    while not queue.empty():
        out.append(queue.get_nowait())
    return out


def make_batch(batch_id: str = "batch-err") -> TestBatch:
    return TestBatch(id=batch_id, batch_id=batch_id, job_list=[make_job()], jobs_count=1, integrations=["ntp"])


async def run_happy_path(tmp_path: Path) -> tuple[FakeAsyncGitHubClient, BatchFinished]:
    """Run a clean two-job batch through the runner once and return the client and the BatchFinished.

    The two jobs share a target/environment/platform, so their artifact names collide with each other
    and never match the generic ``artifact-N`` uploads: correlation therefore finds no match.
    """
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(fake, [make_artifact(1), make_artifact(2)])
    runner = make_runner(fake, tmp_path)

    batch = TestBatch(
        id="batch-1",
        batch_id="batch-1",
        job_list=[make_job("j1"), make_job("j2")],
        jobs_count=2,
        integrations=["ntp", "kafka"],
    )
    await runner.process_message(batch)

    submitted = drain_queue(runner.queue)
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
    assert dispatch_calls[0].kwargs == {
        "owner": "DataDog",
        "repo": "integrations-core",
        "workflow_id": "test-batch.yaml",
        "ref": "master",
        "timeout": None,
        "return_run_details": True,
        "inputs": {
            "batch_id": "batch-1",
            "checkout_sha": "merge-sha-bbb",
            "integrations": json.dumps(["ntp", "kafka"]),
            "job_list": json.dumps(
                [
                    {
                        "name": "j1",
                        "target": "ntp",
                        "runner_labels": ["ubuntu-latest"],
                        "environment": "py3.13",
                        "platform": "linux",
                        "unit_tests": True,
                        "e2e_tests": False,
                        "artifact_name": "ntp_py3.13_linux",
                    },
                    {
                        "name": "j2",
                        "target": "ntp",
                        "runner_labels": ["ubuntu-latest"],
                        "environment": "py3.13",
                        "platform": "linux",
                        "unit_tests": True,
                        "e2e_tests": False,
                        "artifact_name": "ntp_py3.13_linux",
                    },
                ]
            ),
        },
    }


@pytest.mark.asyncio
async def test_opens_check_run_with_head_sha_and_details_url(tmp_path: Path):
    fake, _ = await run_happy_path(tmp_path)

    create_calls = fake.calls_to("create_check_run")
    assert len(create_calls) == 1
    cr = create_calls[0].kwargs
    assert cr["head_sha"] == "base-sha-aaa"
    assert cr["status"] == "in_progress"
    assert cr["name"] == "test-batch/batch-1"
    assert cr["details_url"] == "https://github.com/o/r/actions/runs/123"


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

    assert finished.id == "batch-1"
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
    # The logical batch identity comes from batch_id; the message id is a separate identity and
    # must not be used for the check-run name, the workflow inputs, or the emitted BatchFinished.
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path)

    batch = TestBatch(id="msg-uuid-xyz", batch_id="batch-07", job_list=[make_job()], jobs_count=1, integrations=["ntp"])
    await runner.process_message(batch)

    assert fake.calls_to("create_check_run")[0].kwargs["name"] == "test-batch/batch-07"
    assert fake.calls_to("create_workflow_dispatch")[0].kwargs["inputs"]["batch_id"] == "batch-07"

    finished = drain_queue(runner.queue)[0]
    assert isinstance(finished, BatchFinished)
    assert finished.id == "msg-uuid-xyz"
    assert finished.batch_id == "batch-07"


@pytest.mark.asyncio
async def test_closes_check_run_with_workflow_conclusion(tmp_path: Path):
    fake, _ = await run_happy_path(tmp_path)

    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    upd = update_calls[0].kwargs
    assert upd["check_run_id"] == 999
    assert upd["status"] == "completed"
    assert upd["conclusion"] == "success"


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

    finished = drain_queue(runner.queue)[0]
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

    finished = drain_queue(runner.queue)[0]
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

    finished = drain_queue(runner.queue)[0]
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

    finished = drain_queue(runner.queue)[0]
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

    submitted = drain_queue(runner.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "failure"

    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["status"] == "completed"
    assert update_calls[0].kwargs["conclusion"] == "failure"


@pytest.mark.asyncio
async def test_process_message_skipped_conclusion(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "skipped"))
    mock_artifacts(fake, [])
    runner = make_runner(fake, tmp_path)

    await runner.process_message(make_batch())

    # A "skipped" GitHub conclusion maps to a "skipped" BatchFinished and a "skipped" check run.
    submitted = drain_queue(runner.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "skipped"

    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["conclusion"] == "skipped"


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
    submitted = drain_queue(runner.queue)
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
    submitted = drain_queue(runner.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "failure"

    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["conclusion"] == "neutral"


@pytest.mark.asyncio
async def test_process_message_emits_batch_finished_when_listing_artifacts_fails(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    fake.mock_response("list_workflow_run_artifacts", RuntimeError("boom-list-artifacts"))
    runner = make_runner(fake, tmp_path)

    # A failure listing artifacts must not abort the batch: the check run is still closed
    # and exactly one BatchFinished is emitted with the workflow's real conclusion.
    await runner.process_message(make_batch())

    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["conclusion"] == "success"

    submitted = drain_queue(runner.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "success"


@pytest.mark.asyncio
async def test_process_message_swallows_check_run_close_failure(tmp_path: Path):
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(fake, [make_artifact(1)])
    fake.mock_response("update_check_run", RuntimeError("boom-close"))
    runner = make_runner(fake, tmp_path)

    # A failure closing the check run must not propagate or suppress the BatchFinished.
    await runner.process_message(make_batch())

    assert len(fake.calls_to("update_check_run")) == 1
    submitted = drain_queue(runner.queue)
    assert len(submitted) == 1
    assert isinstance(submitted[0], BatchFinished)
    assert submitted[0].status == "success"


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
    submitted = drain_queue(runner.queue)
    assert len(submitted) == 1
    assert isinstance(submitted[0], BatchFinished)
    assert submitted[0].status == "success"
    assert fake.calls_to("update_check_run")[0].kwargs["conclusion"] == "success"


# ---------------------------------------------------------------------------
# Error paths — try/finally always closes the check run that was opened
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("failure_point", ["create_workflow_dispatch", "get_workflow_run_initial"])
@pytest.mark.asyncio
async def test_failure_before_check_run_opens_does_not_create_check_run(tmp_path: Path, failure_point: str):
    boom = RuntimeError(f"boom-{failure_point}")
    fake = FakeAsyncGitHubClient()
    if failure_point == "create_workflow_dispatch":
        fake.mock_response("create_workflow_dispatch", boom)
    else:
        fake.mock_response("get_workflow_run", boom)
    runner = make_runner(fake, tmp_path)

    with pytest.raises(RuntimeError, match=f"boom-{failure_point}"):
        await runner.process_message(make_batch())

    # The check run is never opened, so there is nothing to close.
    fake.assert_not_called("create_check_run")
    fake.assert_not_called("update_check_run")


@pytest.mark.asyncio
async def test_failure_mid_poll_closes_check_run_as_cancelled(tmp_path: Path):
    boom = RuntimeError("boom-mid-poll")
    fake = FakeAsyncGitHubClient()
    # Initial get succeeds (still running), the first poll raises.
    fake.mock_response("get_workflow_run", make_workflow_run("queued"), once=True)
    fake.mock_response("get_workflow_run", boom, once=True)
    runner = make_runner(fake, tmp_path)

    with pytest.raises(RuntimeError, match="boom-mid-poll"):
        await runner.process_message(make_batch())

    # The check run was opened and the finally closed it as cancelled.
    assert len(fake.calls_to("create_check_run")) == 1
    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["status"] == "completed"
    assert update_calls[0].kwargs["conclusion"] == "cancelled"


@pytest.mark.asyncio
async def test_failure_at_create_check_run_does_not_close_check_run(tmp_path: Path):
    boom = RuntimeError("boom-create-check-run")
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    fake.mock_response("create_check_run", boom)
    runner = make_runner(fake, tmp_path)

    with pytest.raises(RuntimeError, match="boom-create-check-run"):
        await runner.process_message(make_batch())

    # The open was attempted but failed before the try/finally, so there is no check run to close.
    assert len(fake.calls_to("create_check_run")) == 1
    fake.assert_not_called("update_check_run")


@pytest.mark.asyncio
async def test_failure_at_submit_message_closes_check_run_as_success(tmp_path: Path):
    boom = RuntimeError("boom-submit-message")
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", make_workflow_run("completed", "success"))
    mock_artifacts(fake, [make_artifact(1)])
    runner = make_runner(fake, tmp_path)

    class _BoomQueue:
        def put_nowait(self, _: Any):
            raise boom

    runner.queue = _BoomQueue()  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="boom-submit-message"):
        await runner.process_message(make_batch())

    # Workflow completed cleanly; the finally closed the check run as success before submit raised.
    assert len(fake.calls_to("create_check_run")) == 1
    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["status"] == "completed"
    assert update_calls[0].kwargs["conclusion"] == "success"
