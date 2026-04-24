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


class BeforeCompactCallback(Protocol):
    """Called immediately before the agent's history is compacted."""

    async def __call__(self) -> None: ...


class AfterCompactCallback(Protocol):
    """Called immediately after the agent's history has been compacted."""

    async def __call__(self) -> None: ...


class OnBeforeAgentSendCallback(Protocol):
    """Called immediately before each agent.send() request is issued."""

    async def __call__(self, iteration: int) -> None: ...
