# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the ci/tests pipeline messages."""

from __future__ import annotations

from pathlib import Path

import pytest

from ddev.cli.ci.tests.messages import (
    ARTIFACT_NAME_DISALLOWED,
    BatchJob,
    BatchJobResult,
    JobResult,
    Platform,
    UpdatePRComment,
    WorkflowStatus,
)
from ddev.cli.ci.tests.progress import DispatcherProgress
from ddev.cli.ci.tests.status import Status
from ddev.utils.github_async.models import WorkflowJob


def batch_job(
    name="job-1",
    target="ntp",
    runner="ubuntu-latest",
    environment="py3.13",
    platform=Platform.LINUX,
    unit_tests=True,
    e2e_tests=False,
) -> BatchJob:
    return BatchJob(
        name=name,
        target=target,
        runner=runner,
        environment=environment,
        platform=platform,
        unit_tests=unit_tests,
        e2e_tests=e2e_tests,
    )


def test_artifact_name_built_from_target_env_platform() -> None:
    assert batch_job().artifact_name() == "ntp_py3.13_linux"


@pytest.mark.parametrize("field", ["name", "runner", "unit_tests", "e2e_tests"])
def test_artifact_name_ignores_non_identifying_fields(field: str) -> None:
    # name / runner / unit_tests / e2e_tests are not part of the artifact name.
    changed = {"name": "other-job", "runner": "windows-latest", "unit_tests": False, "e2e_tests": True}[field]
    assert batch_job(**{field: changed}).artifact_name() == batch_job().artifact_name()


@pytest.mark.parametrize(
    ("field", "value"),
    [("target", "kafka"), ("environment", "py3.12"), ("platform", Platform.WINDOWS)],
)
def test_artifact_name_varies_with_identifying_fields(field: str, value: str) -> None:
    assert batch_job(**{field: value}).artifact_name() != batch_job().artifact_name()


def test_artifact_name_sanitizes_disallowed_characters() -> None:
    name = batch_job(target='a/b:c*d?e|f"g<h>i\\j', environment="x\r\ny").artifact_name()
    assert ARTIFACT_NAME_DISALLOWED.search(name) is None


def test_correlate_matches_jobs_and_artifacts(tmp_path: Path) -> None:
    job = batch_job("j1")
    base = job.artifact_name()
    artifact_dir = tmp_path / base
    artifact_dir.mkdir()
    workflow_job = WorkflowJob(id=1, run_id=123, name="j1", status="completed", conclusion="success")

    [result] = BatchJobResult.correlate([job], [workflow_job], {base: artifact_dir})

    assert result.job == job
    assert result.workflow_job is workflow_job
    assert result.artifact_name_path == str(artifact_dir)
    assert result.unit_artifact_name == f"unit-{base}"
    assert result.e2e_artifact_name == f"e2e-{base}"
    assert result.coverage_artifact_name == f"coverage-{base}"


def test_correlate_without_workflow_or_artifact_match() -> None:
    # A job absent from the workflow API and with no matching artifact folder still yields a
    # well-formed result whose correlated facets are None.
    job = batch_job("j1")

    [result] = BatchJobResult.correlate([job], [], {})

    assert result.job == job
    assert result.workflow_job is None
    assert result.artifact_name_path is None


def test_correlate_ignores_artifact_dir_missing_on_disk(tmp_path: Path) -> None:
    # A mapped path that does not exist on disk is not recorded.
    job = batch_job("j1")
    base = job.artifact_name()

    [result] = BatchJobResult.correlate([job], [], {base: tmp_path / base})

    assert result.artifact_name_path is None


def test_job_result_defaults() -> None:
    result = JobResult(integration="ntp", environment="py3.13", platform=Platform.LINUX, status=Status.SUCCESS)
    assert result.failed_steps == []
    assert result.reports == ()
    assert result.failed_tests == []


def _job(integration: str, status: Status) -> JobResult:
    return JobResult(integration=integration, environment="py3.13", platform=Platform.LINUX, status=status)


def _workflow(batch_id: str, run_id: int, success: int, failed: int, skipped: int, results: list) -> WorkflowStatus:
    return WorkflowStatus(
        batch_id=batch_id,
        url=f"https://example/runs/{run_id}",
        id=run_id,
        success_count=success,
        failed_count=failed,
        skipped_count=skipped,
        results=results,
    )


def _results(success: int = 0, failed: int = 0, skipped: int = 0) -> list[JobResult]:
    return (
        [_job("postgres", Status.SUCCESS)] * success
        + [_job("mysql", Status.FAILURE)] * failed
        + [_job("consul", Status.SKIPPED)] * skipped
    )


def test_workflow_status_label() -> None:
    assert _workflow("b1", 1, 2, 0, 0, _results(success=2)).status == Status.SUCCESS
    assert _workflow("b2", 2, 1, 1, 0, _results(success=1, failed=1)).status == Status.FAILURE
    assert _workflow("b3", 3, 0, 0, 2, _results(skipped=2)).status == Status.SKIPPED
    # A batch with passes and skips (no failures) reads as success.
    assert _workflow("b4", 4, 3, 0, 1, _results(success=3, skipped=1)).status == Status.SUCCESS


def test_update_pr_comment_carries_only_the_revision_and_the_snapshot() -> None:
    # Ordering metadata plus the aggregate: no second copy of the counts or the done flag.
    progress = DispatcherProgress(batches=(), done=False)
    update = UpdatePRComment(id="m1", revision=0, progress=progress)

    assert (update.id, update.revision) == ("m1", 0)
    assert update.progress is progress
    assert not hasattr(update, "workflows")
    assert not hasattr(update, "done")
