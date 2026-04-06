# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any

import yaml


class CheckpointValidationError(Exception):
    """Raised when the agent's final response does not match the expected checkpoint schema."""


class CheckpointManager:
    """Reads and writes the shared checkpoints.yaml file.

    Concurrency note: write_phase is synchronous (no await), so it is effectively
    atomic within a single asyncio event loop. This assumes single-process asyncio
    execution. Thread or multi-process scenarios would require an external file lock.
    """

    def __init__(self, checkpoint_path: Path) -> None:
        self._path = checkpoint_path

    def read(self) -> dict[str, Any]:
        """Read full checkpoints file. Returns empty dict if file does not exist."""
        if not self._path.exists():
            return {}
        return yaml.safe_load(self._path.read_text()) or {}

    def write_phase(self, phase_name: str, data: dict[str, Any]) -> None:
        """Write or overwrite the section for phase_name. Creates file if needed."""
        checkpoints = self.read()
        checkpoints[phase_name] = data
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(yaml.dump(checkpoints, default_flow_style=False))

    def as_yaml_string(self) -> str:
        """Render the full checkpoint file as a string for prompt injection."""
        data = self.read()
        return yaml.dump(data, default_flow_style=False) if data else "(no checkpoints yet)"


def validate_checkpoint_output(raw: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Parse and validate agent YAML output against schema.

    Raises CheckpointValidationError if the output is not valid YAML,
    not a mapping, or is missing any keys defined in schema.
    """
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise CheckpointValidationError(f"Agent response is not valid YAML: {e}")
    if not isinstance(parsed, dict):
        raise CheckpointValidationError("Agent response must be a YAML mapping")
    missing = set(schema.keys()) - set(parsed.keys())
    if missing:
        raise CheckpointValidationError(f"Agent response missing required keys: {missing}")
    return parsed
