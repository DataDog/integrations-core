# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Shared doubles for the spawn-tool tests: fake agents and a fake ReActProcessFactory.

Use the `mock_agent`, `raising_agent`, `make_response`, and `process_factory` fixtures rather than
importing the classes below directly.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.scope import AgentScope
from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall, ToolResultMessage
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.config import AgentConfig
from ddev.ai.react.process import ReActProcess
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.tools.registry import ToolRegistry


class MockAgent(BaseAgent[Any]):
    """Replays a fixed list of responses, one per send()."""

    def __init__(self, responses: list[AgentResponse]):
        super().__init__("mock", "", ToolRegistry([]))
        self._responses = list(responses)
        self._index = 0

    async def send(
        self, content: str | list[ToolResultMessage], allowed_tools: list[str] | None = None
    ) -> AgentResponse:
        response = self._responses[self._index]
        self._index += 1
        return response

    def reset(self):
        self._history = []

    async def compact(self) -> AgentResponse | None:
        return None

    async def compact_preserving_last_turn(self) -> AgentResponse | None:
        return None


class RaisingAgent(MockAgent):
    """Raises a fixed exception on every send() call."""

    def __init__(self, exc: BaseException):
        super().__init__([])
        self._exc = exc

    async def send(
        self, content: str | list[ToolResultMessage], allowed_tools: list[str] | None = None
    ) -> AgentResponse:
        raise self._exc


def _make_response(
    text: str = "",
    stop_reason: StopReason = StopReason.END_TURN,
    tool_calls: list[ToolCall] | None = None,
) -> AgentResponse:
    return AgentResponse(
        stop_reason=stop_reason,
        text=text,
        tool_calls=tool_calls or [],
        usage=TokenUsage(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0),
    )


class FakeProcessFactory:
    """Stand-in ReActProcessFactory that records create() calls and wires child
    processes to an AgentLogger rooted at ``root`` so logging can be asserted."""

    def __init__(
        self,
        root: Path,
        agent_factory=None,
        tool_registry: ToolRegistry | None = None,
        build_error: BaseException | None = None,
    ):
        self._agent_factory = agent_factory or (lambda: MockAgent([_make_response()]))
        self._tool_registry = tool_registry or ToolRegistry([])
        self._build_error = build_error
        self.callbacks = Callbacks([AgentLogger(root).as_callback_set()])
        self.calls: list[dict[str, Any]] = []

    def create(self, *, scope: AgentScope, agent_config: AgentConfig, system_prompt: str) -> ReActProcess:
        self.calls.append({"owner_id": scope.owner_id, "agent_config": agent_config, "system_prompt": system_prompt})
        if self._build_error is not None:
            raise self._build_error
        runtime = AgentRuntime(agent=self._agent_factory(), tool_registry=self._tool_registry)
        return ReActProcess(runtime, callbacks=self.callbacks, scope=scope)


ResponseFactory = Callable[..., AgentResponse]
ProcessFactoryBuilder = Callable[..., FakeProcessFactory]
SubagentLog = Callable[[str], Path]
ReadEvents = Callable[[Path], list[dict]]


@pytest.fixture
def mock_agent() -> type[MockAgent]:
    return MockAgent


@pytest.fixture
def raising_agent() -> type[RaisingAgent]:
    return RaisingAgent


@pytest.fixture
def make_response() -> ResponseFactory:
    return _make_response


@pytest.fixture
def process_factory(tmp_path: Path) -> ProcessFactoryBuilder:
    def build(agent_factory=None, tool_registry=None, build_error=None) -> FakeProcessFactory:
        return FakeProcessFactory(tmp_path, agent_factory, tool_registry, build_error)

    return build


@pytest.fixture
def subagent_log(tmp_path: Path) -> SubagentLog:
    def path(subagent_id: str) -> Path:
        return tmp_path / "subagent" / f"{subagent_id}.jsonl"

    return path


@pytest.fixture
def read_events() -> ReadEvents:
    def read(log_path: Path) -> list[dict]:
        return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    return read
