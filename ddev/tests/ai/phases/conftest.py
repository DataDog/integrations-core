# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.types import AgentResponse, ContextUsage, StopReason, TokenUsage, ToolResultMessage
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.agentic_phase import AgenticPhase
from ddev.ai.phases.base import FlowContext
from ddev.ai.phases.config import AgentConfig, PhaseConfig, TaskConfig
from ddev.ai.runtime.checkpoints import CheckpointManager
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
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


class MockRuntimeFactory:
    """Minimal AgentRuntimeFactory that injects a MockAgent for testing."""

    def __init__(
        self,
        mock_agent: MockAgent,
        captured_kwargs: dict[str, Any] | None = None,
        goal_runtime_builder: Callable[[str], AgentRuntime] | None = None,
    ) -> None:
        self._mock_agent = mock_agent
        self._captured = captured_kwargs
        self._goal_runtime_builder = goal_runtime_builder

    def build_runtime(
        self,
        *,
        agent_config: AgentConfig,
        system_prompt: str,
        owner_id: str,
    ) -> AgentRuntime:
        if self._goal_runtime_builder is not None and ".goal." in owner_id:
            return self._goal_runtime_builder(owner_id)
        if self._captured is not None:
            self._captured["agent_config"] = agent_config
            self._captured["system_prompt"] = system_prompt
            self._captured["owner_id"] = owner_id
        self._mock_agent.name = owner_id
        self._mock_agent._system_prompt = system_prompt
        return AgentRuntime(agent=self._mock_agent, tool_registry=ToolRegistry([]))


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
    flow_variables: dict[str, str] | None = None,
    runtime_variables: dict[str, str] | None = None,
    context_compact_threshold_pct: int = 80,
    callbacks=None,
    captured_worker_kwargs: dict[str, Any] | None = None,
    goal_runtime_builder: Callable[[str], AgentRuntime] | None = None,
    agent_config: AgentConfig | None = None,
) -> tuple[AgenticPhase, CheckpointManager]:
    """Build an AgenticPhase ready for process_message-driven tests.

    Injects a MockRuntimeFactory so no real LLM or tools are constructed. Pass
    ``captured_worker_kwargs`` (a dict) to record build_runtime inputs.
    Pass ``goal_runtime_builder`` as a callable (owner_id: str) -> AgentRuntime for goal tests.
    """
    config = PhaseConfig(
        agent="writer",
        tasks=tasks or [TaskConfig(name="t1", prompt="Do the work.")],
        checkpoint=checkpoint,
        context_compact_threshold_pct=context_compact_threshold_pct,
    )
    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")
    context = FlowContext(
        runtime_variables=runtime_variables or {},
        flow_variables=flow_variables or {},
        config_dir=flow_dir,
        callbacks=callbacks or Callbacks(),
    )

    runtime_factory = MockRuntimeFactory(
        mock_agent=mock_agent,
        captured_kwargs=captured_worker_kwargs,
        goal_runtime_builder=goal_runtime_builder,
    )
    phase = AgenticPhase(
        phase_id=phase_id,
        dependencies=dependencies or [],
        config=config,
        checkpoint_manager=checkpoint_manager,
        context=context,
        agent_config=agent_config or AgentConfig(tools=[]),
        runtime_factory=runtime_factory,
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
def flow_context(flow_dir):
    return FlowContext(
        runtime_variables={},
        flow_variables={},
        config_dir=flow_dir,
    )


@pytest.fixture
def message_queue():
    """An asyncio.Queue that can be attached to a Phase for submit_message."""
    return asyncio.Queue()


@pytest.fixture
def file_access_policy(tmp_path) -> FileAccessPolicy:
    return FileAccessPolicy(write_root=tmp_path)
