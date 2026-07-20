# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Protocol

from ddev.ai.agent.scope import AgentScope
from ddev.ai.agent.types import AgentResponse, ToolCall
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult

# ---------------------------------------------------------------------------
# Agent-tier protocols
# ---------------------------------------------------------------------------


class OnAgentStartCallback(Protocol):
    """Called once when an agent run begins, before the first agent.send()."""

    async def __call__(self, scope: AgentScope, system_prompt: str, tools: list[str]) -> None: ...


class OnBeforeAgentSendCallback(Protocol):
    """Called immediately before each agent.send() request is issued.

    ``prompt`` is the content sent to the agent. When the agent is fed tool
    results it is the tool-results sentinel emitted by ``ReActProcess``."""

    async def __call__(self, scope: AgentScope, prompt: str, iteration: int) -> None: ...


class OnAgentResponseCallback(Protocol):
    """Called after every agent.send() returns, including the first."""

    async def __call__(self, scope: AgentScope, response: AgentResponse, iteration: int) -> None: ...


class OnToolCallCallback(Protocol):
    """Called once per (tool_call, result) pair after all tools in a batch execute."""

    async def __call__(self, scope: AgentScope, tool_call: ToolCall, result: ToolResult, iteration: int) -> None: ...


class BeforeCompactCallback(Protocol):
    """Called immediately before the agent's history is compacted."""

    async def __call__(self, scope: AgentScope) -> None: ...


class AfterCompactCallback(Protocol):
    """Called immediately after the agent's history has been compacted."""

    async def __call__(self, scope: AgentScope) -> None: ...


class OnContextClearedCallback(Protocol):
    """Called immediately after the agent's conversation history is cleared."""

    async def __call__(self, scope: AgentScope) -> None: ...


class OnAgentFinishCallback(Protocol):
    """Called when the ReAct loop exits cleanly."""

    async def __call__(self, scope: AgentScope, result: ReActResult) -> None: ...


class OnAgentErrorCallback(Protocol):
    """Called when the ReAct loop aborts. The exception is always re-raised after this returns."""

    async def __call__(self, scope: AgentScope, error: BaseException) -> None: ...


