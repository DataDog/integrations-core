# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""GitHub Checks API models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class CheckRunStatus(StrEnum):
    """The status of a check run.

    The `check-run` schema declares `status` as
    `enum: [queued, in_progress, completed, waiting, requested, pending]`.
    Reference:
    https://docs.github.com/en/rest/checks/runs#get-a-check-run
    """

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WAITING = "waiting"
    REQUESTED = "requested"
    PENDING = "pending"


class CheckRunConclusion(StrEnum):
    """The conclusion of a check run.

    The `check-run` schema declares `conclusion` as a nullable
    `enum: [success, failure, neutral, cancelled, skipped, timed_out, action_required]`.
    Reference:
    https://docs.github.com/en/rest/checks/runs#get-a-check-run
    """

    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"


class CheckRun(BaseModel):
    """A GitHub Checks API check run.

    Field reference:
    https://docs.github.com/en/rest/checks/runs#get-a-check-run
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    status: CheckRunStatus
    conclusion: CheckRunConclusion | None
    html_url: str | None
    head_sha: str
