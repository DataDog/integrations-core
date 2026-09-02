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

import logging
import shutil
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from ddev.cli.ci.tests.messages import (
    BatchFinished,
    BatchJob,
    BatchJobResult,
    JobResult,
    TestBatch,
    UpdatePRComment,
    WorkflowStatus,
)
from ddev.cli.ci.tests.progress import ExecutionState, ProgressError
from ddev.cli.ci.tests.status import Status
from ddev.cli.ci.tests.task_run_reporter import RunReporterOptions, TaskRunReporter
from ddev.cli.ci.tests.task_test_gatherer import INITIAL_UPDATE_MESSAGE_ID, TaskTestGatherer
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator
from ddev.utils.github_async.models import JobStep, WorkflowJob
from ddev.utils.junit import TestStatus
from ddev.utils.platform import PlatformName
from tests.cli.ci.tests.helpers import RecordingBus, drain_queue, jobs_reported, make_job
from tests.helpers.github_async import FakeAsyncGitHubClient

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


def _batch_job(
    name: str,
    target: str = "ntp",
    environment: str = "py3.13",
    platform: PlatformName = PlatformName.LINUX,
    runner: str = "ubuntu-latest",
) -> BatchJob:
    return make_job(name, target=target, environment=environment, platform=platform, runner_labels=(runner,))


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
        "batch_id": overrides.get("id", "batch-1"),
        "status": "success",
        "run_id": 100,
        "workflow_url": "https://github.com/o/r/actions/runs/100",
        "artifacts_path": str(artifacts_path),
        "batch_jobs": [_batch_job_result(make_job("j1"))],
    }
    defaults.update(overrides)
    # The logical batch id defaults to the message id unless a test sets them apart on purpose.
    defaults.setdefault("batch_id", defaults["id"])
    return BatchFinished(**defaults)


def _test_batch(batch_id: str, jobs: list[BatchJob]) -> TestBatch:
    """One planned batch. Its message id is deliberately not its batch id: different layers."""
    return TestBatch(
        id=f"msg-{batch_id}",
        batch_id=batch_id,
        job_list=jobs,
        jobs_count=len(jobs),
        integrations=sorted({job.target for job in jobs}),
    )


def _make_gatherer(tmp_path: Path, plan: dict[str, list[BatchJob]] | None = None) -> TaskTestGatherer:
    """Gatherer primed with the complete plan, given as ``{batch_id: planned jobs}``."""
    if plan is None:
        plan = {"batch-1": [_batch_job("j1")]}
    gatherer = TaskTestGatherer(
        "gatherer",
        output_base_path=tmp_path / "out",
        batches=[_test_batch(batch_id, jobs) for batch_id, jobs in plan.items()],
    )
    gatherer.bus = RecordingBus()  # type: ignore[assignment]
    return gatherer


def _one_job_plan(*batch_ids: str) -> dict[str, list[BatchJob]]:
    return {batch_id: [_batch_job("j1")] for batch_id in batch_ids}


def _batch_progress(update: UpdatePRComment, batch_id: str):
    return next(batch for batch in update.progress.batches if batch.batch_id == batch_id)


def _totals(update: UpdatePRComment) -> tuple[int, int, int, int]:
    """The update's aggregate (passed, failed, skipped, complete) job counts."""
    progress = update.progress
    return (progress.passed, progress.failed, progress.skipped, progress.complete)


def _failed_ids(result: JobResult) -> list[str]:
    return [case.identifier for case in result.failed_tests]


def _registry(gatherer: TaskTestGatherer) -> list[WorkflowStatus]:
    """Every batch the gatherer has recorded, in the order it recorded them."""
    return list(gatherer._status_by_batch.values())


def _find_result(gatherer: TaskTestGatherer, integration: str) -> JobResult:
    return next(
        result
        for results in gatherer._results_by_batch.values()
        for result in results
        if result.integration == integration
    )


# ---------------------------------------------------------------------------
# process_message
# ---------------------------------------------------------------------------


def _stopping_before_gathering(gatherer: TaskTestGatherer, bus: RecordingBus) -> None:
    bus.stopping = True


def _stopping_once_the_last_job_is_gathered(gatherer: TaskTestGatherer, bus: RecordingBus) -> None:
    """Flips after the per-job loop, the window that loop's own check cannot see."""
    build_status = gatherer._build_workflow_status

    def cancelled_while_building(*args, **kwargs):
        bus.stopping = True
        return build_status(*args, **kwargs)

    gatherer._build_workflow_status = cancelled_while_building  # type: ignore[method-assign]


@pytest.mark.parametrize(
    "start_stopping",
    [
        pytest.param(_stopping_before_gathering, id="before_gathering"),
        pytest.param(_stopping_once_the_last_job_is_gathered, id="after_the_last_job"),
    ],
)
def test_a_shutting_down_bus_abandons_gathering_without_registering_the_batch(
    tmp_path: Path, start_stopping: Callable[[TaskTestGatherer, RecordingBus], None]
):
    """Gathering runs in a thread the bus cannot interrupt, so it has to give up on its own.

    Registering what it managed to gather would be worse than registering nothing: the batch would
    read as finished while holding a fraction of its jobs, and a run that never completed could then
    report as done.
    """
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")

    gatherer = _make_gatherer(tmp_path)
    bus = RecordingBus()
    gatherer.bus = bus  # type: ignore[assignment]
    start_stopping(gatherer, bus)

    gatherer.process_message(
        _batch_finished(
            artifacts, batch_jobs=[_batch_job_result(make_job("j1"), _workflow_job("j1", "success"), job_dir)]
        )
    )

    assert drain_queue(bus.queue) == []
    assert _registry(gatherer) == []
    # Still planned, so nothing downstream can read the batch as one that finished.
    assert gatherer._progress_by_batch["batch-1"].state is ExecutionState.PLANNED


