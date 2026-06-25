# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskTestGatherer processor."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, UpdatePRComment
from ddev.cli.ci.tests.task_test_gatherer import TaskTestGatherer
from ddev.event_bus.orchestrator import BaseMessage
from ddev.utils.github_async.models import JobStep, WorkflowJob

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"

COVERAGE_XML = (FIXTURES / "coverage-sample.xml").read_text(encoding="utf-8")
JUNIT_PASSING = (FIXTURES / "test-unit-py3.13-4.4.xml").read_text(encoding="utf-8")
JUNIT_E2E = (FIXTURES / "test-e2e-py3.13-4.4.xml").read_text(encoding="utf-8")
JUNIT_FAILING = (FIXTURES / "test-unit-failing.xml").read_text(encoding="utf-8")

# The single failing test case in JUNIT_FAILING, as parsed into a classname::name identifier.
FAILING_TEST_ID = "nagios.tests.test_nagios.TestEventLogTailer::test_line_parser"


def _batch_job(
    name: str,
    target: str = "ntp",
    environment: str = "py3.13",
    platform: str = "linux",
    runner: str = "ubuntu-latest",
) -> BatchJob:
    return BatchJob(
        name=name,
        target=target,
        runner=runner,
        environment=environment,
        platform=platform,
        unit_tests=True,
        e2e_tests=False,
    )


def _make_job_tree(
    artifacts_path: Path,
    job_name: str,
    environment: str = "py3.13",
    *,
    coverage: bool = True,
    junit: str | None = JUNIT_PASSING,
    e2e: bool = True,
) -> Path:
    job_dir = artifacts_path / job_name
    job_dir.mkdir(parents=True)
    if coverage:
        (job_dir / "coverage.xml").write_text(COVERAGE_XML, encoding="utf-8")
    if junit is not None:
        (job_dir / f"test-unit-{environment}.xml").write_text(junit, encoding="utf-8")
    if e2e:
        (job_dir / f"test-e2e-{environment}.xml").write_text(JUNIT_E2E, encoding="utf-8")
    return job_dir


def _workflow_job(name: str, conclusion: str, failed_step: str | None = None, run_id: int = 100) -> WorkflowJob:
    steps = [JobStep(name=failed_step, status="completed", conclusion="failure")] if failed_step else []
    return WorkflowJob(id=1, run_id=run_id, name=name, status="completed", conclusion=conclusion, steps=steps)


def _batch_finished(artifacts_path: Path, **overrides) -> BatchFinished:
    defaults = {
        "id": "batch-1",
        "status": "success",
        "run_id": 100,
        "workflow_url": "https://github.com/o/r/actions/runs/100",
        "artifacts_path": str(artifacts_path),
        "job_list": [_batch_job("j1")],
        "workflow_jobs": None,
    }
    defaults.update(overrides)
    return BatchFinished(**defaults)


