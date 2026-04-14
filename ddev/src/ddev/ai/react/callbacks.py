# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Protocol

from ddev.ai.agent.types import AgentResponse, ToolCall
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult


class OnAgentResponseCallback(Protocol):
    """Called after every agent.send() returns, including the first."""

    async def __call__(self, response: AgentResponse, iteration: int) -> None: ...


class OnToolCallCallback(Protocol):
    """Called once per (tool_call, result) pair after all tools in a batch execute."""

    async def __call__(self, tool_call: ToolCall, result: ToolResult, iteration: int) -> None: ...


class OnCompleteCallback(Protocol):
    """Called when the loop exits cleanly."""

    async def __call__(self, result: ReActResult) -> None: ...


class OnErrorCallback(Protocol):
    """Called when the loop aborts. The exception is always re-raised after this returns."""

    async def __call__(self, error: BaseException) -> None: ...


class OnBeforeCompactCallback(Protocol):
    """Called immediately before the agent's history is compacted."""

    async def __call__(self) -> None: ...


class OnAfterCompactCallback(Protocol):
    """Called immediately after the agent's history has been compacted."""

    async def __call__(self) -> None: ...


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
        self._on_before_compact: list[OnBeforeCompactCallback] = []
        self._on_after_compact: list[OnAfterCompactCallback] = []

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

    def on_before_compact(self, func: OnBeforeCompactCallback) -> OnBeforeCompactCallback:
        """Register a handler fired just before compaction runs."""
        self._on_before_compact.append(func)
        return func

    def on_after_compact(self, func: OnAfterCompactCallback) -> OnAfterCompactCallback:
        """Register a handler fired just after compaction completes."""
        self._on_after_compact.append(func)
        return func

    async def fire_agent_response(self, response: AgentResponse, iteration: int) -> None:
        for handler in self._on_agent_response:
            try:
                await handler(response, iteration)
            except Exception:
                pass  # we will see in the future what to do with this

    async def fire_tool_call(self, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        for handler in self._on_tool_call:
            try:
                await handler(tool_call, result, iteration)
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
        for handler in self._on_before_compact:
            try:
                await handler()
            except Exception:
                pass

    async def fire_after_compact(self) -> None:
        for handler in self._on_after_compact:
            try:
                await handler()
            except Exception:
                pass
