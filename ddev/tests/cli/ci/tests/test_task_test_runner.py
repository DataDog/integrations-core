# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskTestRunner processor."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, TestBatch
from ddev.cli.ci.tests.task_test_runner import TaskTestRunner, _conclusion_to_status
from ddev.event_bus.orchestrator import BaseMessage
from ddev.utils.github_async import (
    Artifact,
    ArtifactsList,
    CheckRun,
    GitHubResponse,
    WorkflowDispatchResult,
    WorkflowRun,
)

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


class _FakeClient:
    """Minimal stand-in for AsyncGitHubClient that records calls and replays canned responses."""

    def __init__(
        self,
        run_statuses: list[str],
        conclusion: str = "success",
        artifacts: list[Artifact] | None = None,
        workflow_url: str = "https://github.com/o/r/actions/runs/123",
        fail_at: dict[str, Exception] | None = None,
        get_workflow_run_transient_failures: int = 0,
        get_workflow_run_fail_after: int = -1,
        download_failure_for_url: str | None = None,
    ) -> None:
        self._run_statuses = list(run_statuses)
        self._conclusion = conclusion
        self._artifacts = artifacts if artifacts is not None else [_artifact(1), _artifact(2)]
        self._workflow_url = workflow_url
        self._fail_at = fail_at or {}
        self._get_workflow_run_transient_failures = get_workflow_run_transient_failures
        self._get_workflow_run_fail_after = get_workflow_run_fail_after
        self._get_workflow_run_call_count = 0
        self._download_failure_for_url = download_failure_for_url
        self.dispatch_calls: list[dict[str, Any]] = []
        self.get_workflow_run_calls: list[int] = []
        self.create_check_run_calls: list[dict[str, Any]] = []
        self.update_check_run_calls: list[dict[str, Any]] = []
        self.list_artifacts_calls: list[int] = []
        self.download_calls: list[tuple[str, Path]] = []

    async def create_workflow_dispatch(
        self,
        owner: str,
        repo: str,
        workflow_id: str | int,
        ref: str,
        inputs: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> GitHubResponse[WorkflowDispatchResult]:
        self.dispatch_calls.append(
            {"owner": owner, "repo": repo, "workflow_id": workflow_id, "ref": ref, "inputs": inputs}
        )
        if "create_workflow_dispatch" in self._fail_at:
            raise self._fail_at["create_workflow_dispatch"]
        return _wrap(WorkflowDispatchResult(workflow_run_id=123))

    async def get_workflow_run(
        self, owner: str, repo: str, run_id: int, timeout: float | None = None
    ) -> GitHubResponse[WorkflowRun]:
        self.get_workflow_run_calls.append(run_id)
        self._get_workflow_run_call_count += 1
        if self._get_workflow_run_call_count <= self._get_workflow_run_transient_failures:
            raise httpx.ConnectError("transient")
        if (
            self._get_workflow_run_fail_after >= 0
            and self._get_workflow_run_call_count > self._get_workflow_run_fail_after
            and "get_workflow_run" in self._fail_at
        ):
            raise self._fail_at["get_workflow_run"]
        if self._get_workflow_run_fail_after < 0 and "get_workflow_run" in self._fail_at:
            raise self._fail_at["get_workflow_run"]
        # Pop the next status; stay at the last one if we're polled extra times.
        status = self._run_statuses.pop(0) if len(self._run_statuses) > 1 else self._run_statuses[0]
        conclusion = self._conclusion if status == "completed" else None
        return _wrap(
            WorkflowRun(
                id=run_id,
                name="test-batch",
                status=status,
                conclusion=conclusion,
                html_url=self._workflow_url,
            )
        )

    async def create_check_run(
        self,
        owner: str,
        repo: str,
        name: str,
        head_sha: str,
        status: str,
        details_url: str | None = None,
        output: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> GitHubResponse[CheckRun]:
        self.create_check_run_calls.append(
            {
                "owner": owner,
                "repo": repo,
                "name": name,
                "head_sha": head_sha,
                "status": status,
                "details_url": details_url,
            }
        )
        if "create_check_run" in self._fail_at:
            raise self._fail_at["create_check_run"]
        return _wrap(CheckRun(id=999, name=name, status=status, head_sha=head_sha, html_url=details_url))

    async def update_check_run(
        self,
        owner: str,
        repo: str,
        check_run_id: int,
        status: str | None = None,
        conclusion: str | None = None,
        details_url: str | None = None,
        output: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> GitHubResponse[CheckRun]:
        self.update_check_run_calls.append(
            {
                "check_run_id": check_run_id,
                "status": status,
                "conclusion": conclusion,
                "details_url": details_url,
            }
        )
        if "update_check_run" in self._fail_at:
            raise self._fail_at["update_check_run"]
        return _wrap(CheckRun(id=check_run_id, name="test-batch", status=status or "completed", conclusion=conclusion))

    async def list_workflow_run_artifacts(
        self, owner: str, repo: str, run_id: int, per_page: int = 30, timeout: float | None = None
    ) -> AsyncIterator[GitHubResponse[ArtifactsList]]:
        self.list_artifacts_calls.append(run_id)
        yield _wrap(ArtifactsList(total_count=len(self._artifacts), artifacts=list(self._artifacts)))

    async def download_artifact(self, archive_download_url: str, dest_path: Path, timeout: float | None = None) -> None:
        self.download_calls.append((archive_download_url, dest_path))
        if "download_artifact" in self._fail_at:
            raise self._fail_at["download_artifact"]
        if self._download_failure_for_url is not None and archive_download_url == self._download_failure_for_url:
            raise RuntimeError(f"download failure for {archive_download_url}")


def _make_runner(client: _FakeClient, tmp_path: Path) -> TaskTestRunner:
    runner = TaskTestRunner(
        name="task-test-runner",
        client=client,  # type: ignore[arg-type]
        owner="DataDog",
        repo="integrations-core",
        workflow_id="test-batch.yaml",
        ref="master",
        base_sha="base-sha-aaa",
        checkout_sha="merge-sha-bbb",
        artifacts_base_path=tmp_path,
        poll_interval_seconds=0.0,
    )
    runner.queue = asyncio.Queue()
    return runner


def _drain_queue(queue: asyncio.Queue[BaseMessage]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    while not queue.empty():
        out.append(queue.get_nowait())
    return out


# ---------------------------------------------------------------------------
# _conclusion_to_status
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
    assert _conclusion_to_status(conclusion) == expected


# ---------------------------------------------------------------------------
# process_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_happy_path(tmp_path: Path) -> None:
    artifacts = [_artifact(1), _artifact(2)]
    client = _FakeClient(run_statuses=["completed"], conclusion="success", artifacts=artifacts)
    runner = _make_runner(client, tmp_path)

    batch = TestBatch(id="batch-1", job_list=[_job("j1"), _job("j2")], jobs_count=2, integrations=["ntp", "kafka"])
    await runner.process_message(batch)

    # Dispatch once, with the right shape
    assert len(client.dispatch_calls) == 1
    call = client.dispatch_calls[0]
    assert call == {
        "owner": "DataDog",
        "repo": "integrations-core",
        "workflow_id": "test-batch.yaml",
        "ref": "master",
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
    assert len(client.create_check_run_calls) == 1
    cr = client.create_check_run_calls[0]
    assert cr["head_sha"] == "base-sha-aaa"
    assert cr["status"] == "in_progress"
    assert cr["name"] == "test-batch/batch-1"
    assert cr["details_url"] == "https://github.com/o/r/actions/runs/123"

    # Both artifacts downloaded under <base>/<run_id>/<id>-<name> (collision-safe path).
    assert len(client.download_calls) == 2
    assert client.download_calls[0] == (
        "https://api.github.com/artifact/1/zip",
        tmp_path / "123" / "1-artifact-1",
    )
    assert client.download_calls[1] == (
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
    assert len(client.update_check_run_calls) == 1
    upd = client.update_check_run_calls[0]
    assert upd["check_run_id"] == 999
    assert upd["status"] == "completed"
    assert upd["conclusion"] == "success"


@pytest.mark.asyncio
async def test_process_message_failure_path(tmp_path: Path) -> None:
    client = _FakeClient(run_statuses=["completed"], conclusion="failure", artifacts=[_artifact(1)])
    runner = _make_runner(client, tmp_path)

    batch = TestBatch(id="batch-2", job_list=[_job()], jobs_count=1, integrations=["ntp"])
    await runner.process_message(batch)

    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    finished = submitted[0]
    assert isinstance(finished, BatchFinished)
    assert finished.status == "failure"

    assert len(client.update_check_run_calls) == 1
    assert client.update_check_run_calls[0]["status"] == "completed"
    assert client.update_check_run_calls[0]["conclusion"] == "failure"


@pytest.mark.asyncio
async def test_process_message_polls_until_completed(tmp_path: Path) -> None:
    statuses = ["queued", "in_progress", "in_progress", "completed"]
    client = _FakeClient(run_statuses=statuses, conclusion="success", artifacts=[])
    runner = _make_runner(client, tmp_path)

    batch = TestBatch(id="batch-3", job_list=[_job()], jobs_count=1, integrations=["ntp"])
    await runner.process_message(batch)

    # Initial get + 3 polls until "completed" pops out.
    assert len(client.get_workflow_run_calls) == len(statuses)
    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    assert isinstance(submitted[0], BatchFinished)
    assert submitted[0].status == "success"


@pytest.mark.asyncio
async def test_process_message_skips_expired_artifacts(tmp_path: Path) -> None:
    artifacts = [
        _artifact(1),
        _artifact(2, expired=True),
        _artifact(3, archive_download_url=None),
    ]
    client = _FakeClient(run_statuses=["completed"], conclusion="success", artifacts=artifacts)
    runner = _make_runner(client, tmp_path)

    batch = TestBatch(id="batch-4", job_list=[_job()], jobs_count=1, integrations=["ntp"])
    await runner.process_message(batch)

    # Only the non-expired artifact with a download URL should be fetched.
    assert len(client.download_calls) == 1
    assert client.download_calls[0][0] == "https://api.github.com/artifact/1/zip"


# ---------------------------------------------------------------------------
# Error paths — try/finally always closes the check
# ---------------------------------------------------------------------------


def _batch(batch_id: str = "batch-err") -> TestBatch:
    return TestBatch(id=batch_id, job_list=[_job()], jobs_count=1, integrations=["ntp"])


@pytest.mark.parametrize(
    "failure_point",
    [
        "create_workflow_dispatch",
        "get_workflow_run_initial",
        "get_workflow_run_mid_poll",
        "update_check_run",
        "submit_message",
    ],
)
@pytest.mark.asyncio
async def test_process_message_failures_propagate_and_close_check_run(tmp_path: Path, failure_point: str) -> None:
    boom = RuntimeError(f"boom-{failure_point}")
    fail_at: dict[str, Exception] = {}
    get_workflow_run_fail_after = -1
    run_statuses = ["completed"]

    if failure_point == "create_workflow_dispatch":
        fail_at = {"create_workflow_dispatch": boom}
    elif failure_point == "get_workflow_run_initial":
        fail_at = {"get_workflow_run": boom}
    elif failure_point == "get_workflow_run_mid_poll":
        fail_at = {"get_workflow_run": boom}
        get_workflow_run_fail_after = 1
        run_statuses = ["queued", "completed"]
    elif failure_point == "update_check_run":
        fail_at = {"update_check_run": boom}

    client = _FakeClient(
        run_statuses=run_statuses,
        conclusion="success",
        artifacts=[_artifact(1)],
        fail_at=fail_at,
        get_workflow_run_fail_after=get_workflow_run_fail_after,
    )
    runner = _make_runner(client, tmp_path)

    if failure_point == "submit_message":

        class _BoomQueue:
            def put_nowait(self, _: Any) -> None:
                raise boom

        runner.queue = _BoomQueue()  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match=f"boom-{failure_point}"):
        await runner.process_message(_batch())

    if failure_point in ("create_workflow_dispatch", "get_workflow_run_initial"):
        # Failure happened before the check was opened.
        assert client.create_check_run_calls == []
        assert client.update_check_run_calls == []
        return

    # In every other case the check run was opened and the finally closed it.
    assert len(client.create_check_run_calls) == 1
    assert len(client.update_check_run_calls) == 1
    closed = client.update_check_run_calls[0]
    assert closed["status"] == "completed"

    if failure_point == "submit_message":
        # Workflow completed cleanly; finally closed with success before submit raised.
        assert closed["conclusion"] == "success"
    elif failure_point == "update_check_run":
        # The close itself raised; the recorded call captures the attempted conclusion.
        assert closed["conclusion"] in ("success", "cancelled")
    else:
        # Any other failure inside the try-block leaves final_conclusion at "cancelled".
        assert closed["conclusion"] == "cancelled"


@pytest.mark.asyncio
async def test_process_message_times_out_when_run_never_completes(tmp_path: Path) -> None:
    client = _FakeClient(run_statuses=["in_progress"], conclusion="success", artifacts=[])
    runner = TaskTestRunner(
        name="t",
        client=client,  # type: ignore[arg-type]
        owner="o",
        repo="r",
        workflow_id="wf",
        ref="main",
        base_sha="abc",
        checkout_sha="def",
        artifacts_base_path=tmp_path,
        poll_interval_seconds=0.0,
        max_wait_seconds=0.0,
    )
    runner.queue = asyncio.Queue()
    await runner.process_message(_batch())

    assert len(client.update_check_run_calls) == 1
    assert client.update_check_run_calls[0]["conclusion"] == "timed_out"
    assert _drain_queue(runner.queue) == []


@pytest.mark.asyncio
async def test_get_workflow_run_retries_on_transient_then_succeeds(tmp_path: Path) -> None:
    client = _FakeClient(
        run_statuses=["queued", "completed"],
        conclusion="success",
        artifacts=[],
        get_workflow_run_transient_failures=2,
    )
    runner = TaskTestRunner(
        name="t",
        client=client,  # type: ignore[arg-type]
        owner="o",
        repo="r",
        workflow_id="wf",
        ref="main",
        base_sha="abc",
        checkout_sha="def",
        artifacts_base_path=tmp_path,
        poll_interval_seconds=0.0,
        max_wait_seconds=300.0,
        transient_retry_attempts=3,
        transient_retry_base_seconds=0.0,
        transient_retry_factor=1.0,
    )
    runner.queue = asyncio.Queue()

    await runner.process_message(_batch())

    # 2 transient failures + 1 success on the initial GET (call 3), then 1 poll → "completed" (call 4).
    assert len(client.get_workflow_run_calls) == 4
    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    assert isinstance(submitted[0], BatchFinished)
    assert submitted[0].status == "success"
    assert client.update_check_run_calls[0]["conclusion"] == "success"


@pytest.mark.asyncio
async def test_download_failure_for_one_artifact_does_not_abort_others(tmp_path: Path) -> None:
    artifacts = [_artifact(1), _artifact(2), _artifact(3)]
    client = _FakeClient(
        run_statuses=["completed"],
        conclusion="success",
        artifacts=artifacts,
        download_failure_for_url="https://api.github.com/artifact/2/zip",
    )
    runner = _make_runner(client, tmp_path)

    await runner.process_message(_batch())

    # All three were attempted; the failure for #2 didn't abort #3.
    urls = [call[0] for call in client.download_calls]
    assert urls == [
        "https://api.github.com/artifact/1/zip",
        "https://api.github.com/artifact/2/zip",
        "https://api.github.com/artifact/3/zip",
    ]
    submitted = _drain_queue(runner.queue)
    assert len(submitted) == 1
    assert isinstance(submitted[0], BatchFinished)
    assert submitted[0].status == "success"
    assert client.update_check_run_calls[0]["conclusion"] == "success"