def test_happy_path_organizes_artifacts_and_emits_update(tmp_path: Path):
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts, batch_jobs=[_batch_job_result(make_job("j1"), _workflow_job("j1", "success"), job_dir)]
        )
    )

    messages = drain_queue(gatherer.bus.queue)
    assert len(messages) == 1
    update = messages[0]
    assert isinstance(update, UpdatePRComment)
    assert update.revision == 1
    assert update.progress.done is True
    [status] = _registry(gatherer)
    assert status.id == 100
    assert status.success_count == 1
    assert status.failed_count == 0
    assert status.skipped_count == 0
    assert len(status.results) == 1

    # Organized filenames are prefixed by the job's artifact identity (target_environment_platform).
    assert (tmp_path / "out" / "coverage" / "ntp_py3.13_linux.xml").is_file()
    assert (tmp_path / "out" / "test_results" / "ntp_py3.13_linux-test-unit-py3.13.xml").is_file()
    assert (tmp_path / "out" / "test_results" / "ntp_py3.13_linux-test-e2e-py3.13.xml").is_file()


def test_failure_path_records_failed_steps_and_reports(tmp_path: Path):
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1", junit=JUNIT_FAILING, e2e=False)

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts,
            status="failure",
            batch_jobs=[
                _batch_job_result(make_job("j1"), _workflow_job("j1", "failure", failed_step="Run unit tests"), job_dir)
            ],
        )
    )

    drain_queue(gatherer.bus.queue)
    [status] = _registry(gatherer)
    assert status.failed_count == 1

    result = gatherer._results_by_batch["batch-1"][0]
    assert result.status == "failure"
    assert result.integration == "ntp"
    assert result.environment == "py3.13"
    assert result.failed_steps == ["Run unit tests"]
    assert _failed_ids(result) == [FAILING_TEST_ID]


def test_full_report_keeps_passing_tests(tmp_path: Path):
    # The failing fixture holds one failing and one passing test; the registry keeps both, not just
    # the failure (dispatcher.md: full registry of everything that happened).
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1", junit=JUNIT_FAILING, e2e=False)

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts,
            status="failure",
            batch_jobs=[_batch_job_result(make_job("j1"), _workflow_job("j1", "failure"), job_dir)],
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
    jobs = [_batch_job("j1", environment="py3.12"), _batch_job("j2", target="kafka", environment="py3.13")]
    gatherer = _make_gatherer(tmp_path, {"batch-1": jobs})
    batch_jobs = [_batch_job_result(job) for job in jobs]
    gatherer.process_message(_batch_finished("", status="failure", run_id=300, batch_jobs=batch_jobs, timed_out=True))

    drain_queue(gatherer.bus.queue)
    [status] = _registry(gatherer)
    assert status.failed_count == 2
    # The timeout is the batch's, not a step of any job: no step name is invented for it.
    assert {tuple(result.failed_steps) for result in status.results} == {()}


def test_multiple_jobs_aggregate_into_one_workflow_status(tmp_path: Path):
    artifacts = tmp_path / "artifacts" / "100"
    j1_dir = _make_job_tree(artifacts, "j1", environment="py3.12", junit=JUNIT_PASSING)
    j2_dir = _make_job_tree(artifacts, "j2", environment="py3.13", junit=JUNIT_FAILING)

    j1 = _batch_job("j1", environment="py3.12")
    j2 = _batch_job("j2", target="kafka", environment="py3.13")
    gatherer = _make_gatherer(tmp_path, {"batch-1": [j1, j2]})
    batch_jobs = [
        _batch_job_result(j1, _workflow_job("j1", "success"), j1_dir),
        _batch_job_result(j2, _workflow_job("j2", "failure"), j2_dir),
    ]
    gatherer.process_message(_batch_finished(artifacts, status="failure", batch_jobs=batch_jobs))

    drain_queue(gatherer.bus.queue)
    [status] = _registry(gatherer)
    assert status.success_count == 1
    assert status.failed_count == 1
    failed = [result.integration for result in status.results if result.status == "failure"]
    assert failed == ["kafka"]


def test_same_integration_different_platforms_do_not_overwrite(tmp_path: Path):
    artifacts = tmp_path / "artifacts" / "100"
    j1_dir = _make_job_tree(artifacts, "j1", e2e=False)
    j2_dir = _make_job_tree(artifacts, "j2", e2e=False)

    j1 = _batch_job("j1", platform=PlatformName.LINUX, runner="ubuntu-latest")
    j2 = _batch_job("j2", platform=PlatformName.WINDOWS, runner="windows-latest")
    gatherer = _make_gatherer(tmp_path, {"batch-1": [j1, j2]})
    batch_jobs = [
        _batch_job_result(j1, _workflow_job("j1", "success"), j1_dir),
        _batch_job_result(j2, _workflow_job("j2", "success"), j2_dir),
    ]
    gatherer.process_message(_batch_finished(artifacts, batch_jobs=batch_jobs))

    # Both jobs share target+environment but differ by platform/runner: each keeps its own file.
    coverage_dir = tmp_path / "out" / "coverage"
    assert (coverage_dir / "ntp_py3.13_linux.xml").is_file()
    assert (coverage_dir / "ntp_py3.13_windows.xml").is_file()


