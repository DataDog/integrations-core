# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

import anthropic
from anthropic.types import MessageParam, ToolParam, ToolResultBlockParam

from ddev.ai.tools.core.registry import ToolRegistry

from .exceptions import (
    AgentAPIError,
    AgentConnectionError,
    AgentError,
    AgentRateLimitError,
)

DEFAULT_MODEL: Final[str] = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS: Final[int] = 8192  # max tokens per response
ALLOWED_TOOL_CALLERS: Final = ["code_execution_20260120"]


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
    input: dict[str, Any]


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
    context: ContextUsage


@dataclass(frozen=True)
class AgentResponse:
    """The complete response from a single AnthropicAgent.send() call.
    Adds useful metadata to the response of the Anthropic API."""

    stop_reason: StopReason
    text: str
    tool_calls: list[ToolCall]
    usage: TokenUsage


class AnthropicAgent:
    """A wrapper around the Anthropic API that provides a simple interface for interacting with agents."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        tools: ToolRegistry,
        system_prompt: str,
        name: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        programmatic_tool_calling: bool = False,
    ) -> None:
        """Initialize an AnthropicAgent.
        Args:
            client: The Anthropic client to use.
            tools: The ToolRegistry to use (might not be used in every call if allowed_tools in send() is provided)
            system_prompt: The system prompt to use.
            name: The name of the agent.
            model: The model to use.
            max_tokens: The max tokens per response.
            programmatic_tool_calling: Whether to allow programmatic tool calling.
        """

        self._client = client
        self._tools = tools
        self._system_prompt = system_prompt
        self.name = name
        self._model = model
        self._max_tokens = max_tokens
        self._programmatic_tool_calling = programmatic_tool_calling
        self._history: list[MessageParam] = []
        self._context_window: int | None = None

    @property
    def history(self) -> list[MessageParam]:
        """Read-only snapshot of the conversation history."""
        return deepcopy(self._history)

    def reset(self) -> None:
        """Clear conversation history to start a new conversation."""
        self._history = []

    async def _get_context_window(self) -> int:
        if self._context_window is None:
            info = await self._client.models.retrieve(self._model)
            self._context_window = info.max_input_tokens
        return self._context_window

    def _get_tool_definitions(self, allowed_tools: list[str] | None) -> list[ToolParam]:
        """Filter tool definitions by allowlist. None means all tools."""
        definitions = self._tools.definitions
        if allowed_tools is not None:
            allowed = set(allowed_tools)
            definitions = [d for d in definitions if d["name"] in allowed]
        if not self._programmatic_tool_calling:
            definitions = [{**d, "allowed_callers": ALLOWED_TOOL_CALLERS} for d in definitions]
        return definitions

    async def send(
        self,
        content: str | list[ToolResultBlockParam],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse:
        """Send a message to the agent and return the response.
        Args:
            content: The content to send to the agent.
            allowed_tools: The tools in the ToolRegistry to allow the agent to use.
        Returns:
            An AgentResponse object containing the response from the agent.
        """
        tool_defs = self._get_tool_definitions(allowed_tools)

        user_msg: MessageParam = {"role": "user", "content": content}
        messages = [*self._history, user_msg]

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=self._system_prompt,
                messages=messages,
                tools=tool_defs if tool_defs else anthropic.NOT_GIVEN,
            )
        except anthropic.APIConnectionError as e:
            raise AgentConnectionError(f"Connection failed: {e}") from e
        except anthropic.RateLimitError as e:
            raise AgentRateLimitError(f"Rate limit exceeded: {e}") from e
        except anthropic.APIStatusError as e:
            raise AgentAPIError(e.status_code, e.message) from e
        except anthropic.APIResponseValidationError as e:
            raise AgentError(f"Response validation failed: {e}") from e

        # stop_reason is None only in streaming responses; we use non-streaming, so None is unexpected
        if response.stop_reason is None:
            raise AgentError("Received null stop_reason from API")

        try:
            stop_reason = StopReason(response.stop_reason)
        except ValueError as e:
            raise AgentError(f"Unknown stop_reason: {response.stop_reason!r}") from e

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if isinstance(block, anthropic.types.TextBlock):
                text_parts.append(block.text)
            elif isinstance(block, anthropic.types.ToolUseBlock):
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=dict(block.input)))
        # ThinkingBlock and RedactedThinkingBlock are intentionally ignored.
        # Extended thinking support can add a `thinking: str` field to AgentResponse later.

        cache_read = response.usage.cache_read_input_tokens or 0
        cache_creation = response.usage.cache_creation_input_tokens or 0
        used_tokens = response.usage.input_tokens + cache_read + cache_creation
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_read_input_tokens=cache_read,
            cache_creation_input_tokens=cache_creation,
            context=ContextUsage(window_size=await self._get_context_window(), used_tokens=used_tokens),
        )

        agent_response = AgentResponse(
            stop_reason=stop_reason,
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            usage=usage,
        )

        # Save to history only after a successful response.
        self._history.extend([user_msg, {"role": "assistant", "content": response.content}])

        return agent_response
