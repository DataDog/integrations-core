# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, Final, overload

import anthropic
from anthropic.types import MessageParam

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.exceptions import AgentAPIError, AgentConnectionError, AgentError, AgentRateLimitError
from ddev.ai.agent.types import AgentResponse, ContextUsage, StopReason, TokenUsage, ToolCall, ToolResultMessage
from ddev.ai.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from anthropic.types import (
        CacheControlEphemeralParam,
        TextBlockParam,
        ToolParam,
        ToolResultBlockParam,
    )

DEFAULT_MODEL: Final[str] = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS: Final[int] = 8192  # max tokens per response

# 1h TTL for the static prefix (system + tools): paid once, read for the whole session.
STATIC_CACHE_CONTROL: Final[CacheControlEphemeralParam] = {"type": "ephemeral", "ttl": "1h"}
# Default TTL (currently 5 min, but Anthropic may change it) for the sliding breakpoint
# on the last user message: re-written each turn, so a longer TTL would be wasted.
SLIDING_CACHE_CONTROL: Final[CacheControlEphemeralParam] = {"type": "ephemeral"}


class AnthropicAgent(BaseAgent[MessageParam]):
    """A wrapper around the Anthropic API that provides a simple interface for interacting with agents."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        tools: ToolRegistry,
        system_prompt: str,
        name: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        """Initialize an AnthropicAgent.
        Args:
            client: The Anthropic client to use.
            tools: The ToolRegistry to use (might not be used in every call if allowed_tools in send() is provided)
            system_prompt: The system prompt to use.
            name: The name of the agent.
            model: The model to use.
            max_tokens: The max tokens per response.
        """

        super().__init__(name=name, system_prompt=system_prompt, tools=tools)
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._context_window: int | None = None

    async def _get_context_window(self) -> int:
        if self._context_window is None:
            try:
                info = await self._client.models.retrieve(self._model)
            except anthropic.APIConnectionError as e:
                raise AgentConnectionError(f"Connection failed: {e}") from e
            except anthropic.RateLimitError as e:
                raise AgentRateLimitError(f"Rate limit exceeded: {e}") from e
            except anthropic.APIStatusError as e:
                raise AgentAPIError(e.status_code, e.message) from e
            except anthropic.APIResponseValidationError as e:
                raise AgentError(f"Response validation failed: {e}") from e

            self._context_window = info.max_input_tokens
        return self._context_window

    def _get_tool_definitions(self, allowed_tools: list[str] | None) -> list[ToolParam]:
        """Filter tool definitions by allowlist. None means all tools."""
        definitions = self._tools.definitions
        if allowed_tools is not None:
            allowed = set(allowed_tools)
            definitions = [d for d in definitions if d["name"] in allowed]
        return definitions

    def _map_stop_reason(self, raw: str) -> StopReason:
        """Map a raw Anthropic stop_reason string to the generic StopReason enum."""
        # pause_turn gets an explicit check to provide a more informative message than "Unknown stop_reason"
        if raw == "pause_turn":
            raise AgentError("pause_turn is not supported in batch mode") from None
        mapping = {
            "end_turn": StopReason.END_TURN,
            "tool_use": StopReason.TOOL_USE,
            "max_tokens": StopReason.MAX_TOKENS,
            "stop_sequence": StopReason.OTHER,
            "refusal": StopReason.OTHER,
        }
        if raw not in mapping:
            raise AgentError(f"Unknown stop_reason: {raw!r}") from None
        return mapping[raw]

    def _to_tool_result_params(self, messages: list[ToolResultMessage]) -> list[ToolResultBlockParam]:
        """Convert model-agnostic ToolResultMessages to Anthropic SDK ToolResultBlockParams."""
        return [
            {
                "type": "tool_result",
                "tool_use_id": msg.tool_call_id,
                "is_error": not msg.result.success,
                **(
                    {"content": msg.result.data}
                    if msg.result.data is not None
                    else {"content": msg.result.error or "(unknown error)"}
                    if not msg.result.success
                    else {}
                ),
            }
            for msg in messages
        ]

    @overload
    @staticmethod
    def _with_user_cache_breakpoint(content: str) -> list[TextBlockParam]: ...

    @overload
    @staticmethod
    def _with_user_cache_breakpoint(content: list[ToolResultBlockParam]) -> list[ToolResultBlockParam]: ...

    @staticmethod
    def _with_user_cache_breakpoint(
        content: str | list[ToolResultBlockParam],
    ) -> list[TextBlockParam] | list[ToolResultBlockParam]:
        """Return a block list with a sliding cache breakpoint on the last block."""
        if isinstance(content, str):
            return [{"type": "text", "text": content, "cache_control": SLIDING_CACHE_CONTROL}]
        if not content:
            return []
        return [*content[:-1], {**content[-1], "cache_control": SLIDING_CACHE_CONTROL}]

    @staticmethod
    def _with_tools_cache_breakpoint(tool_defs: list[ToolParam]) -> list[ToolParam]:
        """Return a tool list with a static cache breakpoint on the last tool."""
        if not tool_defs:
            return tool_defs
        return [*tool_defs[:-1], {**tool_defs[-1], "cache_control": STATIC_CACHE_CONTROL}]

    async def send(
        self,
        content: str | list[ToolResultMessage],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse:
        """Send a message to the agent and return the response.
        Args:
            content: The content to send to the agent.
            allowed_tools: The tools in the ToolRegistry to allow the agent to use.
        Returns:
            An AgentResponse object containing the response from the agent.
        """
        tool_defs = self._with_tools_cache_breakpoint(self._get_tool_definitions(allowed_tools))

        api_content: str | list[ToolResultBlockParam] = (
            self._to_tool_result_params(content) if isinstance(content, list) else content
        )
        user_msg_for_history: MessageParam = {"role": "user", "content": api_content}
        user_msg_for_request: MessageParam = {
            "role": "user",
            "content": self._with_user_cache_breakpoint(api_content),
        }
        messages = [*self._history, user_msg_for_request]

        system_param: list[TextBlockParam] = [
            {"type": "text", "text": self._system_prompt, "cache_control": STATIC_CACHE_CONTROL}
        ]

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_param,
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

        stop_reason = self._map_stop_reason(response.stop_reason)

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
            context_usage=ContextUsage(window_size=await self._get_context_window(), used_tokens=used_tokens),
        )

        agent_response = AgentResponse(
            stop_reason=stop_reason,
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            usage=usage,
        )

        # Save to history only after a successful response. Use the unmarked form so the
        # cache_control breakpoint is only ever on the latest user message — this keeps the
        # request below the 4-marker limit regardless of conversation length.
        self._history.extend([user_msg_for_history, {"role": "assistant", "content": response.content}])

        return agent_response