def test_minimum_base_package_replica_organizes_beside_its_original(tmp_path: Path):
    # The pair shares target, environment and platform, so before the variant became part of the
    # job's identity both wrote the same output files and one silently replaced the other.
    artifacts = tmp_path / "artifacts" / "100"
    original_dir = _make_job_tree(artifacts, "ntp-job", e2e=False)
    # The replica runs without `--cov`, so its bundle legitimately carries no coverage report.
    replica_dir = _make_job_tree(artifacts, "minimum-base-package-ntp-job", coverage=False, e2e=False)

    original = _batch_job("ntp (py3.13)")
    replica = make_job(
        "minimum-base-package-ntp (py3.13)",
        target="ntp",
        minimum_base_package=True,
        coverage=False,
    )
    gatherer = _make_gatherer(tmp_path, {"batch-1": [original, replica]})
    gatherer.process_message(
        _batch_finished(
            artifacts,
            batch_jobs=[
                _batch_job_result(original, _workflow_job(original.name, "success"), original_dir),
                _batch_job_result(replica, _workflow_job(replica.name, "success"), replica_dir),
            ],
        )
    )

    test_results_dir = tmp_path / "out" / "test_results"
    assert (test_results_dir / "ntp_py3.13_linux-test-unit-py3.13.xml").is_file()
    assert (test_results_dir / "minimum-base-package-ntp_py3.13_linux-test-unit-py3.13.xml").is_file()

    # The replica produces no coverage, and its absence is not an error: only the original's file
    # is published, and both jobs still report a result.
    coverage_files = sorted(path.name for path in (tmp_path / "out" / "coverage").iterdir())
    assert coverage_files == ["ntp_py3.13_linux.xml"]

    [status] = _registry(gatherer)
    assert (status.success_count, status.failed_count) == (2, 0)


def test_combined_job_unit_and_e2e_outputs_coexist(tmp_path: Path):
    # One job carries both facets (unit_tests and e2e_tests). Its bundle holds both a unit and an
    # E2E JUnit report plus coverage; the organized outputs are distinguished by filename within
    # the single artifact identity and never overwrite one another.
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "postgres-job", junit=JUNIT_PASSING, e2e=True)

    combined_job = make_job(
        "postgres (py3.13)",
        target="postgres",
        e2e_tests=True,
        agent_image="registry.datadoghq.com/agent-dev:master-py3",
    )

    gatherer = _make_gatherer(tmp_path, {"batch-1": [combined_job]})
    gatherer.process_message(
        _batch_finished(
            artifacts,
            batch_jobs=[_batch_job_result(combined_job, _workflow_job("postgres (py3.13)", "success"), job_dir)],
        )
    )

    assert (tmp_path / "out" / "coverage" / "postgres_py3.13_linux.xml").is_file()

    test_results_dir = tmp_path / "out" / "test_results"
    assert (test_results_dir / "postgres_py3.13_linux-test-unit-py3.13.xml").is_file()
    assert (test_results_dir / "postgres_py3.13_linux-test-e2e-py3.13.xml").is_file()


def test_emits_update_per_batch_done_on_last(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path, _one_job_plan("b1", "b2"))

    artifacts1 = tmp_path / "artifacts" / "100"
    j1_dir = _make_job_tree(artifacts1, "j1")
    gatherer.process_message(
        _batch_finished(
            artifacts1,
            id="b1",
            run_id=100,
            batch_jobs=[_batch_job_result(make_job("j1"), _workflow_job("j1", "success"), j1_dir)],
        )
    )

    # First of two batches: an update is emitted immediately (live updates), but not yet done.
    first = drain_queue(gatherer.bus.queue)
    assert len(first) == 1
    assert first[0].revision == 1
    assert first[0].progress.done is False
    assert {batch.run_id for batch in first[0].progress.batches if batch.run_id is not None} == {100}

    artifacts2 = tmp_path / "artifacts" / "200"
    j1_dir2 = _make_job_tree(artifacts2, "j1")
    gatherer.process_message(
        _batch_finished(
            artifacts2,
            id="b2",
            run_id=200,
            batch_jobs=[_batch_job_result(make_job("j1"), _workflow_job("j1", "success", run_id=200), j1_dir2)],
        )
    )

    # Final batch: revision 2, done, aggregating both runs.
    second = drain_queue(gatherer.bus.queue)
    assert len(second) == 1
    assert second[0].revision == 2
    assert second[0].progress.done is True
    assert {batch.run_id for batch in second[0].progress.batches} == {100, 200}
    assert {status.id for status in _registry(gatherer)} == {100, 200}


def test_multiple_failing_steps_all_collected(tmp_path: Path):
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
            artifacts, status="failure", batch_jobs=[_batch_job_result(make_job("j1"), workflow_job, job_dir)]
        )
    )

    result = gatherer._results_by_batch["batch-1"][0]
    assert result.failed_steps == ["Run unit tests", "Upload logs on failure"]


def test_per_job_status_comes_from_correlated_job(tmp_path: Path):
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
            artifacts, status="failure", batch_jobs=[_batch_job_result(make_job("j1"), workflow_job, job_dir)]
        )
    )

    result = gatherer._results_by_batch["batch-1"][0]
    assert result.status == "failure"
    assert result.failed_steps == ["Run unit tests"]


def test_missing_artifact_dir_is_skipped(tmp_path: Path):
    artifacts = tmp_path / "artifacts" / "100"

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(artifacts, batch_jobs=[_batch_job_result(make_job("j1"), _workflow_job("j1", "success"), None)])
    )

    result = gatherer._results_by_batch["batch-1"][0]
    assert result.status == "success"
    assert result.reports == ()
    assert not (tmp_path / "out").exists()


