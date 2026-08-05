# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Internal status vocabulary for the ci/tests task pipeline.

GitHub's workflow-run/-job conclusions are a wide set of strings (see the models in
``ddev.utils.github_async.models``). ``Status`` is the narrow, binary vocabulary the batch
and PR-comment layers use internally, and ``conclusion_to_status`` is the single place that
collapses a GitHub conclusion into it.
"""

from __future__ import annotations

from enum import StrEnum, auto
from typing import TYPE_CHECKING

from ddev.utils.github_async.models.workflow import WorkflowJobConclusion

if TYPE_CHECKING:
    from collections.abc import Iterable


class Status(StrEnum):
    """Binary outcome of a batch, job, or test as reported internally."""

    SUCCESS = auto()
    FAILURE = auto()
    SKIPPED = auto()


def batch_status(statuses: Iterable[Status]) -> Status:
    """Collapse the statuses of a batch's jobs into the batch's own label.

    Failure wins, then success, else skipped. Callers that can distinguish "every job was skipped"
    from "no job reported anything" must handle the empty case themselves.
    """
    known = set(statuses)
    if Status.FAILURE in known:
        return Status.FAILURE
    if Status.SUCCESS in known:
        return Status.SUCCESS
    return Status.SKIPPED


def conclusion_to_status(conclusion: str | None) -> Status:
    """Map a GitHub Actions conclusion to the internal :class:`Status`.

    Note: ``None`` maps to ``Status.FAILURE`` here while a check run reports ``"neutral"``
    for the same input. The asymmetry is intentional — status consumers want a binary
    outcome, the check UI prefers an explicit ``"neutral"`` badge.
    """
    if conclusion == WorkflowJobConclusion.SUCCESS:
        return Status.SUCCESS
    if conclusion == WorkflowJobConclusion.SKIPPED:
        return Status.SKIPPED
    return Status.FAILURE
