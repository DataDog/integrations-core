# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from collections.abc import Callable
from typing import Any

from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.agent.types import AgentResponse, ContextUsage, StopReason, TokenUsage, ToolResultMessage
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import AgentConfig, PhaseConfig, TaskConfig
from ddev.ai.phases.agentic_phase import AgenticPhase
from ddev.ai.phases.base import FlowContext
from ddev.ai.react.process import ReActProcess
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.runtime.checkpoints import CheckpointManager
from ddev.ai.tools.registry import ToolRegistry
from tests.ai.config.utils import make_agent_config


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


def make_goal_verdict(
    valid: bool,
    reason: str = "",
    findings: list[dict[str, str]] | None = None,
) -> str:
    """Return a valid structured goal-review verdict."""
    effective_findings = findings
    if effective_findings is None:
        effective_findings = [] if valid else [{"id": "finding", "criterion": "goal", "reason": reason}]
    return json.dumps({"valid": valid, "reason": reason, "findings": effective_findings})


class MockAgent:
    """Agent mock that replays a fixed list of responses."""

    def __init__(self, responses: list[AgentResponse]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.send_calls: list[str | list[ToolResultMessage]] = []
        self.compact_call_count: int = 0
        self.reset_call_count: int = 0
        self.name = "mock"
        self._system_prompt = ""
        self._history: list[Any] = []

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

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
        self.reset_call_count += 1

    async def compact(self) -> AgentResponse | None:
        self.compact_call_count += 1
        return None

    async def compact_preserving_last_turn(self) -> AgentResponse | None:
        self.compact_call_count += 1
        return None


class MockProcessFactory:
    """Minimal ReActProcessFactory that wraps a MockAgent in a ReActProcess."""

    def __init__(
        self,
        mock_agent: MockAgent,
        callbacks: Callbacks,
        captured_kwargs: dict[str, Any] | None = None,
        goal_runtime_builder: Callable[[str], AgentRuntime] | None = None,
    ) -> None:
        self._mock_agent = mock_agent
        self._callbacks = callbacks
        self._captured = captured_kwargs
        self._goal_runtime_builder = goal_runtime_builder

    def create(self, *, scope: AgentScope, agent_config: AgentConfig, system_prompt: str) -> ReActProcess:
        if self._goal_runtime_builder is not None and scope.role == AgentRole.GOAL_REVIEWER:
            runtime = self._goal_runtime_builder(scope.owner_id)
        else:
            if self._captured is not None:
                self._captured["agent_config"] = agent_config
                self._captured["system_prompt"] = system_prompt
                self._captured["owner_id"] = scope.owner_id
            self._mock_agent.name = scope.owner_id
            self._mock_agent._system_prompt = system_prompt
            runtime = AgentRuntime(agent=self._mock_agent, tool_registry=ToolRegistry([]))
        return ReActProcess(runtime, callbacks=self._callbacks, scope=scope)


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
    resume_frontier: frozenset[str] = frozenset(),
    phase_cls: type[AgenticPhase] = AgenticPhase,
    phase_kwargs: dict[str, Any] | None = None,
) -> tuple[AgenticPhase, CheckpointManager]:
    """Build an AgenticPhase ready for process_message-driven tests."""
    effective_agent_config = agent_config or make_agent_config(tools=[])
    config = PhaseConfig(
        name=phase_id,
        agent="writer",
        tasks=tasks or [TaskConfig(name="t1", prompt="Do the work.")],
        checkpoint=checkpoint,
        context_compact_threshold_pct=context_compact_threshold_pct,
    )
    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")
    run_logger = AgentLogger(checkpoint_manager.root)
    effective_callbacks = (callbacks or Callbacks()).with_set(run_logger.as_callback_set())
    context = FlowContext(
        runtime_variables=runtime_variables or {},
        flow_variables=flow_variables or {},
        callbacks=effective_callbacks,
        resume_frontier=resume_frontier,
    )

    process_factory = MockProcessFactory(
        mock_agent=mock_agent,
        callbacks=effective_callbacks,
        captured_kwargs=captured_worker_kwargs,
        goal_runtime_builder=goal_runtime_builder,
    )
    phase = phase_cls(
        phase_id=phase_id,
        dependencies=dependencies or [],
        config=config,
        checkpoint_manager=checkpoint_manager,
        context=context,
        agent_config=effective_agent_config,
        process_factory=process_factory,
        **(phase_kwargs or {}),
    )
    phase.queue = message_queue
    return phase, checkpoint_manager


def resolve_key(key: str) -> str:
    """Resolver that wraps a key in 'resolved(...)' for use in template tests."""
    return f"resolved({key})"
