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


@dataclass(frozen=True)
class AgentScope:
    """Identity of a single agent within a run. Carried by every agent-tier event."""

    owner_id: str
    role: AgentRole
