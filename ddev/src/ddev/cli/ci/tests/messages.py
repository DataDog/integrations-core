# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from ddev.event_bus.orchestrator import BaseMessage

if TYPE_CHECKING:
    from ddev.utils.github_async.models import WorkflowJob

# Characters GitHub disallows in an artifact name (plus CR/LF).
ARTIFACT_NAME_DISALLOWED = re.compile(r'["\:<>|*?\\/\r\n]')
# Reserved separator between the artifact name's fields. Chosen so it never appears in a field
# value (target/environment/platform), which keeps the name reversible via a plain split.
ARTIFACT_NAME_SEPARATOR = "~"


@dataclass
class BatchJob:
    """A single job entry in a TestBatch."""

    name: str
    target: str
    runner: str
    environment: str
    platform: Literal["linux", "windows", "macos"]
    unit_tests: bool
    e2e_tests: bool

    def artifact_name(self) -> str:
        """Reversible artifact name built from the job's target, environment, and platform.

        Pure and deterministic. Each field is sanitized to GitHub's artifact-name constraints and
        joined by a reserved separator absent from the values, so the name can be split back into
        ``(target, environment, platform)``. Uniqueness within a batch relies on those three fields
        being distinct per job.
        """
        fields = (self.target, self.environment, self.platform)
        return ARTIFACT_NAME_SEPARATOR.join(ARTIFACT_NAME_DISALLOWED.sub("_", field) for field in fields)


def split_artifact_name(artifact_name: str) -> tuple[str, str, str]:
    """Reverse ``BatchJob.artifact_name`` into ``(target, environment, platform)``.

    Raises ``ValueError`` when ``artifact_name`` is not the expected three-field shape, so callers
    can skip artifacts that are not per-job test artifacts.
    """
    target, environment, platform = artifact_name.split(ARTIFACT_NAME_SEPARATOR)
    return target, environment, platform


@dataclass
class FailedCheck:
    """A single failed test check within a workflow."""

    name: str
    url: str


@dataclass
class BatchJobResult:
    """Everything known about a single job in a finished batch, correlated by the producer.

    ``artifacts_path`` is the single downloaded folder for the job (named after the job's
    ``artifact_name``); the three ``*_artifact_name`` fields are the expected per-facet file names
    inside that folder.
    """

    job: BatchJob
    workflow_job: WorkflowJob | None
    artifacts_path: str | None
    unit_artifact_name: str
    e2e_artifact_name: str
    coverage_artifact_name: str


@dataclass
class WorkflowStatus:
    """Status of a single GitHub Actions workflow run."""

    url: str
    id: int
    success_count: int | None
    failed_count: int | None
    failed_checks: list[FailedCheck]


@dataclass
class TestBatch(BaseMessage):
    """Dispatched to trigger a matrix of test jobs."""

    job_list: list[BatchJob]
    jobs_count: int
    integrations: list[str]


@dataclass
class BatchFinished(BaseMessage):
    """Emitted when a GitHub Actions test workflow has completed."""

    status: Literal["success", "failure", "skipped"]
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
