# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.agent.base import _COMPACT_SYSTEM_PROMPT, BaseAgent
from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolResultMessage
from ddev.ai.tools.core.registry import ToolRegistry

_AGENT_NAME: str = "test"
_AGENT_SYSTEM_PROMPT: str = "original"

# ---------------------------------------------------------------------------
# Minimal concrete agent for testing BaseAgent
# ---------------------------------------------------------------------------


class ConcreteAgent(BaseAgent[dict]):
    """Minimal BaseAgent subclass that records send() calls and replays configured responses."""

    def __init__(self, responses: list[str | Exception] | None = None) -> None:
        super().__init__(name=_AGENT_NAME, system_prompt=_AGENT_SYSTEM_PROMPT, tools=ToolRegistry([]))
        self._responses = list(responses or [])
        self._idx = 0
        self.send_calls: list[dict] = []

    async def send(
        self,
        content: str | list[ToolResultMessage],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse:
        self.send_calls.append(
            {"content": content, "allowed_tools": allowed_tools, "system_prompt": self._system_prompt}
        )
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            if isinstance(resp, Exception):
                raise resp
            text = resp
        else:
            text = "default summary"
            self._idx += 1

        # Simulate what a real provider does: append user + assistant messages.
        self._history.extend(
            [
                {"role": "user", "content": content},
                {"role": "assistant", "content": text},
            ]
        )
        return AgentResponse(
            stop_reason=StopReason.END_TURN,
            text=text,
            tool_calls=[],
            usage=TokenUsage(input_tokens=0, output_tokens=0, cache_read_input_tokens=0, cache_creation_input_tokens=0),
        )


def make_history(n_messages: int) -> list[dict]:
    """Build n_messages alternating user/assistant dicts for seeding _history directly."""
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg-{i}"} for i in range(n_messages)]


# ---------------------------------------------------------------------------
# compact() — history length after compact (guard cases + collapse)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n_messages, responses, expected_len",
    [
        (0, None, 0),
        (1, None, 1),
        (2, None, 2),
        (4, ["summary"], 2),
    ],
)
async def test_compact_history_length(
    n_messages: int,
    responses: list[str] | None,
    expected_len: int,
) -> None:
    agent = ConcreteAgent(responses=responses)
    agent._history = make_history(n_messages)
    await agent.compact()
    assert len(agent.history) == expected_len


async def test_compact_first_message_is_original_task() -> None:
    agent = ConcreteAgent(responses=["summary"])
    original = make_history(4)[0]
    agent._history = make_history(4)
    await agent.compact()
    assert agent.history[0] == original


async def test_compact_second_message_is_summary_response() -> None:
    agent = ConcreteAgent(responses=["the summary text"])
    agent._history = make_history(4)
    await agent.compact()
    summary_msg = agent.history[1]
    assert summary_msg["role"] == "assistant"
    assert summary_msg["content"] == "the summary text"


# ---------------------------------------------------------------------------
# compact() — system prompt swap
# ---------------------------------------------------------------------------


async def test_compact_uses_compaction_system_prompt() -> None:
    agent = ConcreteAgent(responses=["summary"])
    agent._history = make_history(4)
    await agent.compact()
    assert agent.send_calls[0]["system_prompt"] == _COMPACT_SYSTEM_PROMPT


async def test_compact_restores_original_system_prompt() -> None:
    agent = ConcreteAgent(responses=["summary"])
    agent._history = make_history(4)
    await agent.compact()
    assert agent._system_prompt == _AGENT_SYSTEM_PROMPT


async def test_compact_restores_system_prompt_on_send_error() -> None:
    agent = ConcreteAgent(responses=[RuntimeError("api failure")])
    agent._history = make_history(4)
    with pytest.raises(RuntimeError):
        await agent.compact()
    assert agent._system_prompt == _AGENT_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# compact() — send() called with no tools
# ---------------------------------------------------------------------------


async def test_compact_send_uses_no_tools() -> None:
    agent = ConcreteAgent(responses=["summary"])
    agent._history = make_history(4)
    await agent.compact()
    assert agent.send_calls[0]["allowed_tools"] == []


# ---------------------------------------------------------------------------
# compact() — error leaves history unchanged
# ---------------------------------------------------------------------------


async def test_compact_leaves_history_unchanged_on_send_error() -> None:
    agent = ConcreteAgent(responses=[RuntimeError("api failure")])
    original_history = make_history(4)
    agent._history = list(original_history)
    with pytest.raises(RuntimeError):
        await agent.compact()
    assert agent._history == original_history


# ---------------------------------------------------------------------------
# compact() — return value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_messages", [0, 1, 2])
async def test_compact_returns_none_when_history_too_short(n_messages: int) -> None:
    agent = ConcreteAgent()
    agent._history = make_history(n_messages)
    result = await agent.compact()
    assert result is None


async def test_compact_returns_response_when_compaction_occurs() -> None:
    agent = ConcreteAgent(responses=["the summary"])
    agent._history = make_history(4)
    result = await agent.compact()
    assert result is not None
    assert result.text == "the summary"


# ---------------------------------------------------------------------------
# compact_preserving_last_turn() — guard: history too short
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_messages", [0, 1, 2, 3])
async def test_compact_preserving_last_turn_does_nothing_when_history_is_short(n_messages: int) -> None:
    agent = ConcreteAgent()
    agent._history = make_history(n_messages)
    await agent.compact_preserving_last_turn()
    assert len(agent.send_calls) == 0
    assert len(agent._history) == n_messages


# ---------------------------------------------------------------------------
# compact_preserving_last_turn() — collapses middle, keeps last two
# ---------------------------------------------------------------------------


async def test_compact_preserving_last_turn_keeps_last_two_messages() -> None:
    agent = ConcreteAgent(responses=["summary"])
    agent._history = make_history(6)
    last_two = agent._history[-2:]
    await agent.compact_preserving_last_turn()
    assert agent.history[-2:] == last_two


async def test_compact_preserving_last_turn_first_message_is_original_task() -> None:
    agent = ConcreteAgent(responses=["summary"])
    original = make_history(6)[0]
    agent._history = make_history(6)
    await agent.compact_preserving_last_turn()
    assert agent.history[0] == original


async def test_compact_preserving_last_turn_produces_four_messages() -> None:
    agent = ConcreteAgent(responses=["summary"])
    agent._history = make_history(6)
    await agent.compact_preserving_last_turn()
    # original + summary + last user + last assistant
    assert len(agent.history) == 4


# ---------------------------------------------------------------------------
# compact_preserving_last_turn() — error leaves history unchanged
# ---------------------------------------------------------------------------


async def test_compact_preserving_last_turn_leaves_history_unchanged_on_error() -> None:
    agent = ConcreteAgent(responses=[RuntimeError("api failure")])
    original_history = make_history(6)
    agent._history = list(original_history)
    with pytest.raises(RuntimeError):
        await agent.compact_preserving_last_turn()
    assert agent._history == original_history
