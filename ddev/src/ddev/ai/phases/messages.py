# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass
from enum import Enum, auto

from ddev.event_bus.orchestrator import BaseMessage


class TaskValidationStatus(Enum):
    """Status of a task validation attempt."""

    VALIDATING = auto()
    PASSED = auto()
    RETRYING = auto()
    FAILED = auto()


@dataclass
class PhaseTrigger(BaseMessage):
    phase_id: str | None  # None = initial pipeline start; str = the phase that just finished


@dataclass
class PhaseFailedMessage(BaseMessage):
    phase_id: str
    error: str
