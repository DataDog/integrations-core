# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

import yaml
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from ddev.ai.config.errors import ConfigError
from ddev.ai.runtime.helpers import atomic_write_text

if TYPE_CHECKING:
    from ddev.ai.config.models import ResolvedFlow


class CheckpointReadError(Exception):
    """Raised when checkpoints.yaml exists but cannot be read or parsed."""


class CheckpointStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CheckpointTokenInfo(BaseModel):
    total_input: int
    total_output: int


class GoalValidationRecord(BaseModel):
    task: str
    attempts: int
    final_valid: bool


class SuccessCheckpoint(BaseModel):
    """Checkpoint written at the end of a successful phase execution."""

    status: Literal[CheckpointStatus.SUCCESS] = CheckpointStatus.SUCCESS
    started_at: str
    finished_at: str
    tokens: CheckpointTokenInfo
    memory_path: str
    goal_validations: list[GoalValidationRecord] | None = None
    phase_data: dict[str, Any] = {}


class FailedCheckpoint(BaseModel):
    """Checkpoint written when a phase terminates with an error."""

    status: Literal[CheckpointStatus.FAILED] = CheckpointStatus.FAILED
    started_at: str | None
    finished_at: str
    error: str
    error_type: str | None = None
    tokens: CheckpointTokenInfo
    goal_validations: list[GoalValidationRecord] | None = None


class CancelledCheckpoint(BaseModel):
    """Checkpoint written when a started phase is cancelled before completion."""

    status: Literal[CheckpointStatus.CANCELLED] = CheckpointStatus.CANCELLED
    started_at: str
    finished_at: str
    reason: str | None = None
    tokens: CheckpointTokenInfo
    goal_validations: list[GoalValidationRecord] | None = None


PhaseCheckpoint = Annotated[
    SuccessCheckpoint | FailedCheckpoint | CancelledCheckpoint,
    Field(discriminator="status"),
]

# TypeAdapter provides model_validate() for annotated union types that aren't BaseModel subclasses.
CheckpointAdapter: TypeAdapter[PhaseCheckpoint] = TypeAdapter(PhaseCheckpoint)

PHASE_MEMORY_PROMPT = """Write a detailed Markdown handoff for this phase using exactly these sections:

## What the agent was asked for
State the phase's assignment, expected outputs, and boundaries.

## What information it had from before
Record the relevant inputs, prior-phase memory, existing artifacts, and repository context available to you.

## Decisions it took
Explain the important technical or scope decisions and why they were made.

## What it did
Describe the work performed, results produced, validation completed, and any unfinished or uncertain work.

## Files it edited, created, or worked in
List every important file or directory inspected, edited, or created, and describe its role.
Explicitly say when no files were involved.

Be concrete enough that a later agent can understand the phase without access to this conversation.
Do not claim success for work that was not completed."""


