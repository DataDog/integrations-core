# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskTestGatherer processor.

The scenario test at the bottom replays the 12-job / 3-batch run from the dispatcher source of truth
(``~/.claude/plans/dispatcher.md``): the gatherer consumes one ``BatchFinished`` per batch and emits a
single ``UpdatePRComment`` with a monotonically increasing revision, keeping a full in-memory registry
of every job's result — not just failures.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, BatchJobResult, JobResult, Platform, UpdatePRComment
from ddev.cli.ci.tests.task_test_gatherer import TaskTestGatherer
from ddev.event_bus.orchestrator import BaseMessage
from ddev.utils.github_async.models import JobStep, WorkflowJob
from ddev.utils.junit import TestStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"

# Sample report contents captured from real CI runs. Filenames label the content (passing/failing);
# the on-disk artifact name a job actually produces (``test-{unit,e2e}-{env}.xml``) is built by
# ``_make_job_tree`` — failure is encoded in the XML, never in the filename.
COVERAGE_XML = (FIXTURES / "coverage-sample.xml").read_text(encoding="utf-8")
JUNIT_PASSING = (FIXTURES / "junit-unit-passing.sample.xml").read_text(encoding="utf-8")
JUNIT_E2E = (FIXTURES / "junit-e2e-passing.sample.xml").read_text(encoding="utf-8")
JUNIT_FAILING = (FIXTURES / "junit-unit-failing.sample.xml").read_text(encoding="utf-8")

# The single failing test case in JUNIT_FAILING, as a classname::name identifier.
FAILING_TEST_ID = "nagios.tests.test_nagios.TestEventLogTailer::test_line_parser"


def _batch_job(
    name: str,
    target: str = "ntp",
    environment: str = "py3.13",
    platform: Platform = Platform.LINUX,
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


def _batch_job_result(
    job: BatchJob,
    workflow_job: WorkflowJob | None = None,
    artifact_dir: Path | None = None,
) -> BatchJobResult:
    """A single pre-correlated job result, as the runner would emit on BatchFinished.batch_jobs."""
    base = job.artifact_name()
    return BatchJobResult(
        job=job,
        workflow_job=workflow_job,
        artifact_name_path=str(artifact_dir) if artifact_dir is not None else None,
        unit_artifact_name=f"unit-{base}",
        e2e_artifact_name=f"e2e-{base}",
        coverage_artifact_name=f"coverage-{base}",
    )


def _batch_finished(artifacts_path: Path | str, **overrides) -> BatchFinished:
    defaults = {
        "id": "batch-1",
        "status": "success",
        "run_id": 100,
        "workflow_url": "https://github.com/o/r/actions/runs/100",
        "artifacts_path": str(artifacts_path),
        "batch_jobs": [_batch_job_result(_batch_job("j1"))],
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


def _totals(update: UpdatePRComment) -> tuple[int, int, int, int]:
    """The update's aggregate (passed, failed, skipped, complete) job counts."""
    return (update.passed, update.failed, update.skipped, update.complete)


def _failed_ids(result: JobResult) -> list[str]:
    return [case.identifier for case in result.failed_tests]


def _find_result(update: UpdatePRComment, integration: str) -> JobResult:
    return next(
        result for workflow in update.workflows for result in workflow.results if result.integration == integration
    )


# ---------------------------------------------------------------------------
# process_message
# ---------------------------------------------------------------------------


def test_happy_path_organizes_artifacts_and_emits_update(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts, batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), job_dir)]
        )
    )

    messages = _drain_queue(gatherer.queue)
    assert len(messages) == 1
    update = messages[0]
    assert isinstance(update, UpdatePRComment)
    assert update.revision == 1
    assert update.done is True
    assert len(update.workflows) == 1
    status = update.workflows[0]
    assert status.id == 100
    assert status.success_count == 1
    assert status.failed_count == 0
    assert status.skipped_count == 0
    assert len(status.results) == 1

    assert (tmp_path / "out" / "coverage" / "ntp-py3.13-linux.xml").is_file()
    assert (tmp_path / "out" / "test_results" / "ntp-py3.13-linux-test-unit-py3.13.xml").is_file()
    assert (tmp_path / "out" / "test_results" / "ntp-py3.13-linux-test-e2e-py3.13.xml").is_file()


def test_failure_path_records_failed_steps_and_reports(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1", junit=JUNIT_FAILING, e2e=False)

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts,
            status="failure",
            batch_jobs=[
                _batch_job_result(
                    _batch_job("j1"), _workflow_job("j1", "failure", failed_step="Run unit tests"), job_dir
                )
            ],
        )
    )

    status = _drain_queue(gatherer.queue)[0].workflows[0]
    assert status.failed_count == 1

    result = gatherer._results_by_batch["batch-1"][0]
    assert result.status == "failure"
    assert result.integration == "ntp"
    assert result.environment == "py3.13"
    assert result.failed_steps == ["Run unit tests"]
    assert _failed_ids(result) == [FAILING_TEST_ID]


