# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from typing import Any

import pytest

from ddev.ai.agent.types import AgentResponse, ContextUsage, StopReason, TokenUsage, ToolResultMessage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_response(
    text: str = "",
    input_tokens: int = 100,
    output_tokens: int = 50,
    context_pct: float | None = None,
    stop_reason: StopReason = StopReason.END_TURN,
) -> AgentResponse:
    context_usage = None
    if context_pct is not None:
        context_usage = ContextUsage(window_size=100_000, used_tokens=int(100_000 * context_pct / 100))
    return AgentResponse(
        stop_reason=stop_reason,
        text=text,
        tool_calls=[],
        usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            context_usage=context_usage,
        ),
    )


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockAgent:
    """Agent mock that replays a fixed list of responses.

    Used via monkeypatch to replace AnthropicAgent in Phase tests.
    """

    def __init__(self, responses: list[AgentResponse]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.send_calls: list[str | list[ToolResultMessage]] = []
        self.compact_call_count: int = 0
        self.name = "mock"
        self._history: list[Any] = []

    async def send(
        self,
        content: str | list[ToolResultMessage],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse:
        self.send_calls.append(content)
        response = self._responses[self._index]
        self._index += 1
        return response

    def reset(self) -> None:
        self._history = []

    async def compact(self) -> AgentResponse | None:
        self.compact_call_count += 1
        return None

    async def compact_preserving_last_turn(self) -> AgentResponse | None:
        self.compact_call_count += 1
        return None


def make_agent_factory(mock_agent: MockAgent):
    """Create a callable that replaces AnthropicAgent constructor, returning the given mock."""

    def factory(**kwargs: Any) -> MockAgent:
        mock_agent.name = kwargs.get("name", "mock")
        return mock_agent

    return factory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def resolve_key(key: str) -> str:
    """Resolver that wraps a key in 'resolved(...)' for use in template tests."""
    return f"resolved({key})"


@pytest.fixture(autouse=True)
def _clean_phase_registry():
    """Reset PhaseRegistry before each test to avoid cross-contamination."""
    from ddev.ai.phases.base import PhaseRegistry

    original = dict(PhaseRegistry._registry)
    PhaseRegistry._registry.clear()
    yield
    PhaseRegistry._registry.clear()
    PhaseRegistry._registry.update(original)


@pytest.fixture
def flow_dir(tmp_path):
    """Create a minimal flow directory with a system prompt."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "writer.md").write_text("You are a writer for ${phase_name}.")
    return tmp_path


@pytest.fixture
def message_queue():
    """An asyncio.Queue that can be attached to a Phase for submit_message."""
    return asyncio.Queue()
