# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskTestGatherer processor."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, UpdatePRComment
from ddev.cli.ci.tests.task_test_gatherer import TaskTestGatherer
from ddev.event_bus.orchestrator import BaseMessage
from ddev.utils.github_async.models import JobStep, WorkflowJob

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COVERAGE_XML = '<?xml version="1.0"?>\n<coverage line-rate="1.0"></coverage>\n'

JUNIT_PASSING = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="1" failures="0">
  <testcase classname="tests.test_a" name="test_ok"/>
</testsuite>
"""

JUNIT_FAILING = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="2" failures="1">
  <testcase classname="tests.test_a" name="test_ok"/>
  <testcase classname="tests.test_a" name="test_fail"><failure message="boom">trace</failure></testcase>
</testsuite>
"""


def _batch_job(name: str, target: str = "ntp", environment: str = "py3.13", platform: str = "linux") -> BatchJob:
    return BatchJob(
        name=name,
        target=target,
        runner="ubuntu-latest",
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
) -> Path:
    job_dir = artifacts_path / job_name
    job_dir.mkdir(parents=True)
    if coverage:
        (job_dir / "coverage.xml").write_text(COVERAGE_XML, encoding="utf-8")
    if junit is not None:
        (job_dir / f"test-unit-{environment}.xml").write_text(junit, encoding="utf-8")
    return job_dir


def _write_metadata(artifacts_path: Path, jobs: list[dict]) -> None:
    (artifacts_path / "metadata.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")


def _batch_finished(artifacts_path: Path, **overrides) -> BatchFinished:
    defaults = {
        "id": "batch-1",
        "status": "success",
        "run_id": 100,
        "workflow_url": "https://github.com/o/r/actions/runs/100",
        "artifacts_path": str(artifacts_path),
        "job_list": [_batch_job("j1")],
        "jobs": None,
    }
    defaults.update(overrides)
    return BatchFinished(**defaults)