def test_full_report_keeps_passing_tests(tmp_path: Path) -> None:
    # The failing fixture holds one failing and one passing test; the registry keeps both, not just
    # the failure (dispatcher.md: full registry of everything that happened).
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1", junit=JUNIT_FAILING, e2e=False)

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts,
            status="failure",
            batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "failure"), job_dir)],
        )
    )

    result = gatherer._results_by_batch["batch-1"][0]
    suite = result.reports[0].test_suites[0]
    assert suite.reported_counts.tests == 2
    assert suite.reported_counts.passed == 1
    statuses = {case.identifier: case.status for case in suite.test_cases}
    assert statuses[FAILING_TEST_ID] == TestStatus.FAILED
    assert statuses["nagios.tests.test_nagios.TestPerfDataTailer::test_host_perfdata"] == TestStatus.PASSED


def test_timed_out_batch_marks_all_jobs_failed(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path)
    batch_jobs = [
        _batch_job_result(_batch_job("j1", environment="py3.12")),
        _batch_job_result(_batch_job("j2", target="kafka", environment="py3.13")),
    ]
    gatherer.process_message(_batch_finished("", status="failure", run_id=300, batch_jobs=batch_jobs, timed_out=True))

    status = _drain_queue(gatherer.queue)[0].workflows[0]
    assert status.failed_count == 2
    assert {tuple(result.failed_steps) for result in status.results} == {("timed out",)}


def test_multiple_jobs_aggregate_into_one_workflow_status(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    j1_dir = _make_job_tree(artifacts, "j1", environment="py3.12", junit=JUNIT_PASSING)
    j2_dir = _make_job_tree(artifacts, "j2", environment="py3.13", junit=JUNIT_FAILING)

    gatherer = _make_gatherer(tmp_path)
    batch_jobs = [
        _batch_job_result(_batch_job("j1", environment="py3.12"), _workflow_job("j1", "success"), j1_dir),
        _batch_job_result(
            _batch_job("j2", target="kafka", environment="py3.13"), _workflow_job("j2", "failure"), j2_dir
        ),
    ]
    gatherer.process_message(_batch_finished(artifacts, status="failure", batch_jobs=batch_jobs))

    status = _drain_queue(gatherer.queue)[0].workflows[0]
    assert status.success_count == 1
    assert status.failed_count == 1
    failed = [result.integration for result in status.results if result.status == "failure"]
    assert failed == ["kafka"]


def test_same_integration_different_platforms_do_not_overwrite(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    j1_dir = _make_job_tree(artifacts, "j1", e2e=False)
    j2_dir = _make_job_tree(artifacts, "j2", e2e=False)

    gatherer = _make_gatherer(tmp_path)
    batch_jobs = [
        _batch_job_result(
            _batch_job("j1", platform=Platform.LINUX, runner="ubuntu-latest"), _workflow_job("j1", "success"), j1_dir
        ),
        _batch_job_result(
            _batch_job("j2", platform=Platform.WINDOWS, runner="windows-latest"), _workflow_job("j2", "success"), j2_dir
        ),
    ]
    gatherer.process_message(_batch_finished(artifacts, batch_jobs=batch_jobs))

    # Both jobs share target+environment but differ by platform/runner: each keeps its own file.
    coverage_dir = tmp_path / "out" / "coverage"
    assert (coverage_dir / "ntp-py3.13-linux.xml").is_file()
    assert (coverage_dir / "ntp-py3.13-windows.xml").is_file()


def test_emits_update_per_batch_done_on_last(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path, expected_batches=2)

    artifacts1 = tmp_path / "artifacts" / "100"
    j1_dir = _make_job_tree(artifacts1, "j1")
    gatherer.process_message(
        _batch_finished(
            artifacts1,
            id="b1",
            run_id=100,
            batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), j1_dir)],
        )
    )

    # First of two batches: an update is emitted immediately (live updates), but not yet done.
    first = _drain_queue(gatherer.queue)
    assert len(first) == 1
    assert first[0].revision == 1
    assert first[0].done is False
    assert {status.id for status in first[0].workflows} == {100}

    artifacts2 = tmp_path / "artifacts" / "200"
    j1_dir2 = _make_job_tree(artifacts2, "j1")
    gatherer.process_message(
        _batch_finished(
            artifacts2,
            id="b2",
            run_id=200,
            batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success", run_id=200), j1_dir2)],
        )
    )

    # Final batch: revision 2, done, aggregating both runs.
    second = _drain_queue(gatherer.queue)
    assert len(second) == 1
    assert second[0].revision == 2
    assert second[0].done is True
    assert {status.id for status in second[0].workflows} == {100, 200}


