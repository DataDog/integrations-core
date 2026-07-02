# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the ci/tests pipeline messages."""

from __future__ import annotations

from pathlib import Path

import pytest

from ddev.cli.ci.tests.messages import ARTIFACT_NAME_DISALLOWED, BatchJob, BatchJobResult
from ddev.utils.github_async.models import WorkflowJob


def batch_job(
    name="job-1",
    target="ntp",
    runner="ubuntu-latest",
    environment="py3.13",
    platform="linux",
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
    [("target", "kafka"), ("environment", "py3.12"), ("platform", "windows")],
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
