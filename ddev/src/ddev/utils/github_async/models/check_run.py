# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""GitHub Checks API models."""

from __future__ import annotations

from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict


class CheckRunStatus(StrEnum):
    """The status of a check run.

    The `check-run` schema declares `status` as
    `enum: [queued, in_progress, completed, waiting, requested, pending]`.
    Reference:
    https://docs.github.com/en/rest/checks/runs#get-a-check-run
    """

    QUEUED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    WAITING = auto()
    REQUESTED = auto()
    PENDING = auto()


class CheckRunConclusion(StrEnum):
    """The conclusion of a check run.

    The `check-run` response schema declares `conclusion` as a nullable
    `enum: [success, failure, neutral, cancelled, skipped, timed_out, action_required]`.
    `stale` is added on top of those: it is a valid conclusion that only GitHub can
    set (present in the update-a-check-run request enum and the docs, though the
    response schema omits it), so a real response can carry it and the model must
    accept it.
    Reference:
    https://docs.github.com/en/rest/checks/runs#update-a-check-run
    """

    SUCCESS = auto()
    FAILURE = auto()
    NEUTRAL = auto()
    CANCELLED = auto()
    SKIPPED = auto()
    TIMED_OUT = auto()
    ACTION_REQUIRED = auto()
    STALE = auto()


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