def test_multiple_failing_steps_all_collected(tmp_path: Path) -> None:
    # A workflow can run on-failure steps, so more than one step may conclude in failure.
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1", e2e=False)
    workflow_job = WorkflowJob(
        id=1,
        run_id=100,
        name="j1",
        status="completed",
        conclusion="failure",
        steps=[
            JobStep(name="Run unit tests", status="completed", conclusion="failure"),
            JobStep(name="Upload logs on failure", status="completed", conclusion="failure"),
            JobStep(name="Checkout", status="completed", conclusion="success"),
        ],
    )

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts, status="failure", batch_jobs=[_batch_job_result(_batch_job("j1"), workflow_job, job_dir)]
        )
    )

    result = gatherer._results_by_batch["batch-1"][0]
    assert result.failed_steps == ["Run unit tests", "Upload logs on failure"]


def test_per_job_status_comes_from_correlated_job(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1", junit=JUNIT_FAILING, e2e=False)
    workflow_job = WorkflowJob(
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

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts, status="failure", batch_jobs=[_batch_job_result(_batch_job("j1"), workflow_job, job_dir)]
        )
    )

    result = gatherer._results_by_batch["batch-1"][0]
    assert result.status == "failure"
    assert result.failed_steps == ["Run unit tests"]


def test_missing_artifact_dir_is_skipped(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts, batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), None)]
        )
    )

    result = gatherer._results_by_batch["batch-1"][0]
    assert result.status == "success"
    assert result.reports == ()
    assert not (tmp_path / "out").exists()


def test_malformed_junit_is_swallowed(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1", junit="<testsuite><testcase>", e2e=False)

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts, batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), job_dir)]
        )
    )

    result = gatherer._results_by_batch["batch-1"][0]
    assert result.status == "success"
    assert result.reports == ()  # malformed junit skipped; coverage.xml is not a JUnit report


def test_missing_workflow_job_raises(tmp_path: Path) -> None:
    # Correlation is the runner's job; a job without a workflow job on a non-timed-out batch is a bug.
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")

    gatherer = _make_gatherer(tmp_path)
    with pytest.raises(ValueError, match="No workflow job correlated"):
        gatherer.process_message(
            _batch_finished(artifacts, batch_jobs=[_batch_job_result(_batch_job("j1"), None, job_dir)])
        )


def test_empty_batch_jobs_is_skipped(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(_batch_finished("", batch_jobs=[]))

    assert _drain_queue(gatherer.queue) == []
    assert gatherer._results_by_batch == {}
    assert gatherer._received_batches == 0


def test_duplicate_batch_finished_is_ignored(tmp_path: Path) -> None:
    # A duplicate BatchFinished for a run_id already gathered must not re-count the batch or inflate
    # the revision (invariant 2: one revision per consumed batch).
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")
    batch = _batch_finished(
        artifacts, batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), job_dir)]
    )

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(batch)
    first = _drain_queue(gatherer.queue)
    assert len(first) == 1
    assert first[0].revision == 1

    gatherer.process_message(batch)
    assert _drain_queue(gatherer.queue) == []
    assert gatherer._received_batches == 1


def test_no_emission_without_batch_finished(tmp_path: Path) -> None:
    # Invariant: the gatherer's state changes only when a BatchFinished is consumed.
    gatherer = _make_gatherer(tmp_path)
    assert _drain_queue(gatherer.queue) == []
    assert gatherer._results_by_batch == {}
    assert gatherer._received_batches == 0


def test_build_update_message(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path)
    message = gatherer.build_update_message("final", revision=2, done=True)
    assert isinstance(message, UpdatePRComment)
    assert message.id == "final"
    assert message.revision == 2
    assert message.done is True
    assert message.workflows == []


# ---------------------------------------------------------------------------
# dispatcher.md scenario: 12 jobs, 3 batches of 4
# ---------------------------------------------------------------------------


def _scenario_job(
    artifacts: Path,
    target: str,
    conclusion: str,
    junit: str | None,
    *,
    run_id: int,
    platform: Platform = Platform.LINUX,
    runner: str = "ubuntu-latest",
    failed_step: str | None = None,
) -> BatchJobResult:
    job = _batch_job(target, target=target, environment="py3.12", platform=platform, runner=runner)
    job_dir = _make_job_tree(artifacts, target, environment="py3.12", junit=junit, e2e=False)
    workflow_job = _workflow_job(target, conclusion, failed_step=failed_step, run_id=run_id)
    return _batch_job_result(job, workflow_job, job_dir)


