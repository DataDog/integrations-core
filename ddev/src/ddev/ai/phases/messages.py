# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass
from typing import Any

from ddev.event_bus.orchestrator import BaseMessage

# Module-level cache so that make_phase_complete_type("phase_1") always returns
# the same class object, regardless of how many times it is called.
# This is required for EventBusOrchestrator dispatch, which matches by type identity.
_phase_complete_types: dict[str, type["PhaseCompleteMessage"]] = {}


@dataclass
class PipelineStartMessage(BaseMessage):
    """Submitted by the orchestrator's on_initialize() to kick off root phases."""

    checkpoint_path: str
    metadata: dict[str, Any]


@dataclass
class PhaseCompleteMessage(BaseMessage):
    """Emitted by a phase on successful completion. Unique subclasses are auto-generated per phase."""

    phase_name: str
    checkpoint_path: str
    metadata: dict[str, Any]


@dataclass
class PhaseFailedMessage(BaseMessage):
    """Emitted by a phase on failure. The orchestrator must subscribe to this and raise FatalProcessingError."""

    phase_name: str
    checkpoint_path: str
    error: str


def make_phase_complete_type(phase_name: str) -> type[PhaseCompleteMessage]:
    """Return the unique PhaseCompleteMessage subclass for the given phase name.

    Always returns the same class object for the same phase_name, which is required
    so that EventBusOrchestrator subscription and message dispatch use the same type.
    """
    if phase_name not in _phase_complete_types:
        _phase_complete_types[phase_name] = type(f"{phase_name}_complete", (PhaseCompleteMessage,), {})
    return _phase_complete_types[phase_name]