def test_malformed_junit_is_swallowed(tmp_path: Path):
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1", junit="<testsuite><testcase>", e2e=False)

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts, batch_jobs=[_batch_job_result(make_job("j1"), _workflow_job("j1", "success"), job_dir)]
        )
    )

    result = gatherer._results_by_batch["batch-1"][0]
    assert result.status == "success"
    assert result.reports == ()  # malformed junit skipped; coverage.xml is not a JUnit report


def test_missing_workflow_job_raises(tmp_path: Path):
    # Correlation is the runner's job; a job without a workflow job on a non-timed-out batch is a bug.
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")

    gatherer = _make_gatherer(tmp_path)
    with pytest.raises(ValueError, match="No workflow job correlated"):
        gatherer.process_message(
            _batch_finished(artifacts, batch_jobs=[_batch_job_result(make_job("j1"), None, job_dir)])
        )


def test_empty_batch_jobs_has_no_entry_in_the_registry(tmp_path: Path) -> None:
    # Nothing gathered, so the registry stays empty; only the aggregate can say "finished empty".
    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(_batch_finished("", batch_jobs=[]))

    assert gatherer._results_by_batch == {}
    assert _registry(gatherer) == []


def test_empty_batch_jobs_still_terminates_the_batch(tmp_path: Path) -> None:
    # Terminal, unsuccessful, and carrying the reason — and still emitting a revision.
    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(_batch_finished("", status="failure", run_id=100, batch_jobs=[]))

    update = drain_queue(gatherer.bus.queue)[0]
    assert update.revision == 1
    batch = update.progress.batches[0]
    assert batch.state == ExecutionState.FINISHED
    assert batch.status == Status.FAILURE
    assert batch.run_id == 100
    assert batch.error == ProgressError.NO_JOB_RESULTS
    # Its planned jobs are still listed, with no execution: 1 planned, 0 complete.
    assert (update.progress.total, update.progress.complete) == (1, 0)


def test_empty_batch_does_not_block_completion(tmp_path: Path) -> None:
    # A batch that reports nothing is finished, so the run as a whole can still reach done.
    artifacts = tmp_path / "artifacts" / "200"
    job_dir = _make_job_tree(artifacts, "j1")
    gatherer = _make_gatherer(tmp_path, _one_job_plan("b1", "b2"))

    gatherer.process_message(_batch_finished("", id="b1", run_id=100, batch_jobs=[]))
    assert drain_queue(gatherer.bus.queue)[0].progress.done is False

    gatherer.process_message(
        _batch_finished(
            artifacts,
            id="b2",
            run_id=200,
            batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success", run_id=200), job_dir)],
        )
    )

    final = drain_queue(gatherer.bus.queue)[0]
    assert final.progress.done is True
    assert _batch_progress(final, "b1").error == ProgressError.NO_JOB_RESULTS


def test_unplanned_batch_is_ignored(tmp_path: Path) -> None:
    # An unplanned batch_id must not be counted, inflate the revision, or reach the snapshot.
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts,
            id="unknown",
            batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), job_dir)],
        )
    )

    assert drain_queue(gatherer.bus.queue) == []
    assert gatherer._revision == 0
    assert [batch.batch_id for batch in gatherer.build_initial_update().progress.batches] == ["batch-1"]
    # Nor may it write into the output tree the planned batches publish from.
    assert not (tmp_path / "out").exists()


def test_duplicate_batch_finished_is_ignored(tmp_path: Path) -> None:
    # A duplicate BatchFinished for a batch already gathered must not re-count the batch or inflate
    # the revision (invariant 2: one revision per consumed batch).
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")
    batch = _batch_finished(
        artifacts, batch_jobs=[_batch_job_result(make_job("j1"), _workflow_job("j1", "success"), job_dir)]
    )

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(batch)
    first = drain_queue(gatherer.bus.queue)
    assert len(first) == 1
    assert first[0].revision == 1

    # Removed so the replay has to recreate it to be caught organizing artifacts a second time.
    shutil.rmtree(tmp_path / "out")

    gatherer.process_message(batch)
    assert drain_queue(gatherer.bus.queue) == []
    assert gatherer._revision == 1
    assert not (tmp_path / "out").exists()


def test_duplicate_is_detected_by_batch_id_not_message_id(tmp_path: Path) -> None:
    # A re-delivery carries the same batch under a new message id: still one batch.
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")
    job = _batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), job_dir)

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(_batch_finished(artifacts, id="msg-a", batch_id="batch-1", batch_jobs=[job]))
    gatherer.process_message(_batch_finished(artifacts, id="msg-b", batch_id="batch-1", batch_jobs=[job]))

    updates = drain_queue(gatherer.bus.queue)
    assert [update.revision for update in updates] == [1]
    assert gatherer._revision == 1
    assert len(_registry(gatherer)) == 1


def test_correlates_on_batch_id_not_message_id(tmp_path: Path):
    # The gatherer keys its registry and workflow status on the logical batch_id, independent of
    # the message id and of the GitHub run_id (execution metadata).
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")

    gatherer = _make_gatherer(tmp_path, {"batch-09": [make_job("j1")]})
    gatherer.process_message(
        _batch_finished(
            artifacts,
            id="msg-uuid-1",
            batch_id="batch-09",
            run_id=555,
            batch_jobs=[_batch_job_result(make_job("j1"), _workflow_job("j1", "success"), job_dir)],
        )
    )

    assert set(gatherer._results_by_batch) == {"batch-09"}
    drain_queue(gatherer.bus.queue)
    [status] = _registry(gatherer)
    assert status.batch_id == "batch-09"
    assert status.id == 555