def test_dispatcher_scenario_three_batches(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path, expected_batches=3)

    # Batch-01 (steps 10-11): 4 jobs pass.
    a1 = tmp_path / "artifacts" / "1"
    batch_01 = [
        _scenario_job(a1, "postgres", "success", JUNIT_PASSING, run_id=1),
        _scenario_job(a1, "redis", "success", JUNIT_PASSING, run_id=1),
        _scenario_job(
            a1, "ntp", "success", JUNIT_PASSING, run_id=1, platform=Platform.WINDOWS, runner="windows-latest"
        ),
        _scenario_job(a1, "kafka", "success", JUNIT_PASSING, run_id=1),
    ]
    gatherer.process_message(_batch_finished(a1, id="b1", run_id=1, batch_jobs=batch_01))
    rev1 = _drain_queue(gatherer.queue)
    assert len(rev1) == 1
    assert (rev1[0].revision, rev1[0].done) == (1, False)
    assert _totals(rev1[0]) == (4, 0, 0, 4)

    # Batch-02 (steps 13-14): 3 pass + 1 fail (mysql py3.12 linux).
    a2 = tmp_path / "artifacts" / "2"
    batch_02 = [
        _scenario_job(a2, "disk", "success", JUNIT_PASSING, run_id=2),
        _scenario_job(a2, "snmp", "success", JUNIT_PASSING, run_id=2),
        _scenario_job(a2, "http_check", "success", JUNIT_PASSING, run_id=2),
        _scenario_job(a2, "mysql", "failure", JUNIT_FAILING, run_id=2, failed_step="Run unit tests"),
    ]
    gatherer.process_message(_batch_finished(a2, id="b2", run_id=2, batch_jobs=batch_02))
    rev2 = _drain_queue(gatherer.queue)
    assert len(rev2) == 1
    assert (rev2[0].revision, rev2[0].done) == (2, False)
    assert _totals(rev2[0]) == (7, 1, 0, 8)

    # Batch-03 (steps 15-16): 3 pass + 1 skip. Terminal — revision 3, done.
    a3 = tmp_path / "artifacts" / "3"
    batch_03 = [
        _scenario_job(a3, "nginx", "success", JUNIT_PASSING, run_id=3),
        _scenario_job(a3, "kubelet", "success", JUNIT_PASSING, run_id=3),
        _scenario_job(a3, "vault", "success", JUNIT_PASSING, run_id=3),
        _scenario_job(a3, "consul", "skipped", None, run_id=3),
    ]
    gatherer.process_message(_batch_finished(a3, id="b3", run_id=3, batch_jobs=batch_03))
    rev3 = _drain_queue(gatherer.queue)
    assert len(rev3) == 1
    final = rev3[0]
    assert (final.revision, final.done) == (3, True)
    assert _totals(final) == (10, 1, 1, 12)

    # Every batch's workflow is present with its batch id, URL, and the full per-job registry.
    assert {workflow.id for workflow in final.workflows} == {1, 2, 3}
    assert {workflow.batch_id for workflow in final.workflows} == {"b1", "b2", "b3"}
    assert all(workflow.url for workflow in final.workflows)
    assert sum(len(workflow.results) for workflow in final.workflows) == 12

    # Batch-level labels for the "Batch-0X : passed/failed" comment line (b3 is success: 3 pass + 1 skip).
    labels = {workflow.batch_id: workflow.status for workflow in final.workflows}
    assert labels == {"b1": "success", "b2": "failure", "b3": "success"}

    # The failing job surfaces its failed step and failing test.
    mysql = _find_result(final, "mysql")
    assert mysql.status == "failure"
    assert mysql.failed_steps == ["Run unit tests"]
    assert FAILING_TEST_ID in _failed_ids(mysql)

    # The skipped job is recorded as skipped.
    assert _find_result(final, "consul").status == "skipped"


def test_dispatcher_scenario_revisions_are_monotonic(tmp_path: Path) -> None:
    # Each consumed BatchFinished yields exactly one revision, strictly increasing (invariant #2).
    gatherer = _make_gatherer(tmp_path, expected_batches=3)
    revisions: list[int] = []
    for index in (1, 2, 3):
        artifacts = tmp_path / "artifacts" / str(index)
        jobs = [_scenario_job(artifacts, f"int{index}", "success", JUNIT_PASSING, run_id=index)]
        gatherer.process_message(_batch_finished(artifacts, id=f"b{index}", run_id=index, batch_jobs=jobs))
        emitted = _drain_queue(gatherer.queue)
        assert len(emitted) == 1
        revisions.append(emitted[0].revision)

    assert revisions == [1, 2, 3]
