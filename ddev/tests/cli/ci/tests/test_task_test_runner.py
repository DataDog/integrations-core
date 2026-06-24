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

from ddev.cli.ci.tests._status import conclusion_to_status
from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, TestBatch
from ddev.cli.ci.tests.task_test_runner import TaskTestRunner, TestRunnerOptions
from ddev.event_bus.orchestrator import BaseMessage
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import (
    Artifact,
    ArtifactsList,
    WorkflowRun,
)
from tests.helpers.github_async import FakeAsyncGitHubClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wrap(data: Any) -> GitHubResponse[Any]:
    return GitHubResponse(data=data, headers={})


def _job(name: str = "job-1") -> BatchJob:
    return BatchJob(
        name=name,
        target="ntp",
        runner="ubuntu-latest",
        environment="py3.13",
        platform="linux",
        unit_tests=True,
        e2e_tests=False,
    )


_DEFAULT_URL = object()


def _artifact(idx: int, expired: bool = False, archive_download_url: Any = _DEFAULT_URL) -> Artifact:
    url = f"https://api.github.com/artifact/{idx}/zip" if archive_download_url is _DEFAULT_URL else archive_download_url
    return Artifact(
        id=idx,
        name=f"artifact-{idx}",
        size_in_bytes=100,
        url=f"https://api.github.com/artifact/{idx}",
        archive_download_url=url,
        expired=expired,
    )


def _workflow_run(status: str = "completed", conclusion: str | None = "success") -> WorkflowRun:
    return WorkflowRun(
        id=123,
        name="test-batch",
        status=status,
        conclusion=conclusion if status == "completed" else None,
        html_url="https://github.com/o/r/actions/runs/123",
    )


def _artifacts_page(artifacts: list[Artifact]) -> GitHubResponse[ArtifactsList]:
    return _wrap(ArtifactsList(total_count=len(artifacts), artifacts=list(artifacts)))


def _mock_artifacts(fake: FakeAsyncGitHubClient, artifacts: list[Artifact]) -> None:
    fake.mock_response("list_workflow_run_artifacts", _artifacts_page(artifacts))


def _make_runner(client: FakeAsyncGitHubClient, tmp_path: Path) -> TaskTestRunner:
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


def _drain_queue(queue: asyncio.Queue[BaseMessage]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    while not queue.empty():
        out.append(queue.get_nowait())
    return out


def _batch(batch_id: str = "batch-err") -> TestBatch:
    return TestBatch(id=batch_id, job_list=[_job()], jobs_count=1, integrations=["ntp"])


# ---------------------------------------------------------------------------
# conclusion_to_status
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("conclusion", "expected"),
    [
        ("success", "success"),
        ("skipped", "skipped"),
        ("failure", "failure"),
        ("cancelled", "failure"),
        ("timed_out", "failure"),
        ("action_required", "failure"),
        ("neutral", "failure"),
        (None, "failure"),
    ],
)
def test_conclusion_to_status(conclusion: str | None, expected: str) -> None:
    assert conclusion_to_status(conclusion) == expected


# ---------------------------------------------------------------------------
# process_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_happy_path(tmp_path: Path) -> None:
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", _workflow_run("completed", "success"))
    _mock_artifacts(fake, [_artifact(1), _artifact(2)])
    runner = _make_runner(fake, tmp_path)

    batch = TestBatch(id="batch-1", job_list=[_job("j1"), _job("j2")], jobs_count=2, integrations=["ntp", "kafka"])
    await runner.process_message(batch)

    # Dispatch once, with the right shape.
    dispatch_calls = fake.calls_to("create_workflow_dispatch")
    assert len(dispatch_calls) == 1
    assert dispatch_calls[0].kwargs == {
        "owner": "DataDog",
        "repo": "integrations-core",
        "workflow_id": "test-batch.yaml",
        "ref": "master",
        "timeout": None,
        "inputs": {
            "batch_id": "batch-1",
            "checkout_sha": "merge-sha-bbb",
            "integrations": json.dumps(["ntp", "kafka"]),
            "job_list": json.dumps(
                [
                    {
                        "name": "j1",
                        "target": "ntp",
                        "runner": "ubuntu-latest",
                        "environment": "py3.13",
                        "platform": "linux",
                        "unit_tests": True,
                        "e2e_tests": False,
                    },
                    {
                        "name": "j2",
                        "target": "ntp",
                        "runner": "ubuntu-latest",
                        "environment": "py3.13",
                        "platform": "linux",
                        "unit_tests": True,
                        "e2e_tests": False,
                    },
                ]
            ),
        },
    }

    # Check run opened with the PR head SHA, in_progress, with the workflow URL as details_url.
    create_calls = fake.calls_to("create_check_run")
    assert len(create_calls) == 1
    cr = create_calls[0].kwargs
    assert cr["head_sha"] == "base-sha-aaa"
    assert cr["status"] == "in_progress"
    assert cr["name"] == "test-batch/batch-1"
    assert cr["details_url"] == "https://github.com/o/r/actions/runs/123"

    # Both artifacts downloaded under <base>/<run_id>/<id>-<name> (collision-safe path).
    download_calls = fake.calls_to("download_artifact")
    assert len(download_calls) == 2
    assert (download_calls[0].kwargs["archive_download_url"], download_calls[0].kwargs["dest_path"]) == (
        "https://api.github.com/artifact/1/zip",
        tmp_path / "123" / "1-artifact-1",
    )
    assert (download_calls[1].kwargs["archive_download_url"], download_calls[1].kwargs["dest_path"]) == (
        "https://api.github.com/artifact/2/zip",
        tmp_path / "123" / "2-artifact-2",
    )

    # Exactly one BatchFinished message submitted with the right fields.
    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.id == "batch-1"
    assert finished.status == "success"
    assert finished.run_id == 123
    assert finished.workflow_url == "https://github.com/o/r/actions/runs/123"
    assert finished.artifacts_path == str(tmp_path / "123")

    # Check run closed with the GitHub conclusion.
    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    upd = update_calls[0].kwargs
    assert upd["check_run_id"] == 999
    assert upd["status"] == "completed"
    assert upd["conclusion"] == "success"


