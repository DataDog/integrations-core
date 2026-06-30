# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, overload

import anthropic
from anthropic.types import MessageParam

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.exceptions import AgentAPIError, AgentConnectionError, AgentError, AgentRateLimitError
from ddev.ai.agent.types import (
    AgentResponse,
    ContextUsage,
    StopReason,
    TokenUsage,
    ToolCall,
    ToolResultMessage,
    WebActivity,
    WebCitation,
    WebFetchCall,
    WebSearchCall,
)
from ddev.ai.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from anthropic.types import (
        CacheControlEphemeralParam,
        Message,
        TextBlockParam,
        ToolParam,
        ToolResultBlockParam,
    )

DEFAULT_MODEL: Final[str] = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS: Final[int] = 8192  # max tokens per response
MAX_CONTINUATIONS: Final[int] = 10

# Pinned to the ZDR-eligible versions; the _20260209 variants are not ZDR-eligible by default.
WEB_SEARCH_VERSION: Final[str] = "web_search_20250305"
WEB_FETCH_VERSION: Final[str] = "web_fetch_20250910"

NATIVE_TOOL_DEFINITIONS: Final[dict[str, ToolParam]] = {
    # max_uses stays below MAX_CONTINUATIONS so a turn is always left to receive the final response.
    "web_search": {"type": WEB_SEARCH_VERSION, "name": "web_search", "max_uses": MAX_CONTINUATIONS - 1},
    "web_fetch": {
        "type": WEB_FETCH_VERSION,
        "name": "web_fetch",
        "max_uses": MAX_CONTINUATIONS - 1,
        "citations": {"enabled": True},
    },
}

# 1h TTL for the static prefix (system + tools): paid once, read for the whole session.
STATIC_CACHE_CONTROL: Final[CacheControlEphemeralParam] = {"type": "ephemeral", "ttl": "1h"}
# Default TTL (currently 5 min, but Anthropic may change it) for the sliding breakpoint
# on the last user message: re-written each turn, so a longer TTL would be wasted.
SLIDING_CACHE_CONTROL: Final[CacheControlEphemeralParam] = {"type": "ephemeral"}


@dataclass(frozen=True)
class CompletionResult:
    """Outcome of driving messages.create across pause_turn continuations."""

    final_response: Message
    paused_turns: list[MessageParam]
    all_responses: list[Message]


