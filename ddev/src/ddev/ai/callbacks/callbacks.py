# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Protocol

from ddev.ai.agent.types import AgentResponse, ToolCall
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult

# ---------------------------------------------------------------------------
# ReAct-layer protocols
# ---------------------------------------------------------------------------


class OnAgentResponseCallback(Protocol):
    """Called after every agent.send() returns, including the first."""

    async def __call__(self, response: AgentResponse, iteration: int) -> None: ...


class OnToolCallCallback(Protocol):
    """Called once per (tool_call, result) pair after all tools in a batch execute."""

    async def __call__(self, tool_call: ToolCall, result: ToolResult, iteration: int) -> None: ...


class OnCompleteCallback(Protocol):
    """Called when the ReAct loop exits cleanly."""

    async def __call__(self, result: ReActResult) -> None: ...


class OnErrorCallback(Protocol):
    """Called when the ReAct loop aborts. The exception is always re-raised after this returns."""

    async def __call__(self, error: BaseException) -> None: ...


class BeforeCompactCallback(Protocol):
    """Called immediately before the agent's history is compacted."""

    async def __call__(self) -> None: ...


class AfterCompactCallback(Protocol):
    """Called immediately after the agent's history has been compacted."""

    async def __call__(self) -> None: ...


class OnBeforeAgentSendCallback(Protocol):
    """Called immediately before each agent.send() request is issued."""

    async def __call__(self, iteration: int) -> None: ...


# ---------------------------------------------------------------------------
# Phase-layer protocols
# ---------------------------------------------------------------------------


class OnPhaseStartCallback(Protocol):
    """Called once when a phase begins executing, before any agent interaction."""

    async def __call__(self, phase_id: str) -> None: ...


class OnPhaseFinishCallback(Protocol):
    """Called once when a phase completes successfully."""

    async def __call__(self, phase_id: str) -> None: ...


# ---------------------------------------------------------------------------
# CallbackSet and Callbacks
# ---------------------------------------------------------------------------


class CallbackSet:
    """Decorator-based registry for framework lifecycle event handlers.

    Group related handlers in a single instance for semantic cohesion, then
    compose multiple instances via Callbacks():

        class Logger(CallbackSet):
            def __init__(self):
                super().__init__()

                @self.on_complete
                async def log_done(result: ReActResult) -> None:
                    print(f"Done in {result.iterations} iterations")

        callbacks = Callbacks([Logger(), MetricsEmitter()])
    """

    def __init__(self) -> None:
        self._on_agent_response: list[OnAgentResponseCallback] = []
        self._on_tool_call: list[OnToolCallCallback] = []
        self._on_complete: list[OnCompleteCallback] = []
        self._on_error: list[OnErrorCallback] = []
        self._before_compact: list[BeforeCompactCallback] = []
        self._after_compact: list[AfterCompactCallback] = []
        self._on_before_agent_send: list[OnBeforeAgentSendCallback] = []
        self._on_phase_start: list[OnPhaseStartCallback] = []
        self._on_phase_finish: list[OnPhaseFinishCallback] = []

    async def _fire(self, handlers: list[Any], *args: Any) -> None:
        for handler in handlers:
            try:
                await handler(*args)
            except Exception:
                pass

    def on_agent_response(self, func: OnAgentResponseCallback) -> OnAgentResponseCallback:
        self._on_agent_response.append(func)
        return func

    async def fire_agent_response(self, response: AgentResponse, iteration: int) -> None:
        await self._fire(self._on_agent_response, response, iteration)

    def on_tool_call(self, func: OnToolCallCallback) -> OnToolCallCallback:
        self._on_tool_call.append(func)
        return func

    async def fire_tool_call(self, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        await self._fire(self._on_tool_call, tool_call, result, iteration)

    def on_complete(self, func: OnCompleteCallback) -> OnCompleteCallback:
        self._on_complete.append(func)
        return func

    async def fire_complete(self, result: ReActResult) -> None:
        await self._fire(self._on_complete, result)

    def on_error(self, func: OnErrorCallback) -> OnErrorCallback:
        self._on_error.append(func)
        return func

    async def fire_error(self, error: BaseException) -> None:
        await self._fire(self._on_error, error)

    def on_before_compact(self, func: BeforeCompactCallback) -> BeforeCompactCallback:
        self._before_compact.append(func)
        return func

    async def fire_before_compact(self) -> None:
        await self._fire(self._before_compact)

    def on_after_compact(self, func: AfterCompactCallback) -> AfterCompactCallback:
        self._after_compact.append(func)
        return func

    async def fire_after_compact(self) -> None:
        await self._fire(self._after_compact)

    def on_before_agent_send(self, func: OnBeforeAgentSendCallback) -> OnBeforeAgentSendCallback:
        self._on_before_agent_send.append(func)
        return func

    async def fire_before_agent_send(self, iteration: int) -> None:
        await self._fire(self._on_before_agent_send, iteration)

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


class Callbacks:
    """Container of CallbackSet instances. Dispatches each fire_* to all contained sets.

    Usage::

        callbacks = Callbacks([Logger(), MetricsEmitter()])
        process = ReActProcess(agent, registry, callbacks=callbacks)
    """

    def __init__(self, sets: list[CallbackSet] | None = None) -> None:
        self._sets: list[CallbackSet] = sets or []

    async def fire_agent_response(self, response: AgentResponse, iteration: int) -> None:
        for s in self._sets:
            await s.fire_agent_response(response, iteration)

    async def fire_tool_call(self, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        for s in self._sets:
            await s.fire_tool_call(tool_call, result, iteration)

    async def fire_complete(self, result: ReActResult) -> None:
        for s in self._sets:
            await s.fire_complete(result)

    async def fire_error(self, error: BaseException) -> None:
        for s in self._sets:
            await s.fire_error(error)

    async def fire_before_compact(self) -> None:
        for s in self._sets:
            await s.fire_before_compact()

    async def fire_after_compact(self) -> None:
        for s in self._sets:
            await s.fire_after_compact()

    async def fire_before_agent_send(self, iteration: int) -> None:
        for s in self._sets:
            await s.fire_before_agent_send(iteration)

    async def fire_phase_start(self, phase_id: str) -> None:
        for s in self._sets:
            await s.fire_phase_start(phase_id)

    async def fire_phase_finish(self, phase_id: str) -> None:
        for s in self._sets:
            await s.fire_phase_finish(phase_id)