@pytest.mark.asyncio
async def test_process_message_failure_path(tmp_path: Path) -> None:
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", _workflow_run("completed", "failure"))
    _mock_artifacts(fake, [_artifact(1)])
    runner = _make_runner(fake, tmp_path)

    await runner.process_message(TestBatch(id="batch-2", job_list=[_job()], jobs_count=1, integrations=["ntp"]))

    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "failure"

    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["status"] == "completed"
    assert update_calls[0].kwargs["conclusion"] == "failure"


@pytest.mark.asyncio
async def test_process_message_skipped_conclusion(tmp_path: Path) -> None:
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", _workflow_run("completed", "skipped"))
    _mock_artifacts(fake, [])
    runner = _make_runner(fake, tmp_path)

    await runner.process_message(_batch())

    # A "skipped" GitHub conclusion maps to a "skipped" BatchFinished and a "skipped" check run.
    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "skipped"

    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["conclusion"] == "skipped"


@pytest.mark.asyncio
async def test_process_message_polls_until_completed(tmp_path: Path) -> None:
    fake = FakeAsyncGitHubClient()
    # Initial get + polls until "completed"; FIFO one-shots replay in order.
    for status in ("queued", "in_progress", "in_progress", "completed"):
        fake.mock_response("get_workflow_run", _workflow_run(status, "success"), once=True)
    _mock_artifacts(fake, [])
    runner = _make_runner(fake, tmp_path)

    await runner.process_message(TestBatch(id="batch-3", job_list=[_job()], jobs_count=1, integrations=["ntp"]))

    assert len(fake.calls_to("get_workflow_run")) == 4
    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    assert isinstance(submitted[0], BatchFinished)
    assert submitted[0].status == "success"


@pytest.mark.asyncio
async def test_process_message_skips_expired_artifacts(tmp_path: Path) -> None:
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", _workflow_run("completed", "success"))
    _mock_artifacts(
        fake,
        [
            _artifact(1),
            _artifact(2, expired=True),
            _artifact(3, archive_download_url=None),
        ],
    )
    runner = _make_runner(fake, tmp_path)

    await runner.process_message(TestBatch(id="batch-4", job_list=[_job()], jobs_count=1, integrations=["ntp"]))

    # Only the non-expired artifact with a download URL should be fetched.
    download_calls = fake.calls_to("download_artifact")
    assert len(download_calls) == 1
    assert download_calls[0].kwargs["archive_download_url"] == "https://api.github.com/artifact/1/zip"


@pytest.mark.asyncio
async def test_process_message_null_conclusion(tmp_path: Path) -> None:
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", _workflow_run("completed", None))
    _mock_artifacts(fake, [])
    runner = _make_runner(fake, tmp_path)

    await runner.process_message(_batch())

    # A null GitHub conclusion maps to a "failure" BatchFinished and a "neutral" check run.
    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "failure"

    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["conclusion"] == "neutral"


@pytest.mark.asyncio
async def test_process_message_emits_batch_finished_when_listing_artifacts_fails(tmp_path: Path) -> None:
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", _workflow_run("completed", "success"))
    fake.mock_response("list_workflow_run_artifacts", RuntimeError("boom-list-artifacts"))
    runner = _make_runner(fake, tmp_path)

    # A failure listing artifacts must not abort the batch: the check run is still closed
    # and exactly one BatchFinished is emitted with the workflow's real conclusion.
    await runner.process_message(_batch())

    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["conclusion"] == "success"

    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "success"


