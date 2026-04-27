# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any

import yaml


class CheckpointReadError(Exception):
    """Raised when checkpoints.yaml exists but cannot be read or parsed."""


class CheckpointManager:
    """Manages checkpoints.yaml and per-phase memory files for the full pipeline."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def _ensure_dir(self) -> None:
        if not self._path.parent.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> dict[str, Any]:
        """Return full checkpoint data, keyed by phase_id. Empty dict if file absent."""
        if not self._path.exists():
            return {}
        try:
            return yaml.safe_load(self._path.read_text()) or {}
        except (OSError, yaml.YAMLError) as e:
            raise CheckpointReadError(f"Failed to load checkpoints from {self._path}: {e}") from e

    def write_phase_checkpoint(self, phase_id: str, data: dict[str, Any]) -> None:
        """Write or overwrite one phase's section in checkpoints.yaml."""
        checkpoints = self.read()
        checkpoints[phase_id] = data
        self._ensure_dir()
        self._path.write_text(yaml.dump(checkpoints, default_flow_style=False))

    def build_memory_prompt(self, user_additions: str | None) -> str:
        """Build the memory prompt to send to the agent at the end of a phase."""
        base_prompt = "Write a brief summary of what you accomplished in this phase."
        return f"{user_additions}\n\n{base_prompt}" if user_additions else base_prompt

    def memory_path(self, phase_id: str) -> Path:
        """Return the resolved path to a phase's memory file."""
        return (self._path.parent / f"{phase_id}_memory.md").resolve()

    def write_memory(self, phase_id: str, text: str) -> None:
        """Write agent-authored text to this phase's memory file."""
        self._ensure_dir()
        self.memory_path(phase_id).write_text(text, encoding="utf-8")

    def memory_content(self, phase_id: str) -> str:
        """Return the contents of a phase's memory file, or a NOT FOUND placeholder."""
        path = self.memory_path(phase_id)
        return path.read_text(encoding="utf-8") if path.exists() else f"<MEMORY NOT FOUND: {phase_id}>"
