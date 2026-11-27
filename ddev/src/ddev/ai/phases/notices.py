# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass

from ddev.ai.run_events import Notice


@dataclass(frozen=True)
class PhaseStarted(Notice):
    phase_id: str


@dataclass(frozen=True)
class PhaseFinished(Notice):
    phase_id: str


@dataclass(frozen=True)
class PhaseErrored(Notice):
    phase_id: str
    error: BaseException


@dataclass(frozen=True)
class BeforeGoalCheck(Notice):
    phase_id: str
    task_name: str
    attempt: int


@dataclass(frozen=True)
class AfterGoalCheck(Notice):
    phase_id: str
    task_name: str
    attempt: int
    valid: bool
    reason: str
