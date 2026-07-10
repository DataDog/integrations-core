# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.status import Status
from ddev.event_bus.orchestrator import BaseMessage

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.utils.github_async.models import WorkflowJob


class Platform(StrEnum):
    """Operating system a test job runs on."""

    LINUX = auto()
    WINDOWS = auto()
    MACOS = auto()


# Characters GitHub disallows in an artifact name (plus CR/LF).
ARTIFACT_NAME_DISALLOWED = re.compile(r'["\:<>|*?\\/\r\n]')
# Separator between the artifact name's fields. Names are matched by reconstruction, not by
# splitting, so the separator does not need to be absent from the field values.
ARTIFACT_NAME_SEPARATOR = "_"


@dataclass
class BatchJob:
    """A single job entry in a TestBatch."""

    name: str
    target: str
    runner: str
    environment: str
    platform: Platform
    unit_tests: bool
    e2e_tests: bool

    def artifact_name(self) -> str:
        """Deterministic artifact name built from the job's target, environment, and platform.

        Pure and deterministic. Each field is sanitized to GitHub's artifact-name constraints and
        joined by the separator. Uniqueness within a batch relies on those three fields being
        distinct per job.
        """
        fields = (self.target, self.environment, self.platform)
        return ARTIFACT_NAME_SEPARATOR.join(ARTIFACT_NAME_DISALLOWED.sub("_", field) for field in fields)


@dataclass
class WorkflowResult:
    """In-memory result for a single test job within a finished batch."""

    integration: str
    environment: str
    platform: Platform
    status: Status
    failed_step: str | None = None
    failed_tests: list[str] = field(default_factory=list)


@dataclass
class BatchJobResult:
    """Everything known about a single job in a finished batch, correlated by the producer.

    ``artifact_name_path`` is the single downloaded folder for the job (named after the job's
    ``artifact_name``); the three ``*_artifact_name`` fields are the expected per-facet file names
    inside that folder.
    """

    job: BatchJob
    workflow_job: WorkflowJob | None
    artifact_name_path: str | None
    unit_artifact_name: str
    e2e_artifact_name: str
    coverage_artifact_name: str

    @staticmethod
    def correlate(
        job_list: list[BatchJob],
        jobs: list[WorkflowJob],
        artifact_dirs: dict[str, Path],
    ) -> list[BatchJobResult]:
        """Correlate each job's spec, its workflow-run result, and its artifact directory.

        The workflow-job join is by name (tolerant of misses). Each job's artifact folder is matched
        by reconstructing its name from the job's fields (``artifact_name``) and looking it up among
        the downloaded folders; the path is recorded only when it exists on disk. That single folder
        holds the three per-facet files, whose names (``unit-``/``e2e-``/``coverage-`` prefixed on
        the base name) are recorded for the gatherer. A job missing from the API or from disk still
        yields a well-formed result.
        """
        jobs_by_name = {job.name: job for job in jobs}

        results: list[BatchJobResult] = []
        for batch_job in job_list:
            base = batch_job.artifact_name()
            artifact_dir = artifact_dirs.get(base)
            artifact_name_path = str(artifact_dir) if artifact_dir is not None and artifact_dir.exists() else None
            results.append(
                BatchJobResult(
                    job=batch_job,
                    workflow_job=jobs_by_name.get(batch_job.name),
                    artifact_name_path=artifact_name_path,
                    unit_artifact_name=f"unit-{base}",
                    e2e_artifact_name=f"e2e-{base}",
                    coverage_artifact_name=f"coverage-{base}",
                )
            )
        return results


@dataclass
class WorkflowStatus:
    """Status of a single GitHub Actions workflow run."""

    url: str
    id: int
    success_count: int | None
    failed_count: int | None
    failed_checks: list[WorkflowResult]


@dataclass
class TestBatch(BaseMessage):
    """Dispatched to trigger a matrix of test jobs."""

    job_list: list[BatchJob]
    jobs_count: int
    integrations: list[str]


@dataclass
class BatchFinished(BaseMessage):
    """Emitted when a GitHub Actions test workflow has completed."""

    status: Status
    run_id: int
    workflow_url: str
    artifacts_path: str
    timed_out: bool = False
    batch_jobs: list[BatchJobResult] = field(default_factory=list)


@dataclass
class UpdatePRComment(BaseMessage):
    """Emitted to request a PR comment update."""

    done: bool
    workflows: list[WorkflowStatus]
