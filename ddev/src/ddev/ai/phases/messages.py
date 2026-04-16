# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass

from ddev.event_bus.orchestrator import BaseMessage


@dataclass
class StartMessage(BaseMessage):
    pass


@dataclass
class PhaseFinishedMessage(BaseMessage):
    phase_id: str


@dataclass
class PhaseFailedMessage(BaseMessage):
    phase_id: str
    error: str
