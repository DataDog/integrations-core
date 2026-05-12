# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from ddev.ai.agent.types import AgentResponse, ContextUsage, StopReason, TokenUsage, ToolResultMessage
from ddev.ai.phases.agentic_phase import AgenticPhase
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, PhaseConfig, TaskConfig
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry

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


def make_agent_factory(mock_agent: MockAgent, captured_kwargs: dict[str, Any] | None = None):
    """Create a callable that replaces AnthropicAgent constructor, returning the given mock.

    If ``captured_kwargs`` is provided, every call updates it with the kwargs passed to
    the constructor — useful for asserting on system_prompt, tools, etc.
    """

    def factory(**kwargs: Any) -> MockAgent:
        if captured_kwargs is not None:
            captured_kwargs.update(kwargs)
        mock_agent.name = kwargs.get("name", "mock")
        return mock_agent

    return factory


def _empty_registry_from_names(cls, names, *, owner_id, file_registry):
    return ToolRegistry([])


def make_agent_phase(
    flow_dir,
    mock_agent: MockAgent,
    monkeypatch,
    message_queue,
    *,
    phase_id: str = "p1",
    dependencies: list[str] | None = None,
    tasks: list[TaskConfig] | None = None,
    checkpoint=None,
    agent_tools: list[str] | None = None,
    flow_variables: dict[str, str] | None = None,
    runtime_variables: dict[str, str] | None = None,
    context_compact_threshold_pct: int = 80,
    callbacks=None,
    captured_agent_kwargs: dict[str, Any] | None = None,
) -> tuple[AgenticPhase, CheckpointManager]:
    """Build an AgenticPhase ready for process_message-driven tests.

    Patches ``AnthropicAgent`` and ``ToolRegistry.from_names`` so no real LLM or tools
    are constructed. Pass ``captured_agent_kwargs`` (a dict) to record AnthropicAgent
    constructor kwargs across calls (e.g. to inspect system_prompt rendering).
    """
    monkeypatch.setattr(
        "ddev.ai.phases.agentic_phase.AnthropicAgent",
        make_agent_factory(mock_agent, captured_agent_kwargs),
    )
    monkeypatch.setattr(ToolRegistry, "from_names", classmethod(_empty_registry_from_names))

    config = PhaseConfig(
        agent="writer",
        tasks=tasks or [TaskConfig(name="t1", prompt="Do the work.")],
        checkpoint=checkpoint,
        context_compact_threshold_pct=context_compact_threshold_pct,
    )
    agent_config = AgentConfig(tools=agent_tools or [])
    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")

    phase = AgenticPhase(
        phase_id=phase_id,
        dependencies=dependencies or [],
        config=config,
        agent_config=agent_config,
        anthropic_client=MagicMock(),
        checkpoint_manager=checkpoint_manager,
        runtime_variables=runtime_variables or {},
        flow_variables=flow_variables or {},
        config_dir=flow_dir,
        file_registry=FileRegistry(policy=FileAccessPolicy(write_root=flow_dir)),
        callbacks=callbacks,
    )
    phase.queue = message_queue
    return phase, checkpoint_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def resolve_key(key: str) -> str:
    """Resolver that wraps a key in 'resolved(...)' for use in template tests."""
    return f"resolved({key})"


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


@pytest.fixture
def file_access_policy(tmp_path) -> FileAccessPolicy:
    return FileAccessPolicy(write_root=tmp_path)
