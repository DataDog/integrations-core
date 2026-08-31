# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the ci/tests pipeline messages."""

from __future__ import annotations

from pathlib import Path

import pytest

from ddev.cli.ci.tests.messages import (
    ARTIFACT_NAME_DISALLOWED,
    BatchJobResult,
    WorkflowStatus,
)
from ddev.cli.ci.tests.status import Status
from ddev.utils.github_async.models import WorkflowJob
from ddev.utils.platform import PlatformName
from tests.cli.ci.tests.helpers import make_job


def test_artifact_name_built_from_target_env_platform():
    assert make_job().artifact_name() == "ntp_py3.13_linux"


@pytest.mark.parametrize("field", ["name", "runner_labels", "unit_tests", "e2e_tests"])
def test_artifact_name_ignores_non_identifying_fields(field: str):
    # The artifact identity is target + environment + platform; name/runner/facet flags are not part
    # of it (a single job carries its facets, so facets never distinguish two jobs).
    changed = {"name": "other-job", "runner_labels": ("windows-latest",), "unit_tests": False, "e2e_tests": True}[field]
    assert make_job(**{field: changed}).artifact_name() == make_job().artifact_name()


@pytest.mark.parametrize(
    ("field", "value"),
    [("target", "kafka"), ("environment", "py3.12"), ("platform", PlatformName.WINDOWS)],
)
def test_artifact_name_varies_with_identifying_fields(field, value):
    assert make_job(**{field: value}).artifact_name() != make_job().artifact_name()


def test_artifact_name_for_environmentless_job():
    # An environmentless job omits the environment segment entirely (no empty "__" gap); it stays
    # unique because such a target produces a single job per platform.
    assert make_job(environment="").artifact_name() == "ntp_linux"
    assert make_job(environment="", platform=PlatformName.WINDOWS).artifact_name() == "ntp_windows"


def test_artifact_name_sanitizes_disallowed_characters():
    name = make_job(target='a/b:c*d?e|f"g<h>i\\j', environment="x\r\ny").artifact_name()
    assert ARTIFACT_NAME_DISALLOWED.search(name) is None


def test_correlate_matches_jobs_and_artifacts(tmp_path: Path):
    job = make_job("j1")
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


def test_correlate_without_workflow_or_artifact_match():
    # A job absent from the workflow API and with no matching artifact folder still yields a
    # well-formed result whose correlated facets are None.
    job = make_job("j1")

    [result] = BatchJobResult.correlate([job], [], {})

    assert result.job == job
    assert result.workflow_job is None
    assert result.artifact_name_path is None


def test_correlate_ignores_artifact_dir_missing_on_disk(tmp_path: Path):
    # A mapped path that does not exist on disk is not recorded.
    job = make_job("j1")
    base = job.artifact_name()

    [result] = BatchJobResult.correlate([job], [], {base: tmp_path / base})

    assert result.artifact_name_path is None


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


def test_workflow_status_label():
    assert _workflow("b1", 1, 2, 0, 0, []).status == Status.SUCCESS
    assert _workflow("b2", 2, 1, 1, 0, []).status == Status.FAILURE
    assert _workflow("b3", 3, 0, 0, 2, []).status == Status.SKIPPED
    # A batch with passes and skips (no failures) reads as success.
    assert _workflow("b4", 4, 3, 0, 1, []).status == Status.SUCCESS