def test_duplicate_correlates_on_batch_id_across_reruns(tmp_path: Path):
    # A re-run keeps the same logical batch_id but reports a new run_id; the duplicate must still
    # be ignored because correlation is on batch_id, not run_id.
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")
    jobs = [_batch_job_result(make_job("j1"), _workflow_job("j1", "success"), job_dir)]

    gatherer = _make_gatherer(tmp_path, {"batch-09": [make_job("j1")]})
    gatherer.process_message(_batch_finished(artifacts, id="msg-a", batch_id="batch-09", run_id=100, batch_jobs=jobs))
    assert len(drain_queue(gatherer.bus.queue)) == 1

    gatherer.process_message(_batch_finished(artifacts, id="msg-b", batch_id="batch-09", run_id=200, batch_jobs=jobs))
    assert drain_queue(gatherer.bus.queue) == []
    assert gatherer._revision == 1


def test_no_emission_without_batch_finished(tmp_path: Path):
    # Invariant: the gatherer's state changes only when a BatchFinished is consumed.
    gatherer = _make_gatherer(tmp_path)
    assert drain_queue(gatherer.bus.queue) == []
    assert gatherer._results_by_batch == {}
    assert gatherer._revision == 0


def test_build_update_message(tmp_path: Path):
    gatherer = _make_gatherer(tmp_path)
    message = gatherer.build_update_message("final", revision=2, done=True)
    assert isinstance(message, UpdatePRComment)
    assert message.id == "final"
    assert message.revision == 2
    # done is stamped on the snapshot, which is the message's only payload.
    assert message.progress.done is True


# ---------------------------------------------------------------------------
# Aggregate progress
# ---------------------------------------------------------------------------


def test_initial_update_is_revision_zero_over_the_whole_plan(tmp_path: Path) -> None:
    plan = {"b1": [_batch_job("j1"), _batch_job("j2", target="kafka")], "b2": [_batch_job("j3", target="redis")]}
    gatherer = _make_gatherer(tmp_path, plan)

    update = gatherer.build_initial_update()
    assert (update.id, update.revision) == (INITIAL_UPDATE_MESSAGE_ID, 0)
    assert _registry(gatherer) == []

    progress = update.progress
    assert progress.done is False
    assert [batch.batch_id for batch in progress.batches] == ["b1", "b2"]
    assert all(batch.state == ExecutionState.PLANNED for batch in progress.batches)
    assert all(
        batch.status is None and batch.run_id is None and batch.current_attempt is None for batch in progress.batches
    )
    assert [len(batch.jobs_progress) for batch in progress.batches] == [2, 1]
    assert all(job.attempts == () and job.latest is None for batch in progress.batches for job in batch.jobs_progress)
    assert (progress.total, progress.complete) == (3, 0)


def test_finished_batch_leaves_other_batches_planned(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")
    gatherer = _make_gatherer(tmp_path, _one_job_plan("b1", "b2"))

    gatherer.process_message(
        _batch_finished(
            artifacts,
            id="b1",
            run_id=100,
            batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), job_dir)],
        )
    )

    update = drain_queue(gatherer.bus.queue)[0]
    assert update.progress.done is False
    assert _batch_progress(update, "b1").state == ExecutionState.FINISHED
    assert _batch_progress(update, "b2").state == ExecutionState.PLANNED
    # The unfinished batch is planned, not complete — but it is still counted in the total.
    assert (update.progress.complete, update.progress.total) == (1, 2)


def test_progress_and_registry_agree(tmp_path: Path) -> None:
    # Both are built from the same gathered jobs in one pass, so they must agree on counts.
    artifacts = tmp_path / "artifacts" / "100"
    j1_dir = _make_job_tree(artifacts, "j1", environment="py3.12")
    j2_dir = _make_job_tree(artifacts, "j2", environment="py3.13", junit=JUNIT_FAILING)

    gatherer = _make_gatherer(tmp_path, {"batch-1": [_batch_job("j1"), _batch_job("j2", target="kafka")]})
    gatherer.process_message(
        _batch_finished(
            artifacts,
            status="failure",
            batch_jobs=[
                _batch_job_result(_batch_job("j1", environment="py3.12"), _workflow_job("j1", "success"), j1_dir),
                _batch_job_result(
                    _batch_job("j2", target="kafka", environment="py3.13"), _workflow_job("j2", "failure"), j2_dir
                ),
            ],
        )
    )

    update = drain_queue(gatherer.bus.queue)[0]
    [workflow] = _registry(gatherer)
    assert (update.progress.passed, update.progress.failed, update.progress.skipped) == (
        workflow.success_count,
        workflow.failed_count,
        workflow.skipped_count,
    )
    # The batch label is the workflow's, not a roll-up of the jobs the registry counted.
    assert _batch_progress(update, "batch-1").status == Status.FAILURE


def test_batch_status_comes_from_the_workflow_not_from_its_jobs(tmp_path: Path) -> None:
    # A workflow also runs steps no tracked job covers (setup, finalization). When one of those fails
    # the batch failed, even though every job it tracked passed.
    artifacts = tmp_path / "artifacts" / "100"
    job_dir = _make_job_tree(artifacts, "j1")

    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            artifacts,
            status="failure",
            batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), job_dir)],
        )
    )

    update = drain_queue(gatherer.bus.queue)[0]
    batch = _batch_progress(update, "batch-1")
    assert batch.status == Status.FAILURE
    assert [job.latest.status for job in batch.jobs_progress] == [Status.SUCCESS]
    # The job counters still report the job as passed: the discrepancy is the signal.
    assert (update.progress.passed, update.progress.failed) == (1, 0)


