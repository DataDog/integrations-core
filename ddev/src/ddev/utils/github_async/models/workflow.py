# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""GitHub Actions workflow models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkflowRun(BaseModel):
    """A GitHub Actions workflow run."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str | None = None
    status: str
    conclusion: str | None = None
    html_url: str
    created_at: str | None = None
    updated_at: str | None = None


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
    """A single step within a GitHub Actions job."""

    model_config = ConfigDict(extra="ignore")

    name: str
    status: str
    conclusion: str | None = None
    number: int | None = None


class WorkflowJob(BaseModel):
    """A single job within a GitHub Actions workflow run."""

    model_config = ConfigDict(extra="ignore")

    id: int
    run_id: int
    name: str
    status: str
    conclusion: str | None = None
    html_url: str | None = None
    steps: list[JobStep] = Field(default_factory=list)


class WorkflowJobsList(BaseModel):
    """A list of jobs with a total count."""

    model_config = ConfigDict(extra="ignore")

    total_count: int
    jobs: list[WorkflowJob]
