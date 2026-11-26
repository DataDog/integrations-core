# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ddev.ai.run_events import Notice

if TYPE_CHECKING:
    from ddev.ai.agent.scope import AgentScope
    from ddev.ai.agent.types import AgentResponse, ToolCall
    from ddev.ai.react.types import ReActResult
    from ddev.ai.tools.core.types import ToolResult


@dataclass(frozen=True)
class AgentStarted(Notice):
    scope: AgentScope
    system_prompt: str
    tools: list[str]


@dataclass(frozen=True)
class AgentBeforeSend(Notice):
    scope: AgentScope
    prompt: str
    iteration: int


@dataclass(frozen=True)
class AgentResponded(Notice):
    scope: AgentScope
    response: AgentResponse
    iteration: int


@dataclass(frozen=True)
class ToolCalled(Notice):
    scope: AgentScope
    tool_call: ToolCall
    result: ToolResult
    iteration: int


@dataclass(frozen=True)
class BeforeCompact(Notice):
    scope: AgentScope


@dataclass(frozen=True)
class AfterCompact(Notice):
    scope: AgentScope


@dataclass(frozen=True)
class ContextCleared(Notice):
    scope: AgentScope


@dataclass(frozen=True)
class AgentFinished(Notice):
    scope: AgentScope
    result: ReActResult


@dataclass(frozen=True)
class AgentErrored(Notice):
    scope: AgentScope
    error: BaseException