def test_unplanned_job_is_warned_about_but_left_out_of_the_totals(tmp_path: Path) -> None:
    # A job the plan never mentioned would mangle the totals, so it is logged and dropped.
    artifacts = tmp_path / "artifacts" / "100"
    planned_dir = _make_job_tree(artifacts, "j1")
    stray_dir = _make_job_tree(artifacts, "j2")
    gatherer = _make_gatherer(tmp_path)

    gatherer.process_message(
        _batch_finished(
            artifacts,
            batch_jobs=[
                _batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), planned_dir),
                _batch_job_result(_batch_job("j2", target="kafka"), _workflow_job("j2", "failure"), stray_dir),
            ],
        )
    )

    update = drain_queue(gatherer.bus.queue)[0]
    batch = _batch_progress(update, "batch-1")
    assert [job.job.name for job in batch.jobs_progress] == ["j1"]
    assert (update.progress.total, update.progress.complete) == (1, 1)
    assert (update.progress.passed, update.progress.failed) == (1, 0)


def test_timed_out_batch_is_recorded_on_the_batch(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished(
            "",
            status="failure",
            timed_out=True,
            batch_jobs=[_batch_job_result(_batch_job("j1"))],
        )
    )

    batch = _batch_progress(drain_queue(gatherer.bus.queue)[0], "batch-1")
    assert batch.status == Status.FAILURE
    assert batch.error == ProgressError.TIMED_OUT
    assert batch.jobs_progress[0].latest is not None
    # The job never reported a step, and GitHub never reported the job at all.
    assert batch.jobs_progress[0].latest.failed_steps == ()
    assert batch.jobs_progress[0].latest.conclusion is None


def test_concurrent_batches_produce_one_revision_each(tmp_path: Path) -> None:
    # Concurrent batches land on different threads: one revision each, no loss, no repeat.
    plan = {f"b{index}": [_scenario_batch_job(f"int{index}")] for index in range(1, 6)}
    gatherer = _make_gatherer(tmp_path, plan)

    messages = []
    for index in range(1, 6):
        artifacts = tmp_path / "artifacts" / str(index)
        jobs = [_scenario_job(artifacts, f"int{index}", "success", JUNIT_PASSING, run_id=index)]
        messages.append(_batch_finished(artifacts, id=f"b{index}", run_id=index, batch_jobs=jobs))

    barrier = threading.Barrier(len(messages))

    def gather(message) -> None:
        barrier.wait()
        gatherer.process_message(message)

    with ThreadPoolExecutor(max_workers=len(messages)) as pool:
        for future in [pool.submit(gather, message) for message in messages]:
            future.result()

    updates = drain_queue(gatherer.bus.queue)
    assert sorted(update.revision for update in updates) == [1, 2, 3, 4, 5]
    assert [update.progress.done for update in updates].count(True) == 1

    final = max(updates, key=lambda update: update.revision)
    assert {batch.state for batch in final.progress.batches} == {ExecutionState.FINISHED}
    assert (final.progress.passed, final.progress.complete, final.progress.total) == (5, 5, 5)


def test_missing_artifact_dir_is_recorded_as_an_attempt_error(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path)
    gatherer.process_message(
        _batch_finished("", batch_jobs=[_batch_job_result(_batch_job("j1"), _workflow_job("j1", "success"), None)])
    )

    attempt = _batch_progress(drain_queue(gatherer.bus.queue)[0], "batch-1").jobs_progress[0].latest
    assert attempt is not None
    assert attempt.error == ProgressError.NO_ARTIFACTS
    assert attempt.reports == ()


def test_second_run_appends_an_attempt_and_keeps_untouched_jobs(tmp_path: Path) -> None:
    # A failed-job rerun reports only the job it re-ran: that job gains a second attempt, the other
    # keeps its own, and the batch keeps both. (Bypasses the duplicate guard, which retries will own.)
    artifacts = tmp_path / "artifacts" / "100"
    passing = _make_job_tree(artifacts, "j1")
    failing = _make_job_tree(artifacts, "j2", junit=JUNIT_FAILING, e2e=False)
    j1, j2 = _batch_job("j1"), _batch_job("j2", target="kafka")
    gatherer = _make_gatherer(tmp_path, {"batch-1": [j1, j2]})

    gatherer.process_message(
        _batch_finished(
            artifacts,
            status="failure",
            batch_jobs=[
                _batch_job_result(j1, _workflow_job("j1", "success"), passing),
                _batch_job_result(j2, _workflow_job("j2", "failure"), failing),
            ],
        )
    )
    drain_queue(gatherer.bus.queue)

    rerun_dir = _make_job_tree(tmp_path / "artifacts" / "101", "j2")
    rerun = _batch_finished(
        artifacts,
        id="msg-2",
        batch_id="batch-1",
        run_id=101,
        batch_jobs=[_batch_job_result(j2, _workflow_job("j2", "success"), rerun_dir)],
    )
    gatherer._progress_by_batch["batch-1"] = gatherer._finished_batch_progress(
        gatherer._progress_by_batch["batch-1"], rerun, [gatherer._gather_job(rerun.batch_jobs[0], rerun)]
    )

    batch = gatherer._progress_by_batch["batch-1"]
    assert batch.batch_id == "batch-1"
    by_name = {job.job.name: job for job in batch.jobs_progress}
    assert sorted(by_name) == ["j1", "j2"]
    assert by_name["j1"].retry_count == 0
    assert by_name["j2"].retry_count == 1
    assert [attempt.attempt for attempt in by_name["j2"].attempts] == [1, 2]
    assert [attempt.status for attempt in by_name["j2"].attempts] == [Status.FAILURE, Status.SUCCESS]
    # Only the latest attempt counts, so the batch reads as passed and the totals do not double.
    assert batch.status == Status.SUCCESS
    assert batch.current_attempt == 2


