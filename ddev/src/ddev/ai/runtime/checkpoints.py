# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


class CheckpointReadError(Exception):
    """Raised when checkpoints.yaml exists but cannot be read or parsed."""


class CheckpointStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class CheckpointTokenInfo(BaseModel):
    total_input: int
    total_output: int


class SuccessCheckpoint(BaseModel):
    """Checkpoint written at the end of a successful phase execution."""

    model_config = ConfigDict(extra="allow")

    status: Literal[CheckpointStatus.SUCCESS]
    started_at: str
    finished_at: str
    tokens: CheckpointTokenInfo
    memory_path: str


class FailedCheckpoint(BaseModel):
    """Checkpoint written when a phase terminates with an error."""

    status: Literal[CheckpointStatus.FAILED]
    started_at: str | None
    finished_at: str
    error: str
    tokens: CheckpointTokenInfo | None = None
    goal_validations: list[dict[str, Any]] | None = None


PhaseCheckpoint = Annotated[SuccessCheckpoint | FailedCheckpoint, Field(discriminator="status")]

# TypeAdapter provides model_validate() for annotated union types that aren't BaseModel subclasses.
CheckpointAdapter: TypeAdapter[PhaseCheckpoint] = TypeAdapter(PhaseCheckpoint)

RESERVED_SUCCESS_KEYS: frozenset[str] = frozenset(SuccessCheckpoint.model_fields)


class CheckpointManager:
    """Manages checkpoints.yaml and per-phase memory files for the full pipeline."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def root(self) -> Path:
        """Directory that holds checkpoints.yaml, per-phase memory files, and any side artifacts."""
        return self._path.parent

    def _ensure_dir(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def read(self) -> dict[str, PhaseCheckpoint]:
        """Return validated checkpoints keyed by phase_id.
        Raises CheckpointReadError if any entry fails validation.
        Empty dict if file absent."""
        if not self._path.exists():
            return {}
        try:
            raw = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as e:
            raise CheckpointReadError(f"Failed to load checkpoints from {self._path}: {e}") from e

        result: dict[str, PhaseCheckpoint] = {}
        for phase_id, data in raw.items():
            try:
                result[phase_id] = CheckpointAdapter.validate_python(data)
            except ValidationError as e:
                raise CheckpointReadError(f"Checkpoint for phase {phase_id!r} in {self._path} is invalid: {e}") from e
        return result

    def write_phase_checkpoint(self, phase_id: str, data: PhaseCheckpoint) -> None:
        """Write or overwrite one phase's section in checkpoints.yaml.
        Raises CheckpointWriteError if the existing file is corrupted."""
        all_checkpoints = {pid: cp.model_dump(mode="json") for pid, cp in self.read().items()}
        all_checkpoints[phase_id] = data.model_dump(mode="json")
        self._ensure_dir()
        self._path.write_text(yaml.dump(all_checkpoints, default_flow_style=False, sort_keys=False), encoding="utf-8")

    def successful_phases(self) -> set[str]:
        """Phase ids whose last recorded checkpoint reached 'success'."""
        return {pid for pid, data in self.read().items() if data.status == CheckpointStatus.SUCCESS}

    def build_memory_prompt(self, user_additions: str | None) -> str:
        """Build the memory prompt to send to the agent at the end of a phase."""
        base_prompt = "Write a brief summary of what you accomplished in this phase."
        return f"{user_additions}\n\n{base_prompt}" if user_additions else base_prompt

    @property
    def memory_dir(self) -> Path:
        """Directory where memory files and per-phase sidecar artifacts are written."""
        return self._path.parent

    def memory_path(self, phase_id: str) -> Path:
        """Return the resolved path to a phase's memory file."""
        return (self.root / f"{phase_id}_memory.md").resolve()

    def write_memory(self, phase_id: str, text: str) -> None:
        """Write agent-authored text to this phase's memory file."""
        self._ensure_dir()
        self.memory_path(phase_id).write_text(text, encoding="utf-8")

    def memory_content(self, phase_id: str) -> str:
        """Return the contents of a phase's memory file, or a NOT FOUND placeholder."""
        path = self.memory_path(phase_id)
        return path.read_text(encoding="utf-8") if path.exists() else f"<MEMORY NOT FOUND: {phase_id}>"

    def resolve_template_variable(self, key: str) -> str:
        """Resolve a template variable. ``<phase>_memory`` keys read the matching memory file."""
        if key.endswith("_memory"):
            return self.memory_content(key.removesuffix("_memory"))
        return f"<VARIABLE UNDEFINED: {key}>"
