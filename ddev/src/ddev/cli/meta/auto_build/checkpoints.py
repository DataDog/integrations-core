# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

CHECKPOINTS_DIR = ".openmetrics_ai"
CHECKPOINTS_FILE = "checkpoints.yml"


class PhaseStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class PhaseCheckpoint(BaseModel):
    phase: int
    status: PhaseStatus
    timestamp: datetime
    data: dict[str, Any]


class Checkpoints(BaseModel):
    checkpoints: list[PhaseCheckpoint]


def save_checkpoint(directory: Path, checkpoint: PhaseCheckpoint) -> None:
    checkpoint_path = directory / CHECKPOINTS_DIR / CHECKPOINTS_FILE
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict[str, Any]] = []
    if checkpoint_path.exists():
        with checkpoint_path.open() as f:
            existing = yaml.safe_load(f) or []

    existing.append(checkpoint.model_dump(mode="json"))

    with checkpoint_path.open("w") as f:
        yaml.dump(existing, f)


def load_checkpoints(directory: Path) -> Checkpoints:
    checkpoint_path = directory / CHECKPOINTS_DIR / CHECKPOINTS_FILE

    if not checkpoint_path.exists():
        return Checkpoints(checkpoints=[])

    with checkpoint_path.open() as f:
        data = yaml.safe_load(f) or []

    return Checkpoints.model_validate({"checkpoints": data})