# ---------------------------------------------------------------------------
# dispatcher.md scenario: 12 jobs, 3 batches of 4
# ---------------------------------------------------------------------------


def _scenario_batch_job(
    target: str, platform: PlatformName = PlatformName.LINUX, runner: str = "ubuntu-latest"
) -> BatchJob:
    return _batch_job(target, target=target, environment="py3.12", platform=platform, runner=runner)


def _scenario_job(
    artifacts: Path,
    target: str,
    conclusion: str,
    junit: str | None,
    *,
    run_id: int,
    platform: PlatformName = PlatformName.LINUX,
    runner_labels: tuple[str, ...] = ("ubuntu-latest",),
    failed_step: str | None = None,
) -> BatchJobResult:
    job = _scenario_batch_job(target, platform, runner_labels[0])
    job_dir = _make_job_tree(artifacts, target, environment="py3.12", junit=junit, e2e=False)
    workflow_job = _workflow_job(target, conclusion, failed_step=failed_step, run_id=run_id)
    return _batch_job_result(job, workflow_job, job_dir)


def _scenario_plan() -> dict[str, list[BatchJob]]:
    """The plan the dispatcher builds before the event bus starts: 12 jobs across 3 batches of 4."""
    return {
        "b1": [
            _scenario_batch_job("postgres"),
            _scenario_batch_job("redis"),
            _scenario_batch_job("ntp", PlatformName.WINDOWS, "windows-latest"),
            _scenario_batch_job("kafka"),
        ],
        "b2": [_scenario_batch_job(target) for target in ("disk", "snmp", "http_check", "mysql")],
        "b3": [_scenario_batch_job(target) for target in ("nginx", "kubelet", "vault", "consul")],
    }


def test_dispatcher_scenario_three_batches(tmp_path: Path) -> None:
    gatherer = _make_gatherer(tmp_path, _scenario_plan())

    # Batch-01 (steps 10-11): 4 jobs pass.
    a1 = tmp_path / "artifacts" / "1"
    batch_01 = [
        _scenario_job(a1, "postgres", "success", JUNIT_PASSING, run_id=1),
        _scenario_job(a1, "redis", "success", JUNIT_PASSING, run_id=1),
        _scenario_job(
            a1,
            "ntp",
            "success",
            JUNIT_PASSING,
            run_id=1,
            platform=PlatformName.WINDOWS,
            runner_labels=("windows-latest",),
        ),
        _scenario_job(a1, "kafka", "success", JUNIT_PASSING, run_id=1),
    ]
    gatherer.process_message(_batch_finished(a1, id="b1", run_id=1, batch_jobs=batch_01))
    rev1 = drain_queue(gatherer.bus.queue)
    assert len(rev1) == 1
    assert (rev1[0].revision, rev1[0].progress.done) == (1, False)
    assert _totals(rev1[0]) == (4, 0, 0, 4)

    # Batch-02 (steps 13-14): 3 pass + 1 fail (mysql py3.12 linux).
    a2 = tmp_path / "artifacts" / "2"
    batch_02 = [
        _scenario_job(a2, "disk", "success", JUNIT_PASSING, run_id=2),
        _scenario_job(a2, "snmp", "success", JUNIT_PASSING, run_id=2),
        _scenario_job(a2, "http_check", "success", JUNIT_PASSING, run_id=2),
        _scenario_job(a2, "mysql", "failure", JUNIT_FAILING, run_id=2, failed_step="Run unit tests"),
    ]
    gatherer.process_message(_batch_finished(a2, id="b2", status="failure", run_id=2, batch_jobs=batch_02))
    rev2 = drain_queue(gatherer.bus.queue)
    assert len(rev2) == 1
    assert (rev2[0].revision, rev2[0].progress.done) == (2, False)
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
    rev3 = drain_queue(gatherer.bus.queue)
    assert len(rev3) == 1
    final = rev3[0]
    assert (final.revision, final.progress.done) == (3, True)
    assert _totals(final) == (10, 1, 1, 12)

    # The gatherer's registry holds every batch with its id, URL, and the full per-job results.
    registry = _registry(gatherer)
    assert {workflow.id for workflow in registry} == {1, 2, 3}
    assert {workflow.batch_id for workflow in registry} == {"b1", "b2", "b3"}
    assert all(workflow.url for workflow in registry)
    assert sum(len(workflow.results) for workflow in registry) == 12

    # Batch-level labels for the "Batch-0X : passed/failed" comment line (b3 is success: 3 pass + 1 skip).
    labels = {workflow.batch_id: workflow.status for workflow in registry}
    assert labels == {"b1": "success", "b2": "failure", "b3": "success"}

    # The failing job surfaces its failed step and failing test.
    mysql = _find_result(gatherer, "mysql")
    assert mysql.status == "failure"
    assert mysql.failed_steps == ["Run unit tests"]
    assert FAILING_TEST_ID in _failed_ids(mysql)

    # The skipped job is recorded as skipped.
    assert _find_result(gatherer, "consul").status == "skipped"

    # The same run as the published snapshot, which is what the run reporter renders: 12 planned jobs,
    # all complete, with per-batch labels and links matching the registry exactly.
    progress = final.progress
    assert progress.done is True
    assert (progress.passed, progress.failed, progress.skipped) == (10, 1, 1)
    assert (progress.complete, progress.total) == (12, 12)
    assert [batch.batch_id for batch in progress.batches] == ["b1", "b2", "b3"]
    assert {batch.state for batch in progress.batches} == {ExecutionState.FINISHED}
    assert {batch.batch_id: batch.status for batch in progress.batches} == {
        "b1": Status.SUCCESS,
        "b2": Status.FAILURE,
        "b3": Status.SUCCESS,
    }
    assert {batch.run_id for batch in progress.batches} == {1, 2, 3}
    assert all(batch.workflow_url for batch in progress.batches)

    # No retries have run, so every job has exactly one execution and no retry state is reported.
    all_jobs = [job for batch in progress.batches for job in batch.jobs_progress]
    assert all(job.retry_count == 0 for job in all_jobs)
    assert all(batch.retrying_jobs == () and batch.retries_remaining == 0 for batch in progress.batches)

    # The failing job's attempt carries its conclusion, failed step, job link, and failing test.
    mysql_attempt = next(job.latest for job in all_jobs if job.job.target == "mysql")
    assert mysql_attempt is not None
    assert mysql_attempt.status == Status.FAILURE
    assert mysql_attempt.conclusion == "failure"
    assert mysql_attempt.failed_steps == ("Run unit tests",)
    assert mysql_attempt.job_id == 1
    assert [case.identifier for case in mysql_attempt.failed_tests] == [FAILING_TEST_ID]