# ---------------------------------------------------------------------------
# Phase-layer protocols
# ---------------------------------------------------------------------------


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
    """Called when the orchestrator terminates a run with an error."""

    async def __call__(self, error: BaseException, phase_id: str | None) -> None: ...


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
    """Decorator-based registry for framework lifecycle event handlers.

    Group related handlers in a single instance for semantic cohesion, then
    compose multiple instances via Callbacks():

    Usage::
        logger = CallbackSet()

        @logger.on_agent_finish
        async def log_done(scope: AgentScope, result: ReActResult) -> None:
            print(f"{scope.owner_id} done in {result.iterations} iterations")

        callbacks = Callbacks([logger])
    """

    def __init__(self) -> None:
        self._on_agent_start: list[OnAgentStartCallback] = []
        self._on_before_agent_send: list[OnBeforeAgentSendCallback] = []
        self._on_agent_response: list[OnAgentResponseCallback] = []
        self._on_tool_call: list[OnToolCallCallback] = []
        self._before_compact: list[BeforeCompactCallback] = []
        self._after_compact: list[AfterCompactCallback] = []
        self._on_context_cleared: list[OnContextClearedCallback] = []
        self._on_agent_finish: list[OnAgentFinishCallback] = []
        self._on_agent_error: list[OnAgentErrorCallback] = []
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

    def on_agent_start(self, func: OnAgentStartCallback) -> OnAgentStartCallback:
        self._on_agent_start.append(func)
        return func

    async def fire_agent_start(self, scope: AgentScope, system_prompt: str, tools: list[str]) -> None:
        await self._fire(self._on_agent_start, scope, system_prompt, tools)

    def on_before_agent_send(self, func: OnBeforeAgentSendCallback) -> OnBeforeAgentSendCallback:
        self._on_before_agent_send.append(func)
        return func

    async def fire_before_agent_send(self, scope: AgentScope, prompt: str, iteration: int) -> None:
        await self._fire(self._on_before_agent_send, scope, prompt, iteration)

    def on_agent_response(self, func: OnAgentResponseCallback) -> OnAgentResponseCallback:
        self._on_agent_response.append(func)
        return func

    async def fire_agent_response(self, scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        await self._fire(self._on_agent_response, scope, response, iteration)

    def on_tool_call(self, func: OnToolCallCallback) -> OnToolCallCallback:
        self._on_tool_call.append(func)
        return func

    async def fire_tool_call(self, scope: AgentScope, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        await self._fire(self._on_tool_call, scope, tool_call, result, iteration)

    def on_before_compact(self, func: BeforeCompactCallback) -> BeforeCompactCallback:
        self._before_compact.append(func)
        return func

    async def fire_before_compact(self, scope: AgentScope) -> None:
        await self._fire(self._before_compact, scope)

    def on_after_compact(self, func: AfterCompactCallback) -> AfterCompactCallback:
        self._after_compact.append(func)
        return func

    async def fire_after_compact(self, scope: AgentScope) -> None:
        await self._fire(self._after_compact, scope)

    def on_context_cleared(self, func: OnContextClearedCallback) -> OnContextClearedCallback:
        self._on_context_cleared.append(func)
        return func

    async def fire_context_cleared(self, scope: AgentScope) -> None:
        await self._fire(self._on_context_cleared, scope)

    def on_agent_finish(self, func: OnAgentFinishCallback) -> OnAgentFinishCallback:
        self._on_agent_finish.append(func)
        return func

    async def fire_agent_finish(self, scope: AgentScope, result: ReActResult) -> None:
        await self._fire(self._on_agent_finish, scope, result)

    def on_agent_error(self, func: OnAgentErrorCallback) -> OnAgentErrorCallback:
        self._on_agent_error.append(func)
        return func

    async def fire_agent_error(self, scope: AgentScope, error: BaseException) -> None:
        await self._fire(self._on_agent_error, scope, error)

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

    async def fire_run_error(self, error: BaseException, phase_id: str | None) -> None:
        await self._fire(self._on_run_error, error, phase_id)

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

    def with_set(self, cb_set: CallbackSet) -> "Callbacks":
        """Return a new Callbacks with ``cb_set`` appended, leaving this one untouched."""
        return Callbacks([*self._sets, cb_set])

    async def fire_agent_start(self, scope: AgentScope, system_prompt: str, tools: list[str]) -> None:
        for s in self._sets:
            await s.fire_agent_start(scope, system_prompt, tools)

    async def fire_before_agent_send(self, scope: AgentScope, prompt: str, iteration: int) -> None:
        for s in self._sets:
            await s.fire_before_agent_send(scope, prompt, iteration)

    async def fire_agent_response(self, scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        for s in self._sets:
            await s.fire_agent_response(scope, response, iteration)

    async def fire_tool_call(self, scope: AgentScope, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        for s in self._sets:
            await s.fire_tool_call(scope, tool_call, result, iteration)

    async def fire_before_compact(self, scope: AgentScope) -> None:
        for s in self._sets:
            await s.fire_before_compact(scope)

    async def fire_after_compact(self, scope: AgentScope) -> None:
        for s in self._sets:
            await s.fire_after_compact(scope)

    async def fire_context_cleared(self, scope: AgentScope) -> None:
        for s in self._sets:
            await s.fire_context_cleared(scope)

    async def fire_agent_finish(self, scope: AgentScope, result: ReActResult) -> None:
        for s in self._sets:
            await s.fire_agent_finish(scope, result)

    async def fire_agent_error(self, scope: AgentScope, error: BaseException) -> None:
        for s in self._sets:
            await s.fire_agent_error(scope, error)

    async def fire_phase_start(self, phase_id: str) -> None:
        for s in self._sets:
            await s.fire_phase_start(phase_id)

    async def fire_phase_finish(self, phase_id: str) -> None:
        for s in self._sets:
            await s.fire_phase_finish(phase_id)

    async def fire_phase_error(self, phase_id: str, error: BaseException) -> None:
        for s in self._sets:
            await s.fire_phase_error(phase_id, error)

    async def fire_run_error(self, error: BaseException, phase_id: str | None) -> None:
        for s in self._sets:
            await s.fire_run_error(error, phase_id)

    async def fire_before_goal_check(self, phase_id: str, task_name: str, attempt: int) -> None:
        for s in self._sets:
            await s.fire_before_goal_check(phase_id, task_name, attempt)

    async def fire_after_goal_check(
        self, phase_id: str, task_name: str, attempt: int, valid: bool, reason: str
    ) -> None:
        for s in self._sets:
            await s.fire_after_goal_check(phase_id, task_name, attempt, valid, reason)
