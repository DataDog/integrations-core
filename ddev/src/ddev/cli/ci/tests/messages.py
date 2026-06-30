# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from ddev.event_bus.orchestrator import BaseMessage

if TYPE_CHECKING:
    from ddev.utils.github_async.models import WorkflowJob

# GitHub caps artifact names at 255 characters and disallows these characters (plus CR/LF).
ARTIFACT_NAME_MAX_LENGTH = 255
ARTIFACT_NAME_DISALLOWED = re.compile(r'["\:<>|*?\\/\r\n]')


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
        """Deterministic, collision-free artifact name derived solely from this job's frozen fields.

        Pure function: same job always yields the same name, and two distinct jobs never collide.
        A short digest of the raw fields guarantees uniqueness even when the readable prefix is
        truncated or two jobs sanitize to the same prefix.
        """
        raw_fields = (
            self.name,
            self.target,
            self.runner,
            self.environment,
            self.platform,
            str(self.unit_tests),
            str(self.e2e_tests),
        )
        digest = hashlib.sha256("\x00".join(raw_fields).encode()).hexdigest()[:12]
        readable = ARTIFACT_NAME_DISALLOWED.sub("_", "-".join(raw_fields))
        prefix = readable[: ARTIFACT_NAME_MAX_LENGTH - len(digest) - 1]
        return f"{prefix}-{digest}"


@dataclass
class FailedCheck:
    """A single failed test check within a workflow."""

    name: str
    url: str


@dataclass
class BatchJobResult:
    """Everything known about a single job in a finished batch, correlated by the producer."""

    job: BatchJob
    workflow_job: WorkflowJob | None
    artifacts_path: str | None


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
