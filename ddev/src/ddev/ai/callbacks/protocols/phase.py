# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Protocol


class OnPhaseStartCallback(Protocol):
    """Called once when a phase begins executing, before any agent interaction."""

    async def __call__(self, phase_id: str) -> None: ...


class OnPhaseFinishCallback(Protocol):
    """Called once when a phase finishes, after all tasks and the memory step complete."""

    async def __call__(self, phase_id: str) -> None: ...
