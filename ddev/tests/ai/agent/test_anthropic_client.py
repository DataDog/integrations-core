# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.agent.exceptions import AgentAPIError, AgentConnectionError, AgentError, AgentRateLimitError
from ddev.ai.agent.types import StopReason, ToolResultMessage
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.registry import ToolRegistry

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


FAKE_CONTEXT_WINDOW = 200_000


def make_agent(
    tools: ToolRegistry | None = None,
    mock_response: SimpleNamespace | None = None,
) -> tuple[AnthropicAgent, AsyncMock]:
    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=mock_response or make_response("end_turn", []))
    client.models = MagicMock()
    client.models.retrieve = AsyncMock(return_value=SimpleNamespace(max_input_tokens=FAKE_CONTEXT_WINDOW))
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


async def test_end_turn_single_text_block() -> None:
    content = [make_text_block("Hello!")]
    resp = make_response("end_turn", content)
    agent, _ = make_agent(mock_response=resp)

    result = await agent.send("Hi")

    assert result.stop_reason is StopReason.END_TURN
    assert result.text == "Hello!"
    assert result.tool_calls == []
    assert len(agent.history) == 2
    assert agent.history[0] == {"role": "user", "content": "Hi"}
    assert agent.history[1] == {"role": "assistant", "content": content}


# ---------------------------------------------------------------------------
# tool_use
# ---------------------------------------------------------------------------


async def test_tool_use_single_block() -> None:
    block = make_tool_use_block(id="toolu_42", name="read_file", input={"path": "/etc/hosts"})
    resp = make_response("tool_use", [block])
    agent, _ = make_agent(mock_response=resp)

    result = await agent.send("Read hosts")

    assert result.stop_reason is StopReason.TOOL_USE
    assert len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc.id == "toolu_42"
    assert tc.name == "read_file"
    assert tc.input == {"path": "/etc/hosts"}


# ---------------------------------------------------------------------------
# mixed TextBlock + ToolUseBlock
# ---------------------------------------------------------------------------


async def test_mixed_text_and_tool_use() -> None:
    content = [
        make_text_block("I'll read the file for you."),
        make_tool_use_block(id="toolu_01", name="read_file"),
    ]
    resp = make_response("tool_use", content)
    agent, _ = make_agent(mock_response=resp)

    result = await agent.send("Read a file")

    assert result.text == "I'll read the file for you."
    assert len(result.tool_calls) == 1


# ---------------------------------------------------------------------------
# Multiple TextBlocks are concatenated
# ---------------------------------------------------------------------------


async def test_multiple_text_blocks_are_concatenated() -> None:
    content = [make_text_block("Hello, "), make_text_block("world!")]
    resp = make_response("end_turn", content)
    agent, _ = make_agent(mock_response=resp)

    result = await agent.send("Hi")

    assert result.text == "Hello, \nworld!"


# ---------------------------------------------------------------------------
# max_tokens is a normal response (not an error)
# ---------------------------------------------------------------------------


async def test_max_tokens_is_not_an_error() -> None:
    resp = make_response("max_tokens", [make_text_block("Truncated...")])
    agent, _ = make_agent(mock_response=resp)

    result = await agent.send("Tell me everything")

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

    async def run(self, raw: dict) -> ToolResult:
        pass


async def test_allowed_tools_filters_to_subset() -> None:
    registry = ToolRegistry([FakeTool(n) for n in ["read_file", "grep", "mkdir"]])
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, create_mock = make_agent(tools=registry, mock_response=resp)

    await agent.send("Hi", allowed_tools=["read_file"])

    sent_names = [t["name"] for t in create_mock.call_args.kwargs["tools"]]
    assert sent_names == ["read_file"]


async def test_allowed_tools_none_passes_all() -> None:
    registry = ToolRegistry([FakeTool(n) for n in ["a", "b"]])
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, create_mock = make_agent(tools=registry, mock_response=resp)

    await agent.send("Hi", allowed_tools=None)

    sent_names = [t["name"] for t in create_mock.call_args.kwargs["tools"]]
    assert sent_names == ["a", "b"]


@pytest.mark.parametrize("allowed_tools", [[], ["nonexistent_tool"]])
async def test_allowed_tools_passes_not_given(allowed_tools: list[str]) -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, create_mock = make_agent(mock_response=resp)

    await agent.send("Hi", allowed_tools=allowed_tools)

    assert create_mock.call_args.kwargs["tools"] is anthropic.NOT_GIVEN


