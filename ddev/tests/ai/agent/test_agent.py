# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest

from ddev.ai.agent.agent import AnthropicAgent
from ddev.ai.agent.types import (
    AgentAPIError,
    AgentConnectionError,
    AgentError,
    AgentRateLimitError,
    StopReason,
)
from ddev.ai.tools.core.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_usage(
    input_tokens: int = 10,
    output_tokens: int = 20,
    cache_read: int | None = None,
    cache_creation: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_creation,
    )


def make_text_block(text: str) -> anthropic.types.TextBlock:
    return anthropic.types.TextBlock(type="text", text=text)


def make_tool_use_block(
    id: str = "toolu_01",
    name: str = "read_file",
    input: dict | None = None,
) -> anthropic.types.ToolUseBlock:
    return anthropic.types.ToolUseBlock(
        type="tool_use",
        id=id,
        name=name,
        input=input or {"path": "/tmp/file.txt"},
    )


def make_response(
    stop_reason: str | None,
    content: list,
    usage: SimpleNamespace | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=content,
        usage=usage or make_usage(),
    )


def make_agent(
    tools: ToolRegistry | None = None,
    mock_response: SimpleNamespace | None = None,
) -> tuple[AnthropicAgent, AsyncMock]:
    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=mock_response or make_response("end_turn", []))
    registry = tools or ToolRegistry([])
    agent = AnthropicAgent(
        client=client,
        tools=registry,
        system_prompt="You are helpful.",
        name="test-agent",
    )
    return agent, client.messages.create


# ---------------------------------------------------------------------------
# end_turn with a single TextBlock
# ---------------------------------------------------------------------------


def test_end_turn_single_text_block() -> None:
    content = [make_text_block("Hello!")]
    resp = make_response("end_turn", content)
    agent, _ = make_agent(mock_response=resp)

    result = asyncio.run(agent.send("Hi"))

    assert result.stop_reason is StopReason.END_TURN
    assert result.text == "Hello!"
    assert result.tool_calls == []
    assert len(agent.history) == 2
    assert agent.history[0] == {"role": "user", "content": "Hi"}
    assert agent.history[1] == {"role": "assistant", "content": content}


# ---------------------------------------------------------------------------
# tool_use
# ---------------------------------------------------------------------------


def test_tool_use_single_block() -> None:
    block = make_tool_use_block(id="toolu_42", name="read_file", input={"path": "/etc/hosts"})
    resp = make_response("tool_use", [block])
    agent, _ = make_agent(mock_response=resp)

    result = asyncio.run(agent.send("Read hosts"))

    assert result.stop_reason is StopReason.TOOL_USE
    assert len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc.id == "toolu_42"
    assert tc.name == "read_file"
    assert tc.input == {"path": "/etc/hosts"}


# ---------------------------------------------------------------------------
# mixed TextBlock + ToolUseBlock
# ---------------------------------------------------------------------------


def test_mixed_text_and_tool_use() -> None:
    content = [
        make_text_block("I'll read the file for you."),
        make_tool_use_block(id="toolu_01", name="read_file"),
    ]
    resp = make_response("tool_use", content)
    agent, _ = make_agent(mock_response=resp)

    result = asyncio.run(agent.send("Read a file"))

    assert result.text == "I'll read the file for you."
    assert len(result.tool_calls) == 1


# ---------------------------------------------------------------------------
# Multiple TextBlocks are concatenated
# ---------------------------------------------------------------------------


def test_multiple_text_blocks_are_concatenated() -> None:
    content = [make_text_block("Hello, "), make_text_block("world!")]
    resp = make_response("end_turn", content)
    agent, _ = make_agent(mock_response=resp)

    result = asyncio.run(agent.send("Hi"))

    assert result.text == "Hello, world!"


# ---------------------------------------------------------------------------
# max_tokens is a normal response (not an error)
# ---------------------------------------------------------------------------


def test_max_tokens_is_not_an_error() -> None:
    resp = make_response("max_tokens", [make_text_block("Truncated...")])
    agent, _ = make_agent(mock_response=resp)

    result = asyncio.run(agent.send("Tell me everything"))

    assert result.stop_reason is StopReason.MAX_TOKENS
    assert len(agent.history) == 2


# ---------------------------------------------------------------------------
# allowed_tools filtering
# ---------------------------------------------------------------------------


class FakeTool:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return ""

    @property
    def definition(self) -> dict:
        return {"name": self._name, "description": "", "input_schema": {}}

    async def run(self, raw: dict) -> None:
        pass


@pytest.mark.parametrize(
    ("tool_names", "allowed_tools", "expected_names"),
    [
        (["read_file", "grep", "mkdir"], ["read_file"], ["read_file"]),
        (["a", "b"], None, ["a", "b"]),
    ],
)
def test_allowed_tools(
    tool_names: list[str],
    allowed_tools: list[str] | None,
    expected_names: list[str],
) -> None:
    registry = ToolRegistry([FakeTool(n) for n in tool_names])
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, create_mock = make_agent(tools=registry, mock_response=resp)

    asyncio.run(agent.send("Hi", allowed_tools=allowed_tools))

    sent_names = [t["name"] for t in create_mock.call_args.kwargs["tools"]]
    assert sent_names == expected_names