class CheckpointManager:
    """Manages checkpoints.yaml and per-phase memory files for the full pipeline."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def run_dir(self) -> Path:
        """Directory containing all artifacts for this run."""
        return self._path.parent

    @property
    def root(self) -> Path:
        """Directory that holds checkpoints.yaml, per-phase memory files, and any side artifacts."""
        return self.run_dir

    @property
    def outcome_path(self) -> Path:
        """Path where the deterministic run outcome is persisted."""
        return self.run_dir / "run.yaml"

    @property
    def checkpoints_path(self) -> Path:
        """Path to the durable phase checkpoint record."""
        return self._path

    @property
    def summary_markdown_path(self) -> Path:
        """Path to the current run's generated Markdown narrative."""
        return self.run_dir / "summary.md"

    @property
    def agent_log_root(self) -> Path:
        """Directory under which per-agent logs are persisted."""
        return self.run_dir

    def read(self) -> dict[str, PhaseCheckpoint]:
        """Return validated checkpoints keyed by phase_id.
        Raises CheckpointReadError if any entry fails validation.
        Empty dict if file absent."""
        if not self._path.exists():
            return {}
        try:
            raw = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        except (OSError, UnicodeError, yaml.YAMLError) as e:
            raise CheckpointReadError(f"Failed to load checkpoints from {self._path}: {e}") from e
        if not isinstance(raw, dict):
            raise CheckpointReadError(f"Checkpoints in {self._path} must be a mapping")

        result: dict[str, PhaseCheckpoint] = {}
        for phase_id, data in raw.items():
            try:
                result[phase_id] = CheckpointAdapter.validate_python(data)
            except ValidationError as e:
                raise CheckpointReadError(f"Checkpoint for phase {phase_id!r} in {self._path} is invalid: {e}") from e
        return result

    def write_phase_checkpoint(self, phase_id: str, data: PhaseCheckpoint) -> None:
        """Write or overwrite one phase's section in checkpoints.yaml.
        Raises CheckpointReadError if the existing file is corrupted."""
        all_checkpoints = {pid: cp.model_dump(mode="json") for pid, cp in self.read().items()}
        all_checkpoints[phase_id] = data.model_dump(mode="json")
        atomic_write_text(
            self._path,
            yaml.dump(all_checkpoints, default_flow_style=False, sort_keys=False),
        )

    def successful_phases(self) -> set[str]:
        """Phase ids whose last recorded checkpoint reached 'success'."""
        return {pid for pid, data in self.read().items() if data.status == CheckpointStatus.SUCCESS}

    def build_memory_prompt(self, user_additions: str | None) -> str:
        """Build the memory prompt to send to the agent at the end of a phase."""
        return f"{user_additions}\n\n{PHASE_MEMORY_PROMPT}" if user_additions else PHASE_MEMORY_PROMPT

    def resolve_run_artifact(self, relative_path: str) -> Path:
        """Resolve a persisted relative artifact path without allowing run-directory escape."""
        path = Path(relative_path)
        if path.is_absolute():
            raise ValueError("Run artifact paths must be relative")
        resolved = (self.run_dir / path).resolve()
        if not resolved.is_relative_to(self.run_dir.resolve()):
            raise ValueError(f"Run artifact path escapes the run directory: {relative_path!r}")
        return resolved

    @property
    def memory_dir(self) -> Path:
        """Directory where memory files and per-phase sidecar artifacts are written."""
        return self.run_dir

    def memory_path(self, phase_id: str) -> Path:
        """Return the resolved path to a phase's memory file."""
        return (self.run_dir / f"{phase_id}_memory.md").resolve()

    def write_memory(self, phase_id: str, text: str) -> None:
        """Write agent-authored text to this phase's memory file."""
        atomic_write_text(self.memory_path(phase_id), text)

    def memory_content(self, phase_id: str) -> str:
        """Return the contents of a phase's memory file, or a NOT FOUND placeholder."""
        path = self.memory_path(phase_id)
        return path.read_text(encoding="utf-8") if path.exists() else f"<MEMORY NOT FOUND: {phase_id}>"

    def resolve_template_variable(self, key: str) -> str:
        """Resolve a template variable. ``<phase>_memory`` keys read the matching memory file."""
        if key.endswith("_memory"):
            return self.memory_content(key.removesuffix("_memory"))
        return f"<VARIABLE UNDEFINED: {key}>"


def resolve_resume_state(
    resolved_flow: ResolvedFlow, checkpoint_manager: CheckpointManager
) -> tuple[set[str], set[str]]:
    """Compute (completed, frontier) for resuming a flow from its checkpoints.

    ``completed`` is the dependency-closed set of phases that succeeded and whose every
    transitive dependency also succeeded. ``frontier`` is the phases that will run first
    on resume (not completed, but all their dependencies are).

    The single-pass closure relies on ``resolved_flow.flow`` being topologically sorted.
    """
    try:
        succeeded = checkpoint_manager.successful_phases()
    except CheckpointReadError as e:
        raise ConfigError(
            f"Cannot resume: checkpoints file is unreadable ({e}). Delete it and restart from scratch."
        ) from e
    completed: set[str] = set()
    frontier: set[str] = set()
    for entry in resolved_flow.flow:
        deps_done = all(dep in completed for dep in entry.dependencies)
        if entry.phase in succeeded and deps_done:
            completed.add(entry.phase)
        elif deps_done:
            frontier.add(entry.phase)
    return completed, frontier
