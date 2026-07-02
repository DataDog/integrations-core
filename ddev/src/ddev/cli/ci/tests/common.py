# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shared helpers for the ci/tests task pipeline."""

from __future__ import annotations

from typing import Literal


def conclusion_to_status(conclusion: str | None) -> Literal["success", "failure", "skipped"]:
    """Map a GitHub Actions conclusion string to a binary batch/test status.

    Note: ``None`` maps to ``"failure"`` here while a check run reports ``"neutral"``
    for the same input. The asymmetry is intentional — status consumers want a binary
    outcome, the check UI prefers an explicit ``"neutral"`` badge.
    """
    if conclusion == "success":
        return "success"
    if conclusion == "skipped":
        return "skipped"
    return "failure"
