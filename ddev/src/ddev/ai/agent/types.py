# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass
from enum import StrEnum


class StopReason(StrEnum):
    """Maps Anthropic API stop_reason strings to a typed enum."""

    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    TOOL_USE = "tool_use"
    PAUSE_TURN = "pause_turn"
    REFUSAL = "refusal"


@dataclass(frozen=True)
class ToolCall:
    """A single tool invocation requested by the model."""

    id: str
    name: str
    input: dict[str, object]


@dataclass(frozen=True)
class TokenUsage:
    """Token accounting from a single API call."""

    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int


@dataclass(frozen=True)
class AgentResponse:
    """The complete response from a single AnthropicAgent.send() call."""

    stop_reason: StopReason
    text: str
    tool_calls: list[ToolCall]
    usage: TokenUsage


class AgentError(Exception):
    """Base class for all errors raised by AnthropicAgent."""

    pass


class AgentConnectionError(AgentError):
    """Network failure — the API was unreachable."""

    pass


class AgentRateLimitError(AgentError):
    """Rate limit hit — the request may be retried after a delay."""

    pass


class AgentAPIError(AgentError):
    """The API returned an error status code."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
