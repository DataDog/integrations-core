# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Wire types for the agent layer: enums, dataclasses, and response shapes."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ddev.ai.tools.core.types import ToolResult


class StopReason(StrEnum):
    """Generic stop reasons for agent responses, independent of any provider."""

    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    OTHER = "other"


@dataclass(frozen=True)
class ToolCall:
    """A single tool invocation requested by the model."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class WebSearchCall:
    """A server-side web search the model performed (Anthropic native tool)."""

    query: str
    result_count: int = 0
    error: str | None = None


@dataclass(frozen=True)
class ToolResultMessage:
    """Wraps a tool result to be sent back to the agent, keyed by the originating tool call ID."""

    tool_call_id: str  # matches ToolCall.id
    result: ToolResult


@dataclass(frozen=True)
class ContextUsage:
    """Context window accounting for a single API call."""

    window_size: int
    used_tokens: int

    @property
    def context_pct(self) -> float:
        return self.used_tokens / self.window_size * 100

    @property
    def remaining_tokens(self) -> int:
        return self.window_size - self.used_tokens


@dataclass(frozen=True)
class TokenUsage:
    """Token accounting from a single API call."""

    input_tokens: int  # tokens sent to the model (system_prompt + history)
    output_tokens: int  # tokens the model generated
    cache_read_input_tokens: int  # tokens read from prompt cache
    cache_creation_input_tokens: int  # tokens written to prompt cache
    context_usage: ContextUsage | None = None  # None only for agents that don't provide context tracking
    web_search_requests: int = 0  # number of web search requests (billed separately from tokens)


@dataclass(frozen=True)
class AgentResponse:
    """The complete response from a single agent.send() call.
    Adds useful metadata to the response of the agent."""

    stop_reason: StopReason
    text: str
    tool_calls: list[ToolCall]
    usage: TokenUsage
    web_searches: list[WebSearchCall] = field(default_factory=list)
