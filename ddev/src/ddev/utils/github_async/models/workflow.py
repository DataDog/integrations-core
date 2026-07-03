# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""GitHub Actions workflow models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class WorkflowJobStatus(StrEnum):
    """The status of a workflow job.

    The `job` schema declares `status` as
    `enum: [queued, in_progress, completed, waiting, requested, pending]`.
    Reference:
    https://docs.github.com/en/rest/actions/workflow-jobs#get-a-job-for-a-workflow-run
    """

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WAITING = "waiting"
    REQUESTED = "requested"
    PENDING = "pending"


class WorkflowJobConclusion(StrEnum):
    """The conclusion of a workflow job.

    The `job` schema declares `conclusion` as a nullable
    `enum: [success, failure, neutral, cancelled, skipped, timed_out, action_required]`.
    Reference:
    https://docs.github.com/en/rest/actions/workflow-jobs#get-a-job-for-a-workflow-run
    """

    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"


class JobStepStatus(StrEnum):
    """The status of a single step within a workflow job.

    The `job` schema's `steps` items declare `status` as
    `enum: [queued, in_progress, completed]` (a narrower set than the job's own
    status). Their `conclusion` is a nullable string with no `enum`, so it stays
    a plain `str`.
    Reference:
    https://docs.github.com/en/rest/actions/workflow-jobs#get-a-job-for-a-workflow-run
    """

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class WorkflowRun(BaseModel):
    """A GitHub Actions workflow run.

    The `workflow-run` schema declares `status` and `conclusion` as plain
    nullable strings with no `enum`, so they are intentionally kept as free-form
    strings rather than modeled as a StrEnum.
    Reference:
    https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str | None = None
    status: str
    conclusion: str | None = None
    html_url: str
    created_at: str | None = None
    updated_at: str | None = None

    @property
    def is_completed(self) -> bool:
        """Whether the run has finished (``status == "completed"``)."""
        return self.status == "completed"


class WorkflowDispatchResult(BaseModel):
    """Response payload from a successful workflow dispatch."""

    model_config = ConfigDict(extra="ignore")

    workflow_run_id: int


class Artifact(BaseModel):
    """A GitHub Actions artifact."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    size_in_bytes: int | None = None
    url: str | None = None
    archive_download_url: str | None = None
    expired: bool


class ArtifactsList(BaseModel):
    """A list of artifacts with a total count."""

    model_config = ConfigDict(extra="ignore")

    total_count: int
    artifacts: list[Artifact]


class JobStep(BaseModel):
    """A single step within a GitHub Actions job.

    Field reference:
    https://docs.github.com/en/rest/actions/workflow-jobs#get-a-job-for-a-workflow-run
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    status: JobStepStatus
    conclusion: str | None = None
    number: int | None = None


class WorkflowJob(BaseModel):
    """A single job within a GitHub Actions workflow run.

    Field reference:
    https://docs.github.com/en/rest/actions/workflow-jobs#get-a-job-for-a-workflow-run
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    run_id: int
    name: str
    status: WorkflowJobStatus
    conclusion: WorkflowJobConclusion | None = None
    html_url: str | None = None
    steps: list[JobStep] = Field(default_factory=list)


class WorkflowJobsList(BaseModel):
    """A list of jobs with a total count."""

    model_config = ConfigDict(extra="ignore")

    total_count: int
    jobs: list[WorkflowJob]
