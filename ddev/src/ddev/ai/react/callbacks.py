# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Protocol

from ddev.ai.agent.types import AgentResponse, ToolCall
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult


class OnAgentResponseCallback(Protocol):
    """Called after every agent.send() returns, including the first.

    name is the agent's identifier (typically the phase_id) — useful for
    labeling output when multiple agents run concurrently.
    """

    async def __call__(self, response: AgentResponse, iteration: int, name: str) -> None: ...


class OnToolCallCallback(Protocol):
    """Called once per (tool_call, result) pair after all tools in a batch execute.

    display is the tool's UI-friendly rendering of the call (see BaseTool.format_call).
    name is the agent's identifier (typically the phase_id).
    """

    async def __call__(
        self, tool_call: ToolCall, result: ToolResult, display: str, iteration: int, name: str
    ) -> None: ...


class OnCompleteCallback(Protocol):
    """Called when the loop exits cleanly."""

    async def __call__(self, result: ReActResult) -> None: ...


class OnErrorCallback(Protocol):
    """Called when the loop aborts. The exception is always re-raised after this returns."""

    async def __call__(self, error: BaseException) -> None: ...


class BeforeCompactCallback(Protocol):
    """Called immediately before the agent's history is compacted."""

    async def __call__(self) -> None: ...


class AfterCompactCallback(Protocol):
    """Called immediately after the agent's history has been compacted."""

    async def __call__(self) -> None: ...


class OnPhaseStartCallback(Protocol):
    """Called once when a phase begins executing, before any agent interaction."""

    async def __call__(self, phase_id: str) -> None: ...


class OnBeforeAgentSendCallback(Protocol):
    """Called immediately before each agent.send() request is issued.

    name is the agent's identifier (typically the phase_id).
    """

    async def __call__(self, iteration: int, name: str) -> None: ...


class CallbackSet:
    """Decorator-based registry for ReAct lifecycle event handlers.

    Usage::

        cb = CallbackSet()

        @cb.on_complete
        async def log_done(result: ReActResult) -> None:
            print(f"Done in {result.iterations} iterations")
    """

    def __init__(self) -> None:
        self._on_agent_response: list[OnAgentResponseCallback] = []
        self._on_tool_call: list[OnToolCallCallback] = []
        self._on_complete: list[OnCompleteCallback] = []
        self._on_error: list[OnErrorCallback] = []
        self._before_compact: list[BeforeCompactCallback] = []
        self._after_compact: list[AfterCompactCallback] = []
        self._on_phase_start: list[OnPhaseStartCallback] = []
        self._on_before_agent_send: list[OnBeforeAgentSendCallback] = []

    def on_agent_response(self, func: OnAgentResponseCallback) -> OnAgentResponseCallback:
        """Register a handler fired after every agent response."""
        self._on_agent_response.append(func)
        return func

    def on_tool_call(self, func: OnToolCallCallback) -> OnToolCallCallback:
        """Register a handler fired after each tool in a batch executes."""
        self._on_tool_call.append(func)
        return func

    def on_complete(self, func: OnCompleteCallback) -> OnCompleteCallback:
        """Register a handler fired when the loop exits cleanly."""
        self._on_complete.append(func)
        return func

    def on_error(self, func: OnErrorCallback) -> OnErrorCallback:
        """Register a handler fired when the loop aborts."""
        self._on_error.append(func)
        return func

    def on_before_compact(self, func: BeforeCompactCallback) -> BeforeCompactCallback:
        """Register a handler fired just before compaction runs."""
        self._before_compact.append(func)
        return func

    def on_after_compact(self, func: AfterCompactCallback) -> AfterCompactCallback:
        """Register a handler fired just after compaction completes."""
        self._after_compact.append(func)
        return func

    def on_phase_start(self, func: OnPhaseStartCallback) -> OnPhaseStartCallback:
        """Register a handler fired at the start of a phase."""
        self._on_phase_start.append(func)
        return func

    def on_before_agent_send(self, func: OnBeforeAgentSendCallback) -> OnBeforeAgentSendCallback:
        """Register a handler fired right before each agent.send() request."""
        self._on_before_agent_send.append(func)
        return func

    async def fire_agent_response(self, response: AgentResponse, iteration: int, name: str) -> None:
        for handler in self._on_agent_response:
            try:
                await handler(response, iteration, name)
            except Exception:
                pass  # we will see in the future what to do with this

    async def fire_tool_call(
        self, tool_call: ToolCall, result: ToolResult, display: str, iteration: int, name: str
    ) -> None:
        for handler in self._on_tool_call:
            try:
                await handler(tool_call, result, display, iteration, name)
            except Exception:
                pass

    async def fire_complete(self, result: ReActResult) -> None:
        for handler in self._on_complete:
            try:
                await handler(result)
            except Exception:
                pass

    async def fire_error(self, error: BaseException) -> None:
        for handler in self._on_error:
            try:
                await handler(error)
            except Exception:
                pass

    async def fire_before_compact(self) -> None:
        for handler in self._before_compact:
            try:
                await handler()
            except Exception:
                pass

    async def fire_after_compact(self) -> None:
        for handler in self._after_compact:
            try:
                await handler()
            except Exception:
                pass

    async def fire_phase_start(self, phase_id: str) -> None:
        for handler in self._on_phase_start:
            try:
                await handler(phase_id)
            except Exception:
                pass

    async def fire_before_agent_send(self, iteration: int, name: str) -> None:
        for handler in self._on_before_agent_send:
            try:
                await handler(iteration, name)
            except Exception:
                pass
