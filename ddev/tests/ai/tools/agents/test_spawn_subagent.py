# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from ddev.ai.agent.exceptions import AgentError
from ddev.ai.agent.types import StopReason, ToolCall
from ddev.ai.phases.config import AgentConfig
from ddev.ai.tools.agents.spawn_subagent import SpawnSubagentInput, SpawnSubagentTool
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from pathlib import Path

    from tests.ai.conftest import FakeToolFactory
    from tests.ai.tools.agents.conftest import (
        FakeProcessFactory,
        MockAgent,
        ProcessFactoryBuilder,
        RaisingAgent,
        ReadEvents,
        ResponseFactory,
        SubagentLog,
    )


def make_tool(
    factory: FakeProcessFactory,
    parent_tools: list[str] | None = None,
    owner_id: str = "parent",
    agent_config: AgentConfig | None = None,
) -> SpawnSubagentTool:
    return SpawnSubagentTool(
        owner_id=owner_id,
        agent_config=agent_config or AgentConfig(tools=parent_tools or ["read_file", "edit_file"]),
        process_factory=factory,
    )


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
async def test_happy_path(
    process_factory: ProcessFactoryBuilder,
    mock_agent: type[MockAgent],
    make_response: ResponseFactory,
    subagent_log: SubagentLog,
    read_events: ReadEvents,
    name: str | None,
    expected_id: str,
):
    factory = process_factory(lambda: mock_agent([make_response(text="ok")]))
    result = await make_tool(factory)(SpawnSubagentInput(system_prompt="sys", prompt="do it", tools=[], name=name))

    assert result.success is True
    assert result.data == "ok"
    assert result.total_input_tokens == 10
    assert result.total_output_tokens == 5
    assert factory.calls[0]["owner_id"] == expected_id

    events = read_events(subagent_log(expected_id))
    assert events[0]["event"] == "start"
    assert events[-1]["event"] == "finish"
    assert events[-1]["success"] is True


async def test_multi_iteration_wires_callbacks(
    process_factory: ProcessFactoryBuilder,
    mock_agent: type[MockAgent],
    make_response: ResponseFactory,
    subagent_log: SubagentLog,
    read_events: ReadEvents,
    fake_tool: FakeToolFactory,
):
    """A subagent tool call produces a tool_call log event via the run-wide callbacks."""
    tool_call = ToolCall(id="tc1", name="read_file", input={"path": "/f"})
    factory = process_factory(
        lambda: mock_agent(
            [make_response(stop_reason=StopReason.TOOL_USE, tool_calls=[tool_call]), make_response(text="done")]
        ),
        tool_registry=ToolRegistry([fake_tool("read_file", result=ToolResult(success=True, data="content"))]),
    )
    result = await make_tool(factory, parent_tools=["read_file"])(
        SpawnSubagentInput(system_prompt="sys", prompt="go", tools=["read_file"])
    )

    assert result.success is True
    assert result.data == "done"
    events = read_events(subagent_log("parent.sub.001-unnamed"))
    assert "tool_call" in [e["event"] for e in events]


async def test_child_runtime_config_inherits_parent_settings_and_requested_tools(
    process_factory: ProcessFactoryBuilder, mock_agent: type[MockAgent], make_response: ResponseFactory
):
    parent_config = AgentConfig(
        provider="anthropic",
        tools=["read_file", "edit_file", "spawn_subagent"],
        model="custom-model",
        max_tokens=123,
    )
    factory = process_factory(lambda: mock_agent([make_response(text="ok")]))
    result = await make_tool(factory, agent_config=parent_config)(
        SpawnSubagentInput(system_prompt="child system", prompt="go", tools=["read_file"], name="child")
    )

    assert result.success is True
    child_config = factory.calls[0]["agent_config"]
    assert isinstance(child_config, AgentConfig)
    assert child_config.provider == "anthropic"
    assert child_config.model == "custom-model"
    assert child_config.max_tokens == 123
    assert child_config.tools == ["read_file"]
    assert factory.calls[0]["system_prompt"] == "child system"
    assert factory.calls[0]["owner_id"] == "parent.sub.001-child"


async def test_max_tokens_response_prefixed(
    process_factory: ProcessFactoryBuilder,
    mock_agent: type[MockAgent],
    make_response: ResponseFactory,
    subagent_log: SubagentLog,
    read_events: ReadEvents,
):
    factory = process_factory(lambda: mock_agent([make_response(text="partial", stop_reason=StopReason.MAX_TOKENS)]))
    result = await make_tool(factory)(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="mt"))

    assert result.success is True
    assert result.data.startswith("[SUBAGENT HIT MAX_TOKENS — RESPONSE MAY BE TRUNCATED]")
    assert "partial" in result.data

    finish = next(e for e in read_events(subagent_log("parent.sub.001-mt")) if e["event"] == "finish")
    assert finish["stop_reason"] == "max_tokens"


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


async def test_build_failure_returns_tool_result(process_factory: ProcessFactoryBuilder, subagent_log: SubagentLog):
    factory = process_factory(build_error=ValueError("boom"))
    result = await make_tool(factory)(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="fail"))

    assert result.success is False
    assert "fail" in result.error and "ValueError" in result.error and "boom" in result.error
    # create() raised before any process ran, so no child log exists.
    assert not subagent_log("parent.sub.001-fail").exists()


async def test_react_process_failure(
    process_factory: ProcessFactoryBuilder,
    raising_agent: type[RaisingAgent],
    subagent_log: SubagentLog,
    read_events: ReadEvents,
):
    factory = process_factory(lambda: raising_agent(AgentError("rate limit")))
    result = await make_tool(factory)(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="rl"))

    assert result.success is False
    assert "rl" in result.error and "AgentError" in result.error

    events = read_events(subagent_log("parent.sub.001-rl"))
    names = [e["event"] for e in events]
    assert "error" in names and "finish" in names
    assert names.index("error") < names.index("finish")
    assert next(e for e in events if e["event"] == "finish")["success"] is False


# ---------------------------------------------------------------------------
# Counter and unique subagent ids
# ---------------------------------------------------------------------------


async def test_counter_increments_per_invocation(
    process_factory: ProcessFactoryBuilder,
    mock_agent: type[MockAgent],
    make_response: ResponseFactory,
    subagent_log: SubagentLog,
):
    tool = make_tool(process_factory(lambda: mock_agent([make_response(text="r")])))

    await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="a"))
    await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="b"))

    assert subagent_log("parent.sub.001-a").exists()
    assert subagent_log("parent.sub.002-b").exists()


async def test_parallel_spawns_get_distinct_counters(
    tmp_path: Path,
    process_factory: ProcessFactoryBuilder,
    mock_agent: type[MockAgent],
    make_response: ResponseFactory,
):
    factory = process_factory(lambda: mock_agent([make_response(text="ok")]))
    tool = make_tool(factory)
    results = await asyncio.gather(
        *[tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name=n)) for n in ["x", "y", "z"]]
    )

    assert all(r.success for r in results)
    assert len({c["owner_id"] for c in factory.calls}) == 3
    assert len(list((tmp_path / "subagent").glob("*.jsonl"))) == 3
