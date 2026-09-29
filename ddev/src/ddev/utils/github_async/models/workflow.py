# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""GitHub Actions workflow models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict, Field


def _elapsed_seconds(start: str | None, end: str | None) -> float | None:
    """Seconds between two API timestamps, or `None` when they are unusable.

    Zero is valid; a negative result means the timestamps cannot be trusted. Mixed
    naive/aware or unparseable values degrade to `None` rather than failing the caller.
    """
    if start is None or end is None:
        return None
    try:
        duration = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
    except (ValueError, TypeError):
        return None
    return duration if duration >= 0 else None


class WorkflowJobStatus(StrEnum):
    """The status of a workflow job.

    The `job` schema declares `status` as
    `enum: [queued, in_progress, completed, waiting, requested, pending]`.
    Reference:
    https://docs.github.com/en/rest/actions/workflow-jobs#get-a-job-for-a-workflow-run
    """

    QUEUED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    WAITING = auto()
    REQUESTED = auto()
    PENDING = auto()


class WorkflowJobConclusion(StrEnum):
    """The conclusion of a workflow job.

    The `job` schema declares `conclusion` as a nullable
    `enum: [success, failure, neutral, cancelled, skipped, timed_out, action_required]`.
    Reference:
    https://docs.github.com/en/rest/actions/workflow-jobs#get-a-job-for-a-workflow-run
    """

    SUCCESS = auto()
    FAILURE = auto()
    NEUTRAL = auto()
    CANCELLED = auto()
    SKIPPED = auto()
    TIMED_OUT = auto()
    ACTION_REQUIRED = auto()


class JobStepStatus(StrEnum):
    """The status of a step within a workflow job.

    The API returns `pending` for post-job steps, although its published schema omits it.
    Observed response:
    https://github.com/DataDog/integrations-core/actions/runs/34215910364/job/102398685006

    Reference:
    https://docs.github.com/en/rest/actions/workflow-jobs#get-a-job-for-a-workflow-run
    """

    QUEUED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    PENDING = auto()


class WorkflowRun(BaseModel):
    """A GitHub Actions workflow run.

    The `workflow-run` schema declares `status` and `conclusion` as plain
    nullable strings with no `enum`, so they are intentionally kept as free-form
    strings rather than modeled as a StrEnum. `status` is also in the schema's
    `required` list, so it is typed `str | None` with no default: the key is
    always present and only its value may be null.
    Reference:
    https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str | None = None
    status: str | None
    conclusion: str | None = None
    html_url: str
    created_at: str | None = None
    updated_at: str | None = None
    # Start of the latest attempt, reset on rerun (see the workflow-run schema linked above).
    run_started_at: str | None = None

    @property
    def is_completed(self) -> bool:
        """Whether the run has finished (``status == "completed"``)."""
        return self.status == "completed"

    @property
    def duration_seconds(self) -> float | None:
        """The run's duration, or `None` while it is unfinished or its timing is unusable.

        gh's completed-run timing convention is `updated_at - run_started_at`
        (https://github.com/cli/cli/blob/trunk/pkg/cmd/run/shared/shared.go):
        `updated_at` is only the end time once the run completed, so an
        in-progress run has no duration.
        """
        if not self.is_completed:
            return None
        return _elapsed_seconds(self.run_started_at, self.updated_at)


class WorkflowDispatchResult(BaseModel):
    """Run metadata returned by `POST /actions/workflows/{id}/dispatches` when `return_run_details=True`."""

    model_config = ConfigDict(extra="ignore")

    workflow_run_id: int
    run_url: str
    html_url: str


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

    The `job` schema lists `created_at`, `started_at` and `completed_at` in its `required`
    list. Only `completed_at` is nullable, so all three are required keys with no default,
    `created_at` and `started_at` as `str` and `completed_at` as `str | None`, the same
    pattern as `WorkflowRun.status`.
    Field reference and pinned schema (`components.schemas.job`):
    https://docs.github.com/en/rest/actions/workflow-jobs#get-a-job-for-a-workflow-run
    https://github.com/github/rest-api-description/blob/main/descriptions/api.github.com/api.github.com.2022-11-28.json
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    run_id: int
    name: str
    status: WorkflowJobStatus
    conclusion: WorkflowJobConclusion | None = None
    html_url: str | None = None
    created_at: str
    started_at: str
    completed_at: str | None
    steps: list[JobStep] = Field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        """The job's own execution time, or `None` if its timing is unusable. Queue time is excluded."""
        return _elapsed_seconds(self.started_at, self.completed_at)

    @property
    def queue_duration_seconds(self) -> float | None:
        """Seconds the job waited for a runner, or `None` if its timing is unusable."""
        return _elapsed_seconds(self.created_at, self.started_at)


class WorkflowJobsList(BaseModel):
    """A list of jobs with a total count."""

    model_config = ConfigDict(extra="ignore")

    total_count: int
    jobs: list[WorkflowJob]
