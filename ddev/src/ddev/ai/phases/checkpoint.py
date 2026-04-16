# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any

import yaml


class CheckpointManager:
    """Manages checkpoints.yaml and per-phase memory files for the full pipeline."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> dict[str, Any]:
        """Return full checkpoint data, keyed by phase_id. Empty dict if file absent."""
        if not self._path.exists():
            return {}
        return yaml.safe_load(self._path.read_text()) or {}

    def write_phase_checkpoint(self, phase_id: str, data: dict[str, Any]) -> None:
        """Write or overwrite one phase's section in checkpoints.yaml."""
        checkpoints = self.read()
        checkpoints[phase_id] = data
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(yaml.dump(checkpoints, default_flow_style=False))

    def build_memory_prompt(self, user_additions: str | None) -> str:
        """Build the memory prompt to send to the agent at the end of a phase."""
        base_prompt = "Write a brief summary of what you accomplished in this phase."
        return f"{user_additions}\n\n{base_prompt}" if user_additions else base_prompt

    def write_memory(self, phase_id: str, text: str) -> None:
        """Write agent-authored text to this phase's memory file ({phase_id}_memory.md)."""
        memory_path = self._path.parent / f"{phase_id}_memory.md"
        memory_path.write_text(text)

    def get_memory(self, phase_id: str) -> str:
        """Return the contents of a phase's memory file, or a NOT FOUND placeholder."""
        memory_path = self._path.parent / f"{phase_id}_memory.md"
        return memory_path.read_text() if memory_path.exists() else f"<MEMORY NOT FOUND: {phase_id}>"
