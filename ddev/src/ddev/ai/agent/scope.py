# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AgentRole(str, Enum):
    PHASE = "phase"
    SUBAGENT = "subagent"
    GOAL_REVIEWER = "goal_reviewer"
    RUN_SUMMARY = "run_summary"


@dataclass(frozen=True)
class AgentScope:
    """Identity of a single agent within a run. Carried by every agent-tier event."""

    owner_id: str
    role: AgentRole
    phase_id: str | None

    def __post_init__(self) -> None:
        if self.role is AgentRole.RUN_SUMMARY:
            if self.phase_id is not None:
                raise ValueError("Run-summary agents cannot belong to a phase")
        elif self.phase_id is None:
            raise ValueError(f"{self.role.value} agents must belong to a phase")