# ---------------------------------------------------------------------------
# API errors map to the correct AgentError subclass
# ---------------------------------------------------------------------------


def _make_error_agent(side_effect: Exception) -> AnthropicAgent:
    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(side_effect=side_effect)
    return AnthropicAgent(client=client, tools=ToolRegistry([]), system_prompt="", name="t")


async def test_connection_error_maps_to_agent_connection_error() -> None:
    agent = _make_error_agent(anthropic.APIConnectionError(request=MagicMock()))

    with pytest.raises(AgentConnectionError) as exc_info:
        await agent.send("Hi")

    assert "Connection failed" in str(exc_info.value)
    assert agent.history == []


async def test_rate_limit_error_maps_to_agent_rate_limit_error() -> None:
    agent = _make_error_agent(
        anthropic.RateLimitError(
            message="rate limit",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
    )

    with pytest.raises(AgentRateLimitError) as exc_info:
        await agent.send("Hi")

    assert "Rate limit exceeded" in str(exc_info.value)
    assert agent.history == []


async def test_api_status_error_maps_to_agent_api_error() -> None:
    agent = _make_error_agent(
        anthropic.APIStatusError(
            message="internal server error",
            response=MagicMock(status_code=500),
            body=None,
        )
    )

    with pytest.raises(AgentAPIError) as exc_info:
        await agent.send("Hi")

    assert exc_info.value.status_code == 500
    assert agent.history == []


async def test_response_validation_error_maps_to_agent_error() -> None:
    agent = _make_error_agent(anthropic.APIResponseValidationError(response=MagicMock(), body=None))

    with pytest.raises(AgentError) as exc_info:
        await agent.send("Hi")

    assert "Response validation failed" in str(exc_info.value)
    assert agent.history == []


# ---------------------------------------------------------------------------
# Unknown stop_reason raises AgentError, history unchanged
# ---------------------------------------------------------------------------


async def test_unknown_stop_reason_raises_agent_error() -> None:
    resp = make_response("totally_unknown_reason", [])
    agent, _ = make_agent(mock_response=resp)

    with pytest.raises(AgentError) as exc_info:
        await agent.send("Hi")

    assert agent.history == []
    assert "Unknown stop_reason" in str(exc_info.value)
    assert "totally_unknown_reason" in str(exc_info.value)


# ---------------------------------------------------------------------------
# cache_read_input_tokens=None defaults to 0
# ---------------------------------------------------------------------------


async def test_cache_tokens_none_defaults_to_zero() -> None:
    usage = make_usage(cache_read=None, cache_creation=None)
    resp = make_response("end_turn", [make_text_block("ok")], usage=usage)
    agent, _ = make_agent(mock_response=resp)

    result = await agent.send("Hi")

    assert result.usage.cache_read_input_tokens == 0
    assert result.usage.cache_creation_input_tokens == 0


# ---------------------------------------------------------------------------
# ContextUsage fields
# ---------------------------------------------------------------------------


async def test_context_usage_fields() -> None:
    usage = make_usage(input_tokens=1000, cache_read=500, cache_creation=200)
    resp = make_response("end_turn", [make_text_block("ok")], usage=usage)
    agent, _ = make_agent(mock_response=resp)

    result = await agent.send("Hi")

    ctx = result.usage.context_usage
    assert ctx.window_size == FAKE_CONTEXT_WINDOW
    assert ctx.used_tokens == 1700  # 1000 + 500 + 200
    assert ctx.context_pct == pytest.approx(1700 / FAKE_CONTEXT_WINDOW * 100)
    assert ctx.remaining_tokens == FAKE_CONTEXT_WINDOW - 1700


# ---------------------------------------------------------------------------
# context_window is fetched once and cached across multiple sends
# ---------------------------------------------------------------------------


async def test_context_window_fetched_once() -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, _ = make_agent(mock_response=resp)
    agent._client.messages.create = AsyncMock(return_value=resp)

    await agent.send("First")
    await agent.send("Second")

    agent._client.models.retrieve.assert_awaited_once()


# ---------------------------------------------------------------------------
# Multi-turn — send str then send tool results → history has 4 entries
# ---------------------------------------------------------------------------


async def test_multi_turn_history_grows_correctly() -> None:
    tool_resp = make_response("tool_use", [make_tool_use_block(id="toolu_01")])
    text_resp = make_response("end_turn", [make_text_block("Done.")])

    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(side_effect=[tool_resp, text_resp])
    client.models = MagicMock()
    client.models.retrieve = AsyncMock(return_value=SimpleNamespace(max_input_tokens=FAKE_CONTEXT_WINDOW))
    agent = AnthropicAgent(client=client, tools=ToolRegistry([]), system_prompt="", name="t")

    first = await agent.send("Do X")
    assert first.stop_reason is StopReason.TOOL_USE
    assert len(agent.history) == 2

    tool_results = [ToolResultMessage(tool_call_id="toolu_01", result=ToolResult(success=True, data="result"))]
    second = await agent.send(tool_results)
    assert second.stop_reason is StopReason.END_TURN
    assert len(agent.history) == 4
    assert agent.history[2]["role"] == "user"
    assert agent.history[3]["role"] == "assistant"


# ---------------------------------------------------------------------------
# history property returns a copy
# ---------------------------------------------------------------------------


async def test_history_property_returns_copy() -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, _ = make_agent(mock_response=resp)
    await agent.send("Hi")

    snapshot = agent.history
    snapshot.clear()

    assert len(agent.history) == 2


# ---------------------------------------------------------------------------
# reset() clears history
# ---------------------------------------------------------------------------


async def test_reset_clears_history() -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, _ = make_agent(mock_response=resp)
    await agent.send("Hi")
    assert len(agent.history) == 2

    agent.reset()
    assert agent.history == []


# ---------------------------------------------------------------------------
# pause_turn raises AgentError
# ---------------------------------------------------------------------------


async def test_pause_turn_raises_agent_error() -> None:
    resp = make_response("pause_turn", [])
    agent, _ = make_agent(mock_response=resp)

    with pytest.raises(AgentError):
        await agent.send("Hi")

    assert agent.history == []


# ---------------------------------------------------------------------------
# refusal and stop_sequence map to StopReason.OTHER
# ---------------------------------------------------------------------------


async def test_refusal_maps_to_other() -> None:
    resp = make_response("refusal", [make_text_block("I can't do that")])
    agent, _ = make_agent(mock_response=resp)

    result = await agent.send("Do something bad")

    assert result.stop_reason is StopReason.OTHER


async def test_stop_sequence_maps_to_other() -> None:
    resp = make_response("stop_sequence", [make_text_block("Stopped.")])
    agent, _ = make_agent(mock_response=resp)

    result = await agent.send("Hi")

    assert result.stop_reason is StopReason.OTHER


# ---------------------------------------------------------------------------
# Error mid-conversation leaves history unchanged
# ---------------------------------------------------------------------------


async def test_error_mid_conversation_leaves_history_unchanged() -> None:
    ok_resp = make_response("end_turn", [make_text_block("ok")])
    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(
        side_effect=[
            ok_resp,
            anthropic.APIConnectionError(request=MagicMock()),
        ]
    )
    client.models = MagicMock()
    client.models.retrieve = AsyncMock(return_value=SimpleNamespace(max_input_tokens=FAKE_CONTEXT_WINDOW))
    agent = AnthropicAgent(client=client, tools=ToolRegistry([]), system_prompt="", name="t")

    await agent.send("First message")
    history_after_first = agent.history[:]

    with pytest.raises(AgentConnectionError):
        await agent.send("Second message")

    assert agent.history == history_after_first


# ---------------------------------------------------------------------------
# Prompt caching: static breakpoints (system + last tool, 1h TTL)
# ---------------------------------------------------------------------------


async def test_system_prompt_sent_as_block_with_static_cache_control() -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, create_mock = make_agent(mock_response=resp)

    await agent.send("Hi")

    assert create_mock.call_args.kwargs["system"] == [
        {
            "type": "text",
            "text": "You are helpful.",
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        }
    ]


@pytest.mark.parametrize(
    "tool_names",
    [["only"], ["a", "b"], ["a", "b", "c", "d"]],
    ids=["single_tool", "two_tools", "four_tools"],
)
async def test_only_last_tool_carries_static_cache_control(tool_names: list[str]) -> None:
    registry = ToolRegistry([FakeTool(n) for n in tool_names])
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, create_mock = make_agent(tools=registry, mock_response=resp)

    await agent.send("Hi")

    sent_tools = create_mock.call_args.kwargs["tools"]
    assert all("cache_control" not in t for t in sent_tools[:-1])
    assert sent_tools[-1]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


async def test_allowed_tools_subset_places_cache_control_on_last_of_subset() -> None:
    registry = ToolRegistry([FakeTool(n) for n in ["a", "b", "c"]])
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, create_mock = make_agent(tools=registry, mock_response=resp)

    await agent.send("Hi", allowed_tools=["a", "b"])

    sent_tools = create_mock.call_args.kwargs["tools"]
    assert [t["name"] for t in sent_tools] == ["a", "b"]
    assert "cache_control" not in sent_tools[0]
    assert sent_tools[-1]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


# ---------------------------------------------------------------------------
# Prompt caching: sliding breakpoint on the last user message block (default TTL)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("Hi there", id="str"),
        pytest.param(
            [ToolResultMessage(tool_call_id="t1", result=ToolResult(success=True, data="r1"))],
            id="single_tool_result",
        ),
        pytest.param(
            [ToolResultMessage(tool_call_id=f"t{i}", result=ToolResult(success=True, data=f"r{i}")) for i in range(3)],
            id="multiple_tool_results",
        ),
    ],
)
async def test_sliding_cache_control_on_last_user_block_only(
    content: str | list[ToolResultMessage],
) -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, create_mock = make_agent(mock_response=resp)

    await agent.send(content)

    blocks = create_mock.call_args.kwargs["messages"][-1]["content"]
    assert isinstance(blocks, list) and blocks
    assert all("cache_control" not in b for b in blocks[:-1])
    assert blocks[-1]["cache_control"] == {"type": "ephemeral"}
    assert "ttl" not in blocks[-1]["cache_control"]