def _drain_queue(queue: asyncio.Queue[BaseMessage]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    while not queue.empty():
        messages.append(queue.get_nowait())
    return messages


def _make_gatherer(tmp_path: Path) -> TaskTestGatherer:
    gatherer = TaskTestGatherer("gatherer", output_base_path=tmp_path / "out")
    gatherer.queue = asyncio.Queue()
    return gatherer


# ---------------------------------------------------------------------------
# process_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_organizes_artifacts_and_emits_update(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1")
    _write_metadata(artifacts, [{"name": "j1", "conclusion": "success"}])

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(_batch_finished(artifacts, job_list=[_batch_job("j1")]))

    messages = _drain_queue(gatherer.queue)
    assert len(messages) == 1
    update = messages[0]
    assert isinstance(update, UpdatePRComment)
    assert update.done is False
    assert len(update.workflows) == 1
    status = update.workflows[0]
    assert status.id == 100
    assert status.success_count == 1
    assert status.failed_count == 0
    assert status.failed_checks == []

    assert (tmp_path / "out" / "coverage" / "ntp-py3.13.xml").is_file()
    assert (tmp_path / "out" / "test_results" / "ntp-py3.13-test-unit-py3.13.xml").is_file()


@pytest.mark.asyncio
async def test_failure_path_records_failed_step_and_tests(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1", junit=JUNIT_FAILING)
    _write_metadata(artifacts, [{"name": "j1", "conclusion": "failure", "failed_step": "Run unit tests"}])

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(_batch_finished(artifacts, status="failure", job_list=[_batch_job("j1")]))

    status = _drain_queue(gatherer.queue)[0].workflows[0]
    assert status.failed_count == 1
    assert [check.name for check in status.failed_checks] == ["ntp"]

    result = gatherer._results_by_run[100][0]
    assert result.status == "failure"
    assert result.failed_step == "Run unit tests"
    assert result.failed_tests == ["tests.test_a::test_fail"]


@pytest.mark.asyncio
async def test_failed_check_carries_environment_error_and_tests(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1", junit=JUNIT_FAILING)
    _write_metadata(artifacts, [{"name": "j1", "conclusion": "failure", "failed_step": "Run unit tests"}])

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(_batch_finished(artifacts, status="failure", job_list=[_batch_job("j1")]))

    check = _drain_queue(gatherer.queue)[0].workflows[0].failed_checks[0]
    assert check.environment == "py3.13"
    assert check.error == "Run unit tests"
    assert check.failed_tests == ["tests.test_a::test_fail"]


@pytest.mark.asyncio
async def test_timed_out_batch_marks_all_jobs_failed(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path)
    job_list = [_batch_job("j1", environment="py3.12"), _batch_job("j2", target="kafka", environment="py3.13")]
    await gatherer.process_message(
        _batch_finished("", status="failure", run_id=300, job_list=job_list, timed_out=True)
    )

    status = _drain_queue(gatherer.queue)[0].workflows[0]
    assert status.failed_count == 2
    assert {check.error for check in status.failed_checks} == {"timed out"}


@pytest.mark.asyncio
async def test_multiple_jobs_aggregate_into_one_workflow_status(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1", environment="py3.12", junit=JUNIT_PASSING)
    _make_job_tree(artifacts, "j2", environment="py3.13", junit=JUNIT_FAILING)
    _write_metadata(
        artifacts,
        [{"name": "j1", "conclusion": "success"}, {"name": "j2", "conclusion": "failure"}],
    )

    gatherer = _make_gatherer(tmp_path)
    job_list = [_batch_job("j1", environment="py3.12"), _batch_job("j2", target="kafka", environment="py3.13")]
    await gatherer.process_message(_batch_finished(artifacts, status="failure", job_list=job_list))

    status = _drain_queue(gatherer.queue)[0].workflows[0]
    assert status.success_count == 1
    assert status.failed_count == 1
    assert [check.name for check in status.failed_checks] == ["kafka"]


@pytest.mark.asyncio
async def test_accumulates_across_batches(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path)

    artifacts1 = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts1, "j1")
    _write_metadata(artifacts1, [{"name": "j1", "conclusion": "success"}])
    await gatherer.process_message(_batch_finished(artifacts1, id="b1", run_id=100, job_list=[_batch_job("j1")]))

    artifacts2 = tmp_path / "artifacts" / "200"
    _make_job_tree(artifacts2, "j1")
    _write_metadata(artifacts2, [{"name": "j1", "conclusion": "success"}])
    await gatherer.process_message(_batch_finished(artifacts2, id="b2", run_id=200, job_list=[_batch_job("j1")]))

    messages = _drain_queue(gatherer.queue)
    assert len(messages) == 2
    assert len(messages[0].workflows) == 1
    assert len(messages[1].workflows) == 2
    assert {status.id for status in messages[1].workflows} == {100, 200}


@pytest.mark.asyncio
async def test_falls_back_to_forwarded_jobs_when_no_metadata(tmp_path: Path) -> None:
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
    await gatherer.process_message(_batch_finished(artifacts, status="failure", job_list=[_batch_job("j1")], jobs=jobs))

    result = gatherer._results_by_run[100][0]
    assert result.status == "failure"
    assert result.failed_step == "Run unit tests"


@pytest.mark.asyncio
async def test_missing_artifact_dir_is_skipped(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    artifacts.mkdir(parents=True)
    _write_metadata(artifacts, [{"name": "j1", "conclusion": "success"}])

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(_batch_finished(artifacts, job_list=[_batch_job("j1")]))

    result = gatherer._results_by_run[100][0]
    assert result.status == "success"
    assert result.failed_tests == []
    assert not (tmp_path / "out").exists()


@pytest.mark.asyncio
async def test_malformed_junit_is_swallowed(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    _make_job_tree(artifacts, "j1", junit="<testsuite><testcase>")
    _write_metadata(artifacts, [{"name": "j1", "conclusion": "success"}])

    gatherer = _make_gatherer(tmp_path)
    await gatherer.process_message(_batch_finished(artifacts, job_list=[_batch_job("j1")]))

    assert gatherer._results_by_run[100][0].failed_tests == []


def test_build_done_message(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path)
    message = gatherer.build_done_message("final")
    assert isinstance(message, UpdatePRComment)
    assert message.id == "final"
    assert message.done is True
    assert message.workflows == []