def test_dispatcher_scenario_revisions_are_monotonic(tmp_path: Path):
    # Each consumed BatchFinished yields exactly one revision, strictly increasing (invariant #2).
    gatherer = _make_gatherer(tmp_path, {f"b{index}": [_scenario_batch_job(f"int{index}")] for index in (1, 2, 3)})
    revisions: list[int] = []
    for index in (1, 2, 3):
        artifacts = tmp_path / "artifacts" / str(index)
        jobs = [_scenario_job(artifacts, f"int{index}", "success", JUNIT_PASSING, run_id=index)]
        gatherer.process_message(_batch_finished(artifacts, id=f"b{index}", run_id=index, batch_jobs=jobs))
        emitted = drain_queue(gatherer.bus.queue)
        assert len(emitted) == 1
        revisions.append(emitted[0].revision)

    assert revisions == [1, 2, 3]


# ---------------------------------------------------------------------------
# Gatherer -> run reporter, over a real event bus
# ---------------------------------------------------------------------------


class _DispatcherBus(EventBusOrchestrator):
    """Minimal concrete orchestrator, so the two processors are wired the way production wires them."""

    async def on_initialize(self) -> None:
        pass

    async def on_finalize(self, exception: Exception | None) -> None:
        pass

    async def on_message_received(self, message: BaseMessage) -> None:
        pass


def test_gatherer_updates_the_pr_comment_through_the_event_bus(tmp_path: Path):
    """The contract between the two processors, not each half in isolation.

    The gatherer emits ``UpdatePRComment`` and the reporter consumes it: one comment created for the
    initial plan, then edited once per finished batch, never regressing.
    """
    plan = _scenario_plan()
    gatherer = TaskTestGatherer("gatherer", output_base_path=tmp_path / "out", batches=_scenario_batches(plan))
    client = FakeAsyncGitHubClient()
    reporter = TaskRunReporter(
        "run-reporter",
        client,
        RunReporterOptions(owner="DataDog", repo="integrations-core", pr_number=42),
    )

    bus = _DispatcherBus(logging.getLogger("test-bus"), max_timeout=30, grace_period=0.2)
    bus.register_processor(gatherer, [BatchFinished])
    bus.register_processor(reporter, [UpdatePRComment])

    bus.submit_message(gatherer.build_initial_update())
    for index, (batch_id, jobs) in enumerate(plan.items(), start=1):
        artifacts = tmp_path / "artifacts" / batch_id
        results = [_scenario_job(artifacts, job.target, "success", JUNIT_PASSING, run_id=index) for job in jobs]
        bus.submit_message(_batch_finished(artifacts, id=batch_id, run_id=index, batch_jobs=results))

    bus.run()

    # One comment, created once and edited for each of the three batches.
    assert len(client.calls_to("create_issue_comment")) == 1
    assert len(client.calls_to("update_issue_comment")) == 3

    bodies = [client.calls_to("create_issue_comment")[0].kwargs["body"]]
    bodies += [call.kwargs["body"] for call in client.calls_to("update_issue_comment")]

    # The comment only ever moves forward: each write reports at least as many finished jobs as the
    # one before it. The revision itself is not rendered, so the counts are what proves the ordering.
    completed = [jobs_reported(body) for body in bodies]
    assert completed == sorted(completed)

    assert completed[0] == 0
    assert "in progress" in bodies[0]
    assert "**12/12 jobs**" in bodies[-1]
    assert "## ✅ Dispatcher tests · passed" in bodies[-1]
    assert "Dispatcher finished" in bodies[-1]


def _scenario_batches(plan: dict[str, list[BatchJob]]) -> list[TestBatch]:
    return [_test_batch(batch_id, jobs) for batch_id, jobs in plan.items()]