async def test_empty_tool_results_produces_empty_content_block() -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, create_mock = make_agent(mock_response=resp)

    await agent.send([])

    blocks = create_mock.call_args.kwargs["messages"][-1]["content"]
    assert blocks == []


# ---------------------------------------------------------------------------
# Prompt caching: history must not retain cache_control markers
# (otherwise multi-turn requests would exceed the 4-marker limit)
# ---------------------------------------------------------------------------


async def test_history_str_message_keeps_raw_str_form() -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, _ = make_agent(mock_response=resp)

    await agent.send("Hi")

    assert agent.history[0] == {"role": "user", "content": "Hi"}


async def test_history_tool_result_blocks_have_no_cache_control() -> None:
    resp = make_response("end_turn", [make_text_block("ok")])
    agent, _ = make_agent(mock_response=resp)

    tool_results = [
        ToolResultMessage(tool_call_id=f"t{i}", result=ToolResult(success=True, data=f"r{i}")) for i in range(2)
    ]
    await agent.send(tool_results)

    blocks = agent.history[0]["content"]
    assert all("cache_control" not in b for b in blocks)


async def test_multi_turn_only_latest_user_message_in_request_has_cache_control() -> None:
    first_resp = make_response("tool_use", [make_tool_use_block(id="t1")])
    second_resp = make_response("end_turn", [make_text_block("done")])

    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.messages = MagicMock()
    client.messages.create = AsyncMock(side_effect=[first_resp, second_resp])
    client.models = MagicMock()
    client.models.retrieve = AsyncMock(return_value=SimpleNamespace(max_input_tokens=FAKE_CONTEXT_WINDOW))
    agent = AnthropicAgent(client=client, tools=ToolRegistry([]), system_prompt="sp", name="t")

    await agent.send("First")
    await agent.send([ToolResultMessage(tool_call_id="t1", result=ToolResult(success=True, data="r"))])

    first_call_messages = client.messages.create.call_args_list[0].kwargs["messages"]
    assert first_call_messages[-1]["content"] == [
        {"type": "text", "text": "First", "cache_control": {"type": "ephemeral"}}
    ]

    second_call_messages = client.messages.create.call_args_list[1].kwargs["messages"]
    assert second_call_messages[0] == {"role": "user", "content": "First"}
    latest_blocks = second_call_messages[-1]["content"]
    assert all("cache_control" not in b for b in latest_blocks[:-1])
    assert latest_blocks[-1]["cache_control"] == {"type": "ephemeral"}
