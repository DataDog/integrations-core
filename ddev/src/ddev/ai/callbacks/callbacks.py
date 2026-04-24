# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.agent.types import AgentResponse, ToolCall
from ddev.ai.callbacks._dispatch import dispatch
from ddev.ai.callbacks.protocols.phase import OnPhaseStartCallback
from ddev.ai.callbacks.protocols.react import (
    AfterCompactCallback,
    BeforeCompactCallback,
    OnAgentResponseCallback,
    OnBeforeAgentSendCallback,
    OnCompleteCallback,
    OnErrorCallback,
    OnToolCallCallback,
)
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult


class Callbacks:
    """Aggregated observer hub for all framework lifecycle events.

    Consumers register handlers via on_* decorators and fire events via
    fire_*. Each layer calls only the events it owns; this class is a
    neutral aggregation point, not itself a layer.

    Usage::

        cb = Callbacks()

        @cb.on_complete
        async def log_done(result: ReActResult) -> None:
            print(f"Done in {result.iterations} iterations")
    """

    def __init__(self) -> None:
        # --- ReAct events ---
        self._on_agent_response: list[OnAgentResponseCallback] = []
        self._on_tool_call: list[OnToolCallCallback] = []
        self._on_complete: list[OnCompleteCallback] = []
        self._on_error: list[OnErrorCallback] = []
        self._before_compact: list[BeforeCompactCallback] = []
        self._after_compact: list[AfterCompactCallback] = []
        self._on_before_agent_send: list[OnBeforeAgentSendCallback] = []
        # --- Phase events ---
        self._on_phase_start: list[OnPhaseStartCallback] = []

    # --- ReAct events ---

    def on_agent_response(self, func: OnAgentResponseCallback) -> OnAgentResponseCallback:
        """Register a handler fired after every agent response."""
        self._on_agent_response.append(func)
        return func

    async def fire_agent_response(self, response: AgentResponse, iteration: int) -> None:
        await dispatch(self._on_agent_response, response, iteration)

    def on_tool_call(self, func: OnToolCallCallback) -> OnToolCallCallback:
        """Register a handler fired after each tool in a batch executes."""
        self._on_tool_call.append(func)
        return func

    async def fire_tool_call(self, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        await dispatch(self._on_tool_call, tool_call, result, iteration)

    def on_complete(self, func: OnCompleteCallback) -> OnCompleteCallback:
        """Register a handler fired when the loop exits cleanly."""
        self._on_complete.append(func)
        return func

    async def fire_complete(self, result: ReActResult) -> None:
        await dispatch(self._on_complete, result)

    def on_error(self, func: OnErrorCallback) -> OnErrorCallback:
        """Register a handler fired when the loop aborts."""
        self._on_error.append(func)
        return func

    async def fire_error(self, error: BaseException) -> None:
        await dispatch(self._on_error, error)

    def on_before_compact(self, func: BeforeCompactCallback) -> BeforeCompactCallback:
        """Register a handler fired just before compaction runs."""
        self._before_compact.append(func)
        return func

    async def fire_before_compact(self) -> None:
        await dispatch(self._before_compact)

    def on_after_compact(self, func: AfterCompactCallback) -> AfterCompactCallback:
        """Register a handler fired just after compaction completes."""
        self._after_compact.append(func)
        return func

    async def fire_after_compact(self) -> None:
        await dispatch(self._after_compact)

    def on_before_agent_send(self, func: OnBeforeAgentSendCallback) -> OnBeforeAgentSendCallback:
        """Register a handler fired right before each agent.send() request."""
        self._on_before_agent_send.append(func)
        return func

    async def fire_before_agent_send(self, iteration: int) -> None:
        await dispatch(self._on_before_agent_send, iteration)

    # --- Phase events ---

    def on_phase_start(self, func: OnPhaseStartCallback) -> OnPhaseStartCallback:
        """Register a handler fired at the start of a phase."""
        self._on_phase_start.append(func)
        return func

    async def fire_phase_start(self, phase_id: str) -> None:
        await dispatch(self._on_phase_start, phase_id)
