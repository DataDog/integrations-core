# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from anthropic.types import ToolParam

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.exceptions import AgentError
from ddev.ai.agent.scope import AgentScope
from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall, ToolResultMessage
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import AgentConfig
from ddev.ai.react.process import ReActProcess
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.tools.agents.spawn_subagent import SpawnSubagentInput, SpawnSubagentTool
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockAgent(BaseAgent[Any]):
    def __init__(self, responses: list[AgentResponse]) -> None:
        super().__init__("mock", "", ToolRegistry([]))
        self._responses = list(responses)
        self._index = 0

    async def send(
        self,
        content: str | list[ToolResultMessage],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse:
        response = self._responses[self._index]
        self._index += 1
        return response

    def reset(self) -> None:
        self._history = []

    async def compact(self) -> AgentResponse | None:
        return None

    async def compact_preserving_last_turn(self) -> AgentResponse | None:
        return None


class _RaisingAgent(BaseAgent[Any]):
    """Raises a fixed exception on every send() call."""

    def __init__(self, exc: BaseException) -> None:
        super().__init__("raising", "", ToolRegistry([]))
        self._exc = exc

    async def send(
        self,
        content: str | list[ToolResultMessage],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse:
        raise self._exc

    def reset(self) -> None:
        self._history = []

    async def compact(self) -> AgentResponse | None:
        return None

    async def compact_preserving_last_turn(self) -> AgentResponse | None:
        return None


class MockToolRegistry(ToolRegistry):
    def __init__(self, result: ToolResult | None = None) -> None:
        super().__init__([])
        self._result = result or ToolResult(success=True, data="ok")

    @property
    def definitions(self) -> list[ToolParam]:
        return []

    async def run(self, name: str, raw: dict[str, object]) -> ToolResult:
        return self._result


def make_response(
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
        tool_result: ToolResult | None = None,
        build_error: BaseException | None = None,
    ) -> None:
        self._root = root
        self._agent_factory = agent_factory or (lambda: MockAgent([make_response()]))
        self._tool_result = tool_result
        self._build_error = build_error
        self.callbacks = Callbacks([AgentLogger(root).as_callback_set()])
        self.calls: list[dict[str, Any]] = []

    def create(self, *, scope: AgentScope, agent_config: AgentConfig, system_prompt: str) -> ReActProcess:
        self.calls.append({"owner_id": scope.owner_id, "agent_config": agent_config, "system_prompt": system_prompt})
        if self._build_error is not None:
            raise self._build_error
        runtime = AgentRuntime(agent=self._agent_factory(), tool_registry=MockToolRegistry(self._tool_result))
        return ReActProcess(runtime, callbacks=self.callbacks, scope=scope)


def make_tool(
    factory: FakeProcessFactory,
    parent_tools: list[str] | None = None,
    owner_id: str = "parent",
    agent_config: AgentConfig | None = None,
) -> SpawnSubagentTool:
    return SpawnSubagentTool(
        owner_id=owner_id,
        agent_config=agent_config or AgentConfig(name="writer", tools=parent_tools or ["read_file", "edit_file"]),
        process_factory=factory,
    )


def subagent_log(root: Path, subagent_id: str) -> Path:
    return root / "subagent" / f"{subagent_id}.jsonl"


def read_events(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Input validation — fails before the child process is created
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tools,allowed,error_fragment",
    [
        (["spawn_subagent"], ["read_file"], "spawn further subagents"),
        (["read_file", "edit_file"], ["read_file"], "edit_file"),
    ],
    ids=["recursive", "disallowed"],
)
async def test_input_validation_fails_before_create(tmp_path, tools, allowed, error_fragment):
    factory = FakeProcessFactory(tmp_path, lambda: MockAgent([make_response()]))
    tool = make_tool(factory, parent_tools=allowed)
    result = await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=tools, name="x"))

    assert result.success is False
    assert error_fragment in result.error
    assert "x" in result.error
    assert factory.calls == []
    assert tool._counter == 0
    assert not (tmp_path / "subagent").exists()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected_id"),
    [
        ("worker", "parent.sub.001-worker"),
        (None, "parent.sub.001-unnamed"),
        ("", "parent.sub.001-unnamed"),
    ],
    ids=["named", "none", "empty"],
)
async def test_happy_path(tmp_path: Path, name: str | None, expected_id: str) -> None:
    factory = FakeProcessFactory(tmp_path, lambda: MockAgent([make_response(text="ok")]))
    tool = make_tool(factory)
    result = await tool(SpawnSubagentInput(system_prompt="sys", prompt="do it", tools=[], name=name))

    assert result.success is True
    assert result.data == "ok"
    assert result.total_input_tokens == 10
    assert result.total_output_tokens == 5
    assert factory.calls[0]["owner_id"] == expected_id

    events = read_events(subagent_log(tmp_path, expected_id))
    assert events[0]["event"] == "start"
    assert events[-1]["event"] == "finish"
    assert events[-1]["success"] is True