@pytest.mark.parametrize("allowed_tools", [[], ["nonexistent_tool"]])
def test_allowed_tools_passes_not_given(allowed_tools: list[str]) -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, create_mock = make_agent(mock_response=resp)

    asyncio.run(agent.send("Hi", allowed_tools=allowed_tools))

    assert create_mock.call_args.kwargs["tools"] is anthropic.NOT_GIVEN


# ---------------------------------------------------------------------------
# API errors map to the correct AgentError subclass
# ---------------------------------------------------------------------------

_mock_500 = MagicMock()
_mock_500.status_code = 500


@pytest.mark.parametrize(
    "side_effect,expected_exc,extra_check",
    [
        (
            anthropic.APIConnectionError(request=MagicMock()),
            AgentConnectionError,
            lambda e: "Connection failed" in str(e),
        ),
        (
            anthropic.RateLimitError(
                message="rate limit",
                response=MagicMock(status_code=429, headers={}),
                body=None,
            ),
            AgentRateLimitError,
            lambda e: "Rate limit exceeded" in str(e),
        ),
        (
            anthropic.APIStatusError(
                message="internal server error",
                response=_mock_500,
                body=None,
            ),
            AgentAPIError,
            lambda e: e.status_code == 500,
        ),
        (
            anthropic.APIResponseValidationError(
                response=MagicMock(),
                body=None,
            ),
            AgentError,
            lambda e: "Response validation failed" in str(e),
        ),
    ],
)
def test_api_errors_map_correctly(
    side_effect: Exception,
    expected_exc: type[AgentError],
    extra_check: Callable[[AgentError], bool],
) -> None:
    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(side_effect=side_effect)
    agent = AnthropicAgent(client=client, tools=ToolRegistry([]), system_prompt="", name="t")

    with pytest.raises(expected_exc) as exc_info:
        asyncio.run(agent.send("Hi"))

    assert extra_check(exc_info.value)
    assert agent.history == []


# ---------------------------------------------------------------------------
# Unknown stop_reason raises AgentError, history unchanged
# ---------------------------------------------------------------------------


def test_unknown_stop_reason_raises_agent_error() -> None:
    resp = make_response("totally_unknown_reason", [])
    agent, _ = make_agent(mock_response=resp)

    with pytest.raises(AgentError) as exc_info:
        asyncio.run(agent.send("Hi"))

    assert agent.history == []
    assert "Unknown stop_reason" in str(exc_info.value)
    assert "totally_unknown_reason" in str(exc_info.value)


# ---------------------------------------------------------------------------
# cache_read_input_tokens=None defaults to 0
# ---------------------------------------------------------------------------


def test_cache_tokens_none_defaults_to_zero() -> None:
    usage = make_usage(cache_read=None, cache_creation=None)
    resp = make_response("end_turn", [make_text_block("ok")], usage=usage)
    agent, _ = make_agent(mock_response=resp)

    result = asyncio.run(agent.send("Hi"))

    assert result.usage.cache_read_input_tokens == 0
    assert result.usage.cache_creation_input_tokens == 0


# ---------------------------------------------------------------------------
# Multi-turn — send str then send tool results → history has 4 entries
# ---------------------------------------------------------------------------


def test_multi_turn_history_grows_correctly() -> None:
    tool_resp = make_response("tool_use", [make_tool_use_block(id="toolu_01")])
    text_resp = make_response("end_turn", [make_text_block("Done.")])

    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(side_effect=[tool_resp, text_resp])
    agent = AnthropicAgent(client=client, tools=ToolRegistry([]), system_prompt="", name="t")

    first = asyncio.run(agent.send("Do X"))
    assert first.stop_reason is StopReason.TOOL_USE
    assert len(agent.history) == 2

    tool_results = [{"type": "tool_result", "tool_use_id": "toolu_01", "content": "result"}]
    second = asyncio.run(agent.send(tool_results))
    assert second.stop_reason is StopReason.END_TURN
    assert len(agent.history) == 4
    assert agent.history[2]["role"] == "user"
    assert agent.history[3]["role"] == "assistant"


# ---------------------------------------------------------------------------
# history property returns a copy
# ---------------------------------------------------------------------------


def test_history_property_returns_copy() -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, _ = make_agent(mock_response=resp)
    asyncio.run(agent.send("Hi"))

    snapshot = agent.history
    snapshot.clear()

    assert len(agent.history) == 2


# ---------------------------------------------------------------------------
# reset() clears history
# ---------------------------------------------------------------------------


def test_reset_clears_history() -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, _ = make_agent(mock_response=resp)
    asyncio.run(agent.send("Hi"))
    assert len(agent.history) == 2

    agent.reset()
    assert agent.history == []


# ---------------------------------------------------------------------------
# Error mid-conversation leaves history unchanged
# ---------------------------------------------------------------------------


def test_error_mid_conversation_leaves_history_unchanged() -> None:
    ok_resp = make_response("end_turn", [make_text_block("ok")])
    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(
        side_effect=[
            ok_resp,
            anthropic.APIConnectionError(request=MagicMock()),
        ]
    )
    agent = AnthropicAgent(client=client, tools=ToolRegistry([]), system_prompt="", name="t")

    asyncio.run(agent.send("First message"))
    history_after_first = agent.history[:]

    with pytest.raises(AgentConnectionError):
        asyncio.run(agent.send("Second message"))

    assert agent.history == history_after_first
