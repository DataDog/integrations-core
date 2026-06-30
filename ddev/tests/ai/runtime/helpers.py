# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any

from ddev.ai.runtime.checkpoints import (
    CheckpointAdapter,
    CheckpointStatus,
    CheckpointTokenInfo,
    FailedCheckpoint,
    PhaseCheckpoint,
    SuccessCheckpoint,
)

STARTED = "2026-01-01T00:00:00+00:00"
FINISHED = "2026-01-01T00:01:00+00:00"
DEFAULT_TOKENS = CheckpointTokenInfo(total_input=10, total_output=20)


def make_checkpoint(status: CheckpointStatus, data: dict[str, Any] | None = None) -> PhaseCheckpoint:
    """Build a checkpoint of the given status, validated through the discriminated union adapter."""
    payload = {
        "started_at": STARTED,
        "finished_at": FINISHED,
        "tokens": DEFAULT_TOKENS,
        "memory_path": "/tmp/phase_memory.md",
        "error": "something broke",
        **(data or {}),
        "status": status,
    }
    return CheckpointAdapter.validate_python(payload)


def make_success(**kwargs: Any) -> SuccessCheckpoint:
    return make_checkpoint(CheckpointStatus.SUCCESS, kwargs)


def make_failed(**kwargs: Any) -> FailedCheckpoint:
    return make_checkpoint(CheckpointStatus.FAILED, kwargs)
