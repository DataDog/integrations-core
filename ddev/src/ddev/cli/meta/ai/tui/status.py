# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Execution status values used by the AI TUI."""

from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    """Finite phase/task execution states shown in the TUI."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

    @property
    def has_started(self) -> bool:
        return self is not RunStatus.PENDING
