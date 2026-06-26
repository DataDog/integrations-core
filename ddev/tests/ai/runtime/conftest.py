# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any

from ddev.ai.runtime.checkpoints import (
    CheckpointStatus,
    CheckpointTokenInfo,
    FailedCheckpoint,
    SuccessCheckpoint,
)

STARTED = "2026-01-01T00:00:00+00:00"
FINISHED = "2026-01-01T00:01:00+00:00"


def make_success(**kwargs: Any) -> SuccessCheckpoint:
    return SuccessCheckpoint(
        status=CheckpointStatus.SUCCESS,
        started_at=STARTED,
        finished_at=FINISHED,
        tokens=CheckpointTokenInfo(total_input=10, total_output=20),
        memory_path="/tmp/phase_memory.md",
        **kwargs,
    )


def make_failed(**kwargs: Any) -> FailedCheckpoint:
    return FailedCheckpoint(
        status=CheckpointStatus.FAILED,
        started_at=STARTED,
        finished_at=FINISHED,
        error="something broke",
        **kwargs,
    )


def make_checkpoint(data: dict) -> SuccessCheckpoint | FailedCheckpoint:
    status = data.get("status")
    ts = "2026-01-01T00:00:00+00:00"
    match status:
        case "success":
            return SuccessCheckpoint(
                status=CheckpointStatus.SUCCESS,
                started_at=ts,
                finished_at=ts,
                tokens=CheckpointTokenInfo(total_input=0, total_output=0),
                memory_path="/tmp/mem.md",
            )
        case "failed":
            return FailedCheckpoint(
                status=CheckpointStatus.FAILED, started_at=None, finished_at=ts, error=data.get("error", "")
            )
        case _:
            raise ValueError(f"unexpected checkpoint status: {status!r}")