def _drain_queue(queue: asyncio.Queue[BaseMessage]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    while not queue.empty():
        messages.append(queue.get_nowait())
    return messages


def _make_gatherer(tmp_path: Path, expected_batches: int = 1) -> TaskTestGatherer:
    gatherer = TaskTestGatherer("gatherer", output_base_path=tmp_path / "out", expected_batches=expected_batches)
    gatherer.queue = asyncio.Queue()
    return gatherer


# ---------------------------------------------------------------------------
# process_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_organizes_artifacts_and_emits_update(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1")

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(
        _batch_finished(artifacts, job_list=[_batch_job("j1")], workflow_jobs=[_workflow_job("j1", "success")])
    )

    messages = _drain_queue(gatherer.queue)
    assert len(messages) == 1
    update = messages[0]
    assert isinstance(update, UpdatePRComment)
    assert update.done is True
    assert len(update.workflows) == 1
    status = update.workflows[0]
    assert status.id == 100
    assert status.success_count == 1
    assert status.failed_count == 0
    assert status.failed_checks == []

    assert (tmp_path / "out" / "coverage" / "ntp-py3.13-linux-ubuntu-latest.xml").is_file()
    assert (tmp_path / "out" / "test_results" / "ntp-py3.13-linux-ubuntu-latest-test-unit-py3.13.xml").is_file()
    assert (tmp_path / "out" / "test_results" / "ntp-py3.13-linux-ubuntu-latest-test-e2e-py3.13.xml").is_file()


@pytest.mark.asyncio
async def test_failure_path_records_failed_step_and_tests(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1", junit=JUNIT_FAILING)

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(
        _batch_finished(
            artifacts,
            status="failure",
            job_list=[_batch_job("j1")],
            workflow_jobs=[_workflow_job("j1", "failure", failed_step="Run unit tests")],
        )
    )

    status = _drain_queue(gatherer.queue)[0].workflows[0]
    assert status.failed_count == 1
    assert [check.integration for check in status.failed_checks] == ["ntp"]

    result = gatherer._results_by_run[100][0]
    assert result.status == "failure"
    assert result.failed_step == "Run unit tests"
    assert result.failed_tests == [FAILING_TEST_ID]


@pytest.mark.asyncio
async def test_failed_check_carries_environment_error_and_tests(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1", junit=JUNIT_FAILING)

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(
        _batch_finished(
            artifacts,
            status="failure",
            job_list=[_batch_job("j1")],
            workflow_jobs=[_workflow_job("j1", "failure", failed_step="Run unit tests")],
        )
    )

    check = _drain_queue(gatherer.queue)[0].workflows[0].failed_checks[0]
    assert check.environment == "py3.13"
    assert check.failed_step == "Run unit tests"
    assert check.failed_tests == [FAILING_TEST_ID]


@pytest.mark.asyncio
async def test_timed_out_batch_marks_all_jobs_failed(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path)
    job_list = [_batch_job("j1", environment="py3.12"), _batch_job("j2", target="kafka", environment="py3.13")]
    await gatherer.process_message(_batch_finished("", status="failure", run_id=300, job_list=job_list, timed_out=True))

    status = _drain_queue(gatherer.queue)[0].workflows[0]
    assert status.failed_count == 2
    assert {check.failed_step for check in status.failed_checks} == {"timed out"}


@pytest.mark.asyncio
async def test_multiple_jobs_aggregate_into_one_workflow_status(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1", environment="py3.12", junit=JUNIT_PASSING)
    _make_job_tree(artifacts, "j2", environment="py3.13", junit=JUNIT_FAILING)

    gatherer = _make_gatherer(tmp_path)
    job_list = [_batch_job("j1", environment="py3.12"), _batch_job("j2", target="kafka", environment="py3.13")]
    jobs = [_workflow_job("j1", "success"), _workflow_job("j2", "failure")]
    await gatherer.process_message(_batch_finished(artifacts, status="failure", job_list=job_list, workflow_jobs=jobs))

    status = _drain_queue(gatherer.queue)[0].workflows[0]
    assert status.success_count == 1
    assert status.failed_count == 1
    assert [check.integration for check in status.failed_checks] == ["kafka"]


@pytest.mark.asyncio
async def test_same_integration_different_platforms_do_not_overwrite(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1", e2e=False)
    _make_job_tree(artifacts, "j2", e2e=False)

    gatherer = _make_gatherer(tmp_path)
    job_list = [
        _batch_job("j1", platform="linux", runner="ubuntu-latest"),
        _batch_job("j2", platform="windows", runner="windows-latest"),
    ]
    jobs = [_workflow_job("j1", "success"), _workflow_job("j2", "success")]
    await gatherer.process_message(_batch_finished(artifacts, job_list=job_list, workflow_jobs=jobs))

    # Both jobs share target+environment but differ by platform/runner: each keeps its own file.
    coverage_dir = tmp_path / "out" / "coverage"
    assert (coverage_dir / "ntp-py3.13-linux-ubuntu-latest.xml").is_file()
    assert (coverage_dir / "ntp-py3.13-windows-windows-latest.xml").is_file()


@pytest.mark.asyncio
async def test_no_pr_update_until_final_batch(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path, expected_batches=2)

    artifacts1 = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts1, "j1")
    await gatherer.process_message(
        _batch_finished(
            artifacts1, id="b1", run_id=100, job_list=[_batch_job("j1")], workflow_jobs=[_workflow_job("j1", "success")]
        )
    )

    # First of two batches: nothing emitted yet — the PR must not be updated mid-run.
    assert _drain_queue(gatherer.queue) == []

    artifacts2 = tmp_path / "artifacts" / "200"
    _make_job_tree(artifacts2, "j1")
    await gatherer.process_message(
        _batch_finished(
            artifacts2,
            id="b2",
            run_id=200,
            job_list=[_batch_job("j1")],
            workflow_jobs=[_workflow_job("j1", "success", run_id=200)],
        )
    )

    # Final batch in: exactly one done=True update aggregating both runs.
    messages = _drain_queue(gatherer.queue)
    assert len(messages) == 1
    assert messages[0].done is True
    assert {status.id for status in messages[0].workflows} == {100, 200}


@pytest.mark.asyncio
async def test_per_job_status_comes_from_forwarded_jobs(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1", junit=JUNIT_FAILING)
    jobs = [
        WorkflowJob(
            id=1,
            run_id=100,
            name="j1",
            status="completed",
            conclusion="failure",
            steps=[
                JobStep(name="Checkout", status="completed", conclusion="success"),
                JobStep(name="Run unit tests", status="completed", conclusion="failure"),
            ],
        )
    ]

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(
        _batch_finished(artifacts, status="failure", job_list=[_batch_job("j1")], workflow_jobs=jobs)
    )

    result = gatherer._results_by_run[100][0]
    assert result.status == "failure"
    assert result.failed_step == "Run unit tests"


@pytest.mark.asyncio
async def test_missing_artifact_dir_is_skipped(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    artifacts.mkdir(parents=True)

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(
        _batch_finished(artifacts, job_list=[_batch_job("j1")], workflow_jobs=[_workflow_job("j1", "success")])
    )

    result = gatherer._results_by_run[100][0]
    assert result.status == "success"
    assert result.failed_tests == []
    assert not (tmp_path / "out").exists()


@pytest.mark.asyncio
async def test_malformed_junit_is_swallowed(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1", junit="<testsuite><testcase>")

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(
        _batch_finished(artifacts, job_list=[_batch_job("j1")], workflow_jobs=[_workflow_job("j1", "success")])
    )

    assert gatherer._results_by_run[100][0].failed_tests == []


def test_locate_job_dir_anchors_token(tmp_path: Path) -> None:
    (tmp_path / "j12").mkdir()
    # "j12" must NOT satisfy a lookup for "j1".
    assert TaskTestGatherer._locate_job_dir(tmp_path, "j1") is None
    # A decorated directory containing "j1" as a bounded token matches.
    (tmp_path / "coverage-j1").mkdir()
    assert TaskTestGatherer._locate_job_dir(tmp_path, "j1") == tmp_path / "coverage-j1"
    # An exact directory name always wins.
    (tmp_path / "j1").mkdir()
    assert TaskTestGatherer._locate_job_dir(tmp_path, "j1") == tmp_path / "j1"


def test_build_done_message(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path)
    message = gatherer.build_done_message("final")
    assert isinstance(message, UpdatePRComment)
    assert message.id == "final"
    assert message.done is True
    assert message.workflows == []