@pytest.mark.asyncio
async def test_process_message_swallows_check_run_close_failure(tmp_path: Path) -> None:
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", _workflow_run("completed", "success"))
    _mock_artifacts(fake, [_artifact(1)])
    fake.mock_response("update_check_run", RuntimeError("boom-close"))
    runner = _make_runner(fake, tmp_path)

    # A failure closing the check run must not propagate or suppress the BatchFinished.
    await runner.process_message(_batch())

    assert len(fake.calls_to("update_check_run")) == 1
    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    assert isinstance(submitted[0], BatchFinished)
    assert submitted[0].status == "success"


@pytest.mark.asyncio
async def test_download_failure_for_one_artifact_does_not_abort_others(tmp_path: Path) -> None:
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", _workflow_run("completed", "success"))
    _mock_artifacts(fake, [_artifact(1), _artifact(2), _artifact(3)])
    fake.mock_response(
        "download_artifact",
        RuntimeError("download failure for artifact 2"),
        archive_download_url="https://api.github.com/artifact/2/zip",
    )
    runner = _make_runner(fake, tmp_path)

    await runner.process_message(_batch())

    # All three were attempted; the failure for #2 didn't abort #3.
    urls = [call.kwargs["archive_download_url"] for call in fake.calls_to("download_artifact")]
    assert urls == [
        "https://api.github.com/artifact/1/zip",
        "https://api.github.com/artifact/2/zip",
        "https://api.github.com/artifact/3/zip",
    ]
    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    assert isinstance(submitted[0], BatchFinished)
    assert submitted[0].status == "success"
    assert fake.calls_to("update_check_run")[0].kwargs["conclusion"] == "success"


# ---------------------------------------------------------------------------
# Error paths — try/finally always closes the check run that was opened
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("failure_point", ["create_workflow_dispatch", "get_workflow_run_initial"])
@pytest.mark.asyncio
async def test_failure_before_check_run_opens_does_not_create_check_run(tmp_path: Path, failure_point: str) -> None:
    boom = RuntimeError(f"boom-{failure_point}")
    fake = FakeAsyncGitHubClient()
    if failure_point == "create_workflow_dispatch":
        fake.mock_response("create_workflow_dispatch", boom)
    else:
        fake.mock_response("get_workflow_run", boom)
    runner = _make_runner(fake, tmp_path)

    with pytest.raises(RuntimeError, match=f"boom-{failure_point}"):
        await runner.process_message(_batch())

    # The check run is never opened, so there is nothing to close.
    fake.assert_not_called("create_check_run")
    fake.assert_not_called("update_check_run")


@pytest.mark.asyncio
async def test_failure_mid_poll_closes_check_run_as_cancelled(tmp_path: Path) -> None:
    boom = RuntimeError("boom-mid-poll")
    fake = FakeAsyncGitHubClient()
    # Initial get succeeds (still running), the first poll raises.
    fake.mock_response("get_workflow_run", _workflow_run("queued"), once=True)
    fake.mock_response("get_workflow_run", boom, once=True)
    runner = _make_runner(fake, tmp_path)

    with pytest.raises(RuntimeError, match="boom-mid-poll"):
        await runner.process_message(_batch())

    # The check run was opened and the finally closed it as cancelled.
    assert len(fake.calls_to("create_check_run")) == 1
    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["status"] == "completed"
    assert update_calls[0].kwargs["conclusion"] == "cancelled"


@pytest.mark.asyncio
async def test_failure_at_create_check_run_does_not_close_check_run(tmp_path: Path) -> None:
    boom = RuntimeError("boom-create-check-run")
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", _workflow_run("completed", "success"))
    fake.mock_response("create_check_run", boom)
    runner = _make_runner(fake, tmp_path)

    with pytest.raises(RuntimeError, match="boom-create-check-run"):
        await runner.process_message(_batch())

    # The open was attempted but failed before the try/finally, so there is no check run to close.
    assert len(fake.calls_to("create_check_run")) == 1
    fake.assert_not_called("update_check_run")


@pytest.mark.asyncio
async def test_failure_at_submit_message_closes_check_run_as_success(tmp_path: Path) -> None:
    boom = RuntimeError("boom-submit-message")
    fake = FakeAsyncGitHubClient()
    fake.mock_response("get_workflow_run", _workflow_run("completed", "success"))
    _mock_artifacts(fake, [_artifact(1)])
    runner = _make_runner(fake, tmp_path)

    class _BoomQueue:
        def put_nowait(self, _: Any) -> None:
            raise boom

    runner.queue = _BoomQueue()  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="boom-submit-message"):
        await runner.process_message(_batch())

    # Workflow completed cleanly; the finally closed the check run as success before submit raised.
    assert len(fake.calls_to("create_check_run")) == 1
    update_calls = fake.calls_to("update_check_run")
    assert len(update_calls) == 1
    assert update_calls[0].kwargs["status"] == "completed"
    assert update_calls[0].kwargs["conclusion"] == "success"
