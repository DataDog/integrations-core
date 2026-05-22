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
from ddev.ai.agent.build import SubagentBuilder
from ddev.ai.agent.exceptions import AgentError
from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall, ToolResultMessage
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


def make_builder(responses: list[AgentResponse], tool_result: ToolResult | None = None) -> SubagentBuilder:
    """Return a builder closure that replays fixed responses."""
    tr = tool_result or ToolResult(success=True, data="ok")

    def builder(system_prompt: str, owner_id: str, tool_names: list[str]) -> tuple[BaseAgent[Any], ToolRegistry]:
        return MockAgent(list(responses)), MockToolRegistry(tr)

    return builder


def make_tool(
    log_dir: Path,
    builder: SubagentBuilder,
    allowed_tools: list[str] | None = None,
    owner_id: str = "parent",
) -> SpawnSubagentTool:
    return SpawnSubagentTool(
        owner_id=owner_id,
        subagent_builder=builder,
        allowed_tools=allowed_tools if allowed_tools is not None else ["read_file", "edit_file"],
        log_dir=log_dir,
    )


def read_events(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Input validation — fails before any log file is opened
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tools,allowed,error_fragment",
    [
        (["spawn_subagent"], ["read_file"], "spawn further subagents"),
        (["read_file", "edit_file"], ["read_file"], "edit_file"),
    ],
    ids=["recursive", "disallowed"],
)
async def test_input_validation_fails_before_logging(tmp_path, tools, allowed, error_fragment):
    tool = make_tool(tmp_path, make_builder([make_response()]), allowed_tools=allowed)
    result = await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=tools, name="x"))

    assert result.success is False
    assert error_fragment in result.error
    assert "x" in result.error
    assert list(tmp_path.glob("*.jsonl")) == []
    assert tool._counter == 0


# ---------------------------------------------------------------------------
# mkdir failure — after validation, before counter advances
# ---------------------------------------------------------------------------


async def test_mkdir_failure(tmp_path):
    blocker = tmp_path / "blocked"
    blocker.write_text("I am a file")
    log_dir = blocker / "subagents"

    tool = make_tool(log_dir, make_builder([make_response()]))
    result = await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="x"))

    assert result.success is False
    assert "x" in result.error
    assert str(log_dir) in result.error
    assert tool._counter == 0


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected_log_name"),
    [
        ("worker", "001-worker.jsonl"),
        (None, "001-unnamed.jsonl"),
        ("", "001-unnamed.jsonl"),
    ],
    ids=["named", "none", "empty"],
)
async def test_happy_path(tmp_path: Path, name: str | None, expected_log_name: str) -> None:
    tool = make_tool(tmp_path, make_builder([make_response(text="ok")]))
    result = await tool(SpawnSubagentInput(system_prompt="sys", prompt="do it", tools=[], name=name))

    assert result.success is True
    assert result.data == "ok"

    events = read_events(tmp_path / expected_log_name)
    assert events[0]["event"] == "start"
    assert events[-1]["event"] == "finish"
    assert events[-1]["success"] is True


async def test_multi_iteration_wires_callbacks(tmp_path):
    """Proves AgentLogger callbacks are wired: a subagent tool call produces a tool_call log event."""
    tool_call = ToolCall(id="tc1", name="read_file", input={"path": "/f"})
    tool = make_tool(
        tmp_path,
        make_builder(
            [make_response(stop_reason=StopReason.TOOL_USE, tool_calls=[tool_call]), make_response(text="done")],
            tool_result=ToolResult(success=True, data="content"),
        ),
        allowed_tools=["read_file"],
    )

    result = await tool(SpawnSubagentInput(system_prompt="sys", prompt="go", tools=["read_file"]))

    assert result.success is True
    assert result.data == "done"
    assert "tool_call" in [e["event"] for e in read_events(tmp_path / "001-unnamed.jsonl")]


async def test_max_tokens_response_prefixed(tmp_path):
    tool = make_tool(tmp_path, make_builder([make_response(text="partial", stop_reason=StopReason.MAX_TOKENS)]))
    result = await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="mt"))

    assert result.success is True
    assert result.data.startswith("[SUBAGENT HIT MAX_TOKENS — RESPONSE MAY BE TRUNCATED]")
    assert "partial" in result.data

    finish = next(e for e in read_events(tmp_path / "001-mt.jsonl") if e["event"] == "finish")
    assert finish["stop_reason"] == "max_tokens"


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