@dataclass(frozen=True)
class ResponseContent:
    """Parsed pieces of a single response's content blocks."""

    text: str
    tool_calls: list[ToolCall]
    citations: list[WebCitation]


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

    def reconcile_pending_tool_calls(self, placeholder_error: str) -> int:
        if not self._history or self._history[-1]["role"] != "assistant":
            return 0

        content = self._history[-1]["content"]
        tool_use_ids: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "tool_use":
                    tool_use_ids.append(block["id"])
            elif getattr(block, "type", None) == "tool_use":
                tool_use_ids.append(block.id)

        if not tool_use_ids:
            return 0

        synthetic_results = [
            {"type": "tool_result", "tool_use_id": id_, "is_error": True, "content": placeholder_error}
            for id_ in tool_use_ids
        ]
        self._history.append({"role": "user", "content": synthetic_results})
        return len(tool_use_ids)

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

    @staticmethod
    def _filter_by_allowed(names: list[str], allowed_tools: list[str] | None) -> list[str]:
        """Filter names by allowlist. None means all names."""
        if allowed_tools is None:
            return names
        allowed = set(allowed_tools)
        return [n for n in names if n in allowed]

    def _get_tool_definitions(self, allowed_tools: list[str] | None) -> list[ToolParam]:
        """Filter tool definitions by allowlist. None means all tools."""
        definitions = self._tools.definitions
        allowed_names = set(self._filter_by_allowed([d["name"] for d in definitions], allowed_tools))
        return [d for d in definitions if d["name"] in allowed_names]

    def _map_stop_reason(self, raw: str) -> StopReason:
        """Map a raw Anthropic stop_reason string to the generic StopReason enum."""
        mapping = {
            "end_turn": StopReason.END_TURN,
            "tool_use": StopReason.TOOL_USE,
            "max_tokens": StopReason.MAX_TOKENS,
            "stop_sequence": StopReason.OTHER,
            "refusal": StopReason.OTHER,
        }
        if raw == "pause_turn":
            raise AgentError("pause_turn leaked past continuation loop") from None
        if raw not in mapping:
            raise AgentError(f"Unknown stop_reason: {raw!r}") from None
        return mapping[raw]

    def _native_tool_defs(self, allowed_tools: list[str] | None) -> list[ToolParam]:
        names = self._filter_by_allowed(self._tools.native_tool_names, allowed_tools)
        return [NATIVE_TOOL_DEFINITIONS[name] for name in names]

    @staticmethod
    def _server_tool_requests(response: Message, attr: str) -> int:
        """Server tool request count from one response (0 if absent). Robust to fakes/providers."""
        server_use = getattr(response.usage, "server_tool_use", None)
        return getattr(server_use, attr, 0)

    @staticmethod
    def _extract_web_searches(responses: list[Message]) -> list[WebSearchCall]:
        """Collect server-side web searches (query + result count) across all responses.

        Web searches are server tools: the model emits a ``ServerToolUseBlock`` (the query)
        and Anthropic answers inline with a ``WebSearchToolResultBlock`` (the results). They
        never become client ``ToolCall``s, so we surface them here for logging.
        """
        queries: dict[str, str] = {}
        results: dict[str, tuple[int, str | None]] = {}
        for response in responses:
            for block in response.content:
                if isinstance(block, anthropic.types.ServerToolUseBlock) and block.name == "web_search":
                    query = block.input.get("query", "")
                    queries[block.id] = str(query)
                elif isinstance(block, anthropic.types.WebSearchToolResultBlock):
                    content = block.content
                    if isinstance(content, anthropic.types.WebSearchToolResultError):
                        results[block.tool_use_id] = (0, content.error_code)
                    else:
                        results[block.tool_use_id] = (len(content), None)

        searches: list[WebSearchCall] = []
        for use_id, query in queries.items():
            count, error = results.get(use_id, (0, None))
            searches.append(WebSearchCall(query=query, result_count=count, error=error))
        return searches

    @staticmethod
    def _extract_web_fetches(responses: list[Message]) -> list[WebFetchCall]:
        """Collect server-side web fetches (url + retrieved_at/error) across all responses.

        Like web searches, fetches are server tools: the model emits a ``ServerToolUseBlock``
        (the url) and Anthropic answers inline with a ``WebFetchToolResultBlock``. They never
        become client ``ToolCall``s, so we surface them here for logging.
        """
        urls: dict[str, str] = {}
        results: dict[str, tuple[str | None, str | None]] = {}
        for response in responses:
            for block in response.content:
                if isinstance(block, anthropic.types.ServerToolUseBlock) and block.name == "web_fetch":
                    url = block.input.get("url", "")
                    urls[block.id] = str(url)
                elif isinstance(block, anthropic.types.WebFetchToolResultBlock):
                    content = block.content
                    if isinstance(content, anthropic.types.WebFetchToolResultErrorBlock):
                        results[block.tool_use_id] = (None, content.error_code)
                    else:
                        results[block.tool_use_id] = (content.retrieved_at, None)

        fetches: list[WebFetchCall] = []
        for use_id, url in urls.items():
            retrieved_at, error = results.get(use_id, (None, None))
            fetches.append(WebFetchCall(url=url, retrieved_at=retrieved_at, error=error))
        return fetches

    async def _create_until_complete(
        self,
        *,
        request_messages: list[MessageParam],
        system_param: list[TextBlockParam],
        tool_defs: list[ToolParam],
    ) -> CompletionResult:
        """Call messages.create, transparently continuing across pause_turn.

        all_responses includes all intermediate responses so the caller can sum
        token usage across calls.
        """
        paused_turns: list[MessageParam] = []
        all_responses: list[Message] = []
        messages = request_messages
        for _ in range(MAX_CONTINUATIONS):
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_param,
                messages=messages,
                tools=tool_defs if tool_defs else anthropic.NOT_GIVEN,
            )
            all_responses.append(response)
            if response.stop_reason != "pause_turn":
                return CompletionResult(final_response=response, paused_turns=paused_turns, all_responses=all_responses)
            paused_turn: MessageParam = {"role": "assistant", "content": response.content}
            paused_turns.append(paused_turn)
            messages = [*messages, paused_turn]
        raise AgentError(f"pause_turn did not resolve after {MAX_CONTINUATIONS} continuations")

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

    def _assemble_tool_defs(self, allowed_tools: list[str] | None) -> list[ToolParam]:
        """Combine client and native tool defs, with the static cache breakpoint on the last."""
        tool_defs = self._get_tool_definitions(allowed_tools) + self._native_tool_defs(allowed_tools)
        return self._with_tools_cache_breakpoint(tool_defs)

    async def _call_api(
        self,
        *,
        messages: list[MessageParam],
        system_param: list[TextBlockParam],
        tool_defs: list[ToolParam],
    ) -> CompletionResult:
        """Drive the continuation loop, mapping Anthropic SDK errors to agent errors."""
        try:
            return await self._create_until_complete(
                request_messages=messages,
                system_param=system_param,
                tool_defs=tool_defs,
            )
        except anthropic.APIConnectionError as e:
            raise AgentConnectionError(f"Connection failed: {e}") from e
        except anthropic.RateLimitError as e:
            raise AgentRateLimitError(f"Rate limit exceeded: {e}") from e
        except anthropic.APIStatusError as e:
            raise AgentAPIError(e.status_code, e.message) from e
        except anthropic.APIResponseValidationError as e:
            raise AgentError(f"Response validation failed: {e}") from e

    @staticmethod
    def _parse_response_content(response: Message) -> ResponseContent:
        """Extract text, client tool calls, and web-search/fetch citations from response blocks.

        Server tool blocks are intentionally skipped: they stay verbatim in history so
        Anthropic can resolve encrypted_content / encrypted_index for citations.
        """
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        citations: list[WebCitation] = []
        for block in response.content:
            if isinstance(block, anthropic.types.TextBlock):
                text_parts.append(block.text)
                for c in block.citations or []:
                    if isinstance(c, anthropic.types.CitationsWebSearchResultLocation):
                        citations.append(WebCitation(url=c.url, title=c.title, cited_text=c.cited_text))
                    elif isinstance(
                        c,
                        (
                            anthropic.types.CitationCharLocation,
                            anthropic.types.CitationPageLocation,
                            anthropic.types.CitationContentBlockLocation,
                        ),
                    ):
                        citations.append(WebCitation(cited_text=c.cited_text, title=c.document_title))
            elif isinstance(block, anthropic.types.ToolUseBlock):
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=dict(block.input)))
        return ResponseContent(text="\n".join(text_parts), tool_calls=tool_calls, citations=citations)

    async def _build_usage(self, completion: CompletionResult) -> TokenUsage:
        """Sum token and web-search usage across all responses; context reflects the final call."""
        all_responses = completion.all_responses
        final = completion.final_response
        final_cache_read = final.usage.cache_read_input_tokens or 0
        final_cache_creation = final.usage.cache_creation_input_tokens or 0
        return TokenUsage(
            input_tokens=sum(r.usage.input_tokens for r in all_responses),
            output_tokens=sum(r.usage.output_tokens for r in all_responses),
            cache_read_input_tokens=sum(r.usage.cache_read_input_tokens or 0 for r in all_responses),
            cache_creation_input_tokens=sum(r.usage.cache_creation_input_tokens or 0 for r in all_responses),
            context_usage=ContextUsage(
                window_size=await self._get_context_window(),
                used_tokens=final.usage.input_tokens + final_cache_read + final_cache_creation,
            ),
            web_search_requests=sum(self._server_tool_requests(r, "web_search_requests") for r in all_responses),
            web_fetch_requests=sum(self._server_tool_requests(r, "web_fetch_requests") for r in all_responses),
        )

    def _append_history(
        self, user_msg: MessageParam, paused_turns: list[MessageParam], final_response: Message
    ) -> None:
        """Append the user turn, any paused turns, and the final assistant turn to history.

        Paused turns precede the final turn so multi-turn citations remain valid.
        """
        self._history.append(user_msg)
        self._history.extend(paused_turns)
        self._history.append({"role": "assistant", "content": final_response.content})

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
        tool_defs = self._assemble_tool_defs(allowed_tools)

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

        completion = await self._call_api(messages=messages, system_param=system_param, tool_defs=tool_defs)
        final = completion.final_response

        # stop_reason is None only in streaming responses; we use non-streaming, so None is unexpected
        if final.stop_reason is None:
            raise AgentError("Received null stop_reason from API")

        parsed = self._parse_response_content(final)
        agent_response = AgentResponse(
            stop_reason=self._map_stop_reason(final.stop_reason),
            text=parsed.text,
            tool_calls=parsed.tool_calls,
            usage=await self._build_usage(completion),
            web_activity=WebActivity(
                searches=self._extract_web_searches(completion.all_responses),
                fetches=self._extract_web_fetches(completion.all_responses),
                citations=parsed.citations,
            ),
        )

        # Save to history only after a successful response.
        self._append_history(user_msg_for_history, completion.paused_turns, final)
        return agent_response
