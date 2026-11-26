# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Protocol


class OnPhaseStartCallback(Protocol):
    """Called once when a phase begins executing, before any agent interaction."""

    async def __call__(self, phase_id: str) -> None: ...


class OnPhaseFinishCallback(Protocol):
    """Called once when a phase completes successfully."""

    async def __call__(self, phase_id: str) -> None: ...


class OnPhaseErrorCallback(Protocol):
    """Called once when a phase terminates with an error."""

    async def __call__(self, phase_id: str, error: BaseException) -> None: ...


class OnRunErrorCallback(Protocol):
    """Called when the orchestrator stops a run because a phase failed."""

    async def __call__(self) -> None: ...


class OnBeforeGoalCheckCallback(Protocol):
    """Called immediately before each reviewer agent run for a task with a goal."""

    async def __call__(self, phase_id: str, task_name: str, attempt: int) -> None: ...


class OnAfterGoalCheckCallback(Protocol):
    """Called after each reviewer agent run, with the parsed verdict."""

    async def __call__(self, phase_id: str, task_name: str, attempt: int, valid: bool, reason: str) -> None: ...


# ---------------------------------------------------------------------------
# CallbackSet and Callbacks
# ---------------------------------------------------------------------------


class CallbackSet:
    """Registry for phase, goal-check and run callbacks."""

    def __init__(self) -> None:
        self._on_phase_start: list[OnPhaseStartCallback] = []
        self._on_phase_finish: list[OnPhaseFinishCallback] = []
        self._on_phase_error: list[OnPhaseErrorCallback] = []
        self._on_run_error: list[OnRunErrorCallback] = []
        self._on_before_goal_check: list[OnBeforeGoalCheckCallback] = []
        self._on_after_goal_check: list[OnAfterGoalCheckCallback] = []

    async def _fire(self, handlers: list[Any], *args: Any) -> None:
        for handler in handlers:
            try:
                await handler(*args)
            except Exception:
                pass

    def on_phase_start(self, func: OnPhaseStartCallback) -> OnPhaseStartCallback:
        self._on_phase_start.append(func)
        return func

    async def fire_phase_start(self, phase_id: str) -> None:
        await self._fire(self._on_phase_start, phase_id)

    def on_phase_finish(self, func: OnPhaseFinishCallback) -> OnPhaseFinishCallback:
        self._on_phase_finish.append(func)
        return func

    async def fire_phase_finish(self, phase_id: str) -> None:
        await self._fire(self._on_phase_finish, phase_id)

    def on_phase_error(self, func: OnPhaseErrorCallback) -> OnPhaseErrorCallback:
        self._on_phase_error.append(func)
        return func

    async def fire_phase_error(self, phase_id: str, error: BaseException) -> None:
        await self._fire(self._on_phase_error, phase_id, error)

    def on_run_error(self, func: OnRunErrorCallback) -> OnRunErrorCallback:
        self._on_run_error.append(func)
        return func

    async def fire_run_error(self) -> None:
        await self._fire(self._on_run_error)

    def on_before_goal_check(self, func: OnBeforeGoalCheckCallback) -> OnBeforeGoalCheckCallback:
        self._on_before_goal_check.append(func)
        return func

    async def fire_before_goal_check(self, phase_id: str, task_name: str, attempt: int) -> None:
        await self._fire(self._on_before_goal_check, phase_id, task_name, attempt)

    def on_after_goal_check(self, func: OnAfterGoalCheckCallback) -> OnAfterGoalCheckCallback:
        self._on_after_goal_check.append(func)
        return func

    async def fire_after_goal_check(
        self, phase_id: str, task_name: str, attempt: int, valid: bool, reason: str
    ) -> None:
        await self._fire(self._on_after_goal_check, phase_id, task_name, attempt, valid, reason)


class Callbacks:
    """Container of CallbackSet instances. Dispatches each fire_* to all contained sets."""

    def __init__(self, sets: list[CallbackSet] | None = None) -> None:
        self._sets: list[CallbackSet] = sets or []

    async def fire_phase_start(self, phase_id: str) -> None:
        for s in self._sets:
            await s.fire_phase_start(phase_id)

    async def fire_phase_finish(self, phase_id: str) -> None:
        for s in self._sets:
            await s.fire_phase_finish(phase_id)

    async def fire_phase_error(self, phase_id: str, error: BaseException) -> None:
        for s in self._sets:
            await s.fire_phase_error(phase_id, error)

    async def fire_run_error(self) -> None:
        for s in self._sets:
            await s.fire_run_error()

    async def fire_before_goal_check(self, phase_id: str, task_name: str, attempt: int) -> None:
        for s in self._sets:
            await s.fire_before_goal_check(phase_id, task_name, attempt)

    async def fire_after_goal_check(
        self, phase_id: str, task_name: str, attempt: int, valid: bool, reason: str
    ) -> None:
        for s in self._sets:
            await s.fire_after_goal_check(phase_id, task_name, attempt, valid, reason)