async def test_multi_iteration_wires_callbacks(tmp_path):
    """A subagent tool call produces a tool_call log event via the run-wide callbacks."""
    tool_call = ToolCall(id="tc1", name="read_file", input={"path": "/f"})
    factory = FakeProcessFactory(
        tmp_path,
        lambda: MockAgent(
            [make_response(stop_reason=StopReason.TOOL_USE, tool_calls=[tool_call]), make_response(text="done")]
        ),
        tool_result=ToolResult(success=True, data="content"),
    )
    tool = make_tool(factory, parent_tools=["read_file"])

    result = await tool(SpawnSubagentInput(system_prompt="sys", prompt="go", tools=["read_file"]))

    assert result.success is True
    assert result.data == "done"
    events = read_events(subagent_log(tmp_path, "parent.sub.001-unnamed"))
    assert "tool_call" in [e["event"] for e in events]


async def test_child_runtime_config_inherits_parent_settings_and_requested_tools(tmp_path):
    parent_config = AgentConfig(
        name="writer",
        provider="anthropic",
        tools=["read_file", "edit_file", "spawn_subagent"],
        model="custom-model",
        max_tokens=123,
    )
    factory = FakeProcessFactory(tmp_path, lambda: MockAgent([make_response(text="ok")]))
    tool = make_tool(
        factory,
        parent_tools=["read_file", "edit_file", "spawn_subagent"],
        agent_config=parent_config,
    )

    result = await tool(
        SpawnSubagentInput(system_prompt="child system", prompt="go", tools=["read_file"], name="child")
    )

    assert result.success is True
    call = factory.calls[0]
    child_config = call["agent_config"]
    assert isinstance(child_config, AgentConfig)
    assert child_config.provider == "anthropic"
    assert child_config.model == "custom-model"
    assert child_config.max_tokens == 123
    assert child_config.tools == ["read_file"]
    assert call["system_prompt"] == "child system"
    assert call["owner_id"] == "parent.sub.001-child"


async def test_max_tokens_response_prefixed(tmp_path):
    responses = [make_response(text="partial", stop_reason=StopReason.MAX_TOKENS)]
    factory = FakeProcessFactory(tmp_path, lambda: MockAgent(list(responses)))
    tool = make_tool(factory)
    result = await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="mt"))

    assert result.success is True
    assert result.data.startswith("[SUBAGENT HIT MAX_TOKENS — RESPONSE MAY BE TRUNCATED]")
    assert "partial" in result.data

    finish = next(e for e in read_events(subagent_log(tmp_path, "parent.sub.001-mt")) if e["event"] == "finish")
    assert finish["stop_reason"] == "max_tokens"


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


async def test_build_failure_returns_tool_result(tmp_path):
    factory = FakeProcessFactory(tmp_path, build_error=ValueError("boom"))
    tool = make_tool(factory)
    result = await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="fail"))

    assert result.success is False
    assert "fail" in result.error and "ValueError" in result.error and "boom" in result.error
    # create() raised before any process ran, so no child log exists.
    assert not subagent_log(tmp_path, "parent.sub.001-fail").exists()


async def test_react_process_failure(tmp_path):
    factory = FakeProcessFactory(tmp_path, lambda: _RaisingAgent(AgentError("rate limit")))
    tool = make_tool(factory)
    result = await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="rl"))

    assert result.success is False
    assert "rl" in result.error and "AgentError" in result.error

    events = read_events(subagent_log(tmp_path, "parent.sub.001-rl"))
    names = [e["event"] for e in events]
    assert "error" in names and "finish" in names
    assert names.index("error") < names.index("finish")
    assert next(e for e in events if e["event"] == "finish")["success"] is False


# ---------------------------------------------------------------------------
# Counter and unique subagent ids
# ---------------------------------------------------------------------------


async def test_counter_increments_per_invocation(tmp_path):
    factory = FakeProcessFactory(tmp_path, lambda: MockAgent([make_response(text="r")]))
    tool = make_tool(factory)

    await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="a"))
    await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="b"))

    assert subagent_log(tmp_path, "parent.sub.001-a").exists()
    assert subagent_log(tmp_path, "parent.sub.002-b").exists()


async def test_parallel_spawns_get_distinct_counters(tmp_path):
    factory = FakeProcessFactory(tmp_path, lambda: MockAgent([make_response(text="ok")]))
    tool = make_tool(factory)
    results = await asyncio.gather(
        *[tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name=n)) for n in ["x", "y", "z"]]
    )

    assert all(r.success for r in results)
    owner_ids = {c["owner_id"] for c in factory.calls}
    assert len(owner_ids) == 3
    assert len(list((tmp_path / "subagent").glob("*.jsonl"))) == 3