async def test_builder_failure(tmp_path):
    def failing_builder(
        system_prompt: str,
        owner_id: str,
        tool_names: list[str],
    ) -> tuple[BaseAgent[Any], ToolRegistry]:
        raise ValueError("boom")

    tool = SpawnSubagentTool(owner_id="parent", subagent_builder=failing_builder, allowed_tools=[], log_dir=tmp_path)
    result = await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="fail"))

    assert result.success is False
    assert "fail" in result.error and "ValueError" in result.error and "boom" in result.error

    events = read_events(tmp_path / "001-fail.jsonl")
    assert [e["event"] for e in events] == ["start", "finish"]
    assert events[-1]["success"] is False


async def test_react_process_failure(tmp_path):
    def builder(
        system_prompt: str,
        owner_id: str,
        tool_names: list[str],
    ) -> tuple[BaseAgent[Any], ToolRegistry]:
        return _RaisingAgent(AgentError("rate limit")), MockToolRegistry()

    tool = make_tool(tmp_path, builder)
    result = await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="rl"))

    assert result.success is False
    assert "rl" in result.error and "AgentError" in result.error

    names = [e["event"] for e in read_events(tmp_path / "001-rl.jsonl")]
    assert "error" in names and "finish" in names
    assert names.index("error") < names.index("finish")
    assert next(e for e in read_events(tmp_path / "001-rl.jsonl") if e["event"] == "finish")["success"] is False


async def test_finally_close_runs_on_base_exception(tmp_path):
    """KeyboardInterrupt propagates but logger.close() still runs via finally."""

    def builder(
        system_prompt: str,
        owner_id: str,
        tool_names: list[str],
    ) -> tuple[BaseAgent[Any], ToolRegistry]:
        return _RaisingAgent(KeyboardInterrupt()), MockToolRegistry()

    tool = make_tool(tmp_path, builder)

    with pytest.raises(KeyboardInterrupt):
        await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="ki"))

    names = [e["event"] for e in read_events(tmp_path / "001-ki.jsonl")]
    assert "error" in names
    assert "finish" not in names


# ---------------------------------------------------------------------------
# Counter and log file naming
# ---------------------------------------------------------------------------


async def test_counter_increments_per_invocation(tmp_path):
    tool = make_tool(tmp_path, make_builder([make_response(text="r1"), make_response(text="r2")]))

    await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="a"))
    await tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name="b"))

    assert (tmp_path / "001-a.jsonl").exists()
    assert (tmp_path / "002-b.jsonl").exists()


async def test_parallel_spawns_get_distinct_counters(tmp_path):
    owner_ids: list[str] = []

    def recording_builder(
        system_prompt: str,
        owner_id: str,
        tool_names: list[str],
    ) -> tuple[BaseAgent[Any], ToolRegistry]:
        owner_ids.append(owner_id)
        return MockAgent([make_response(text="ok")]), MockToolRegistry()

    tool = SpawnSubagentTool(owner_id="parent", subagent_builder=recording_builder, allowed_tools=[], log_dir=tmp_path)
    results = await asyncio.gather(
        *[tool(SpawnSubagentInput(system_prompt="s", prompt="p", tools=[], name=n)) for n in ["x", "y", "z"]]
    )

    assert all(r.success for r in results)
    assert len(list(tmp_path.glob("*.jsonl"))) == 3
    assert len(set(owner_ids)) == 3


# ---------------------------------------------------------------------------
# Pydantic input validation (via BaseTool.run)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        {"prompt": "x"},
        {"system_prompt": "s", "prompt": "p", "tools": [], "bad_field": True},
        {"system_prompt": "s", "prompt": "p", "tools": [], "name": "../oops"},
    ],
    ids=["missing_field", "extra_field", "unsafe_name"],
)
async def test_pydantic_rejects_invalid_input(raw: dict[str, object]) -> None:
    tool = SpawnSubagentTool(
        owner_id="p",
        subagent_builder=make_builder([make_response()]),
        allowed_tools=[],
        log_dir=Path("/tmp"),
    )
    result = await tool.run(raw)
    assert result.success is False
