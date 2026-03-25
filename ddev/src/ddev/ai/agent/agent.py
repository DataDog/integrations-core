# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Final

import anthropic
from anthropic.types import MessageParam, ToolParam, ToolResultBlockParam

from ddev.ai.tools.core.registry import ToolRegistry

from .types import (
    AgentAPIError,
    AgentConnectionError,
    AgentError,
    AgentRateLimitError,
    AgentResponse,
    StopReason,
    TokenUsage,
    ToolCall,
)

MODEL: Final[str] = "claude-opus-4-6"
MAX_TOKENS: Final[int] = 8192


class AnthropicAgent:
    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        tools: ToolRegistry,
        system_prompt: str,
        name: str,
        model: str = MODEL,
        max_tokens: int = MAX_TOKENS,
    ) -> None:
        self._client = client
        self._tools = tools
        self._system_prompt = system_prompt
        self.name = name
        self._model = model
        self._max_tokens = max_tokens
        self._history: list[MessageParam] = []

    @property
    def history(self) -> list[MessageParam]:
        """Read-only snapshot of the conversation history."""
        return list(self._history)

    def reset(self) -> None:
        """Clear conversation history to start a new conversation."""
        self._history = []

    def _get_tool_definitions(self, allowed_tools: list[str] | None) -> list[ToolParam]:
        """Filter tool definitions by allowlist. None means all tools."""
        if allowed_tools is None:
            return self._tools.definitions
        allowed = set(allowed_tools)
        return [d for d in self._tools.definitions if d["name"] in allowed]

    async def send(
        self,
        content: str | list[ToolResultBlockParam],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse:
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

        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_read_input_tokens=response.usage.cache_read_input_tokens or 0,
            cache_creation_input_tokens=response.usage.cache_creation_input_tokens or 0,
        )

        agent_response = AgentResponse(
            stop_reason=stop_reason,
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage=usage,
        )

        # Save to history only after a successful response.
        self._history = [*messages, {"role": "assistant", "content": response.content}]

        return agent_response
