# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from ddev.ai.agent.types import StopReason
from ddev.ai.phases.config import AgentConfig
from ddev.ai.tools.agents.spawn_identical_subagents import (
    CONCISE_DIRECTIVE,
    Assignment,
    SpawnIdenticalSubagentsInput,
    SpawnIdenticalSubagentsTool,
)

if TYPE_CHECKING:
    from tests.ai.tools.agents.conftest import (
        FakeProcessFactory,
        MockAgent,
        ProcessFactoryBuilder,
        RaisingAgent,
        ResponseFactory,
    )


def make_tool(
    factory: FakeProcessFactory, parent_tools: list[str] | None = None, owner_id: str = "parent"
) -> SpawnIdenticalSubagentsTool:
    return SpawnIdenticalSubagentsTool(
        owner_id=owner_id,
        agent_config=AgentConfig(tools=parent_tools or ["read_file", "edit_file"]),
        process_factory=factory,
    )


def assignments(*names: str) -> list[Assignment]:
    return [Assignment(name=n, prompt=f"do {n}") for n in names]


async def test_duplicate_names_rejected(process_factory: ProcessFactoryBuilder):
    factory = process_factory()
    result = await make_tool(factory)(
        SpawnIdenticalSubagentsInput(system_prompt="s", assignments=assignments("a", "a"))
    )
    assert result.success is False
    assert "unique" in result.error
    assert factory.calls == []


async def test_over_cap_rejected(process_factory: ProcessFactoryBuilder):
    factory = process_factory()
    result = await make_tool(factory)(
        SpawnIdenticalSubagentsInput(system_prompt="s", assignments=assignments(*[f"a{i}" for i in range(33)]))
    )
    assert result.success is False
    assert "Too many" in result.error
    assert factory.calls == []


async def test_happy_path(
    process_factory: ProcessFactoryBuilder, mock_agent: type[MockAgent], make_response: ResponseFactory
):
    factory = process_factory(lambda: mock_agent([make_response(text="done")]))
    result = await make_tool(factory)(
        SpawnIdenticalSubagentsInput(system_prompt="sys", tools=["read_file"], assignments=assignments("a", "b", "c"))
    )
    assert result.success is True
    assert result.total_input_tokens == 30
    assert result.total_output_tokens == 15
    assert all(
        c["system_prompt"].startswith("sys\n\n") and CONCISE_DIRECTIVE in c["system_prompt"] for c in factory.calls
    )
    assert all(c["agent_config"].tools == ["read_file"] for c in factory.calls)
    assert [c["owner_id"] for c in factory.calls] == [
        "parent.par.001.000-a",
        "parent.par.001.001-b",
        "parent.par.001.002-c",
    ]
    assert result.data.index("## a") < result.data.index("## b") < result.data.index("## c")


async def test_repeated_calls_produce_distinct_owner_ids(
    process_factory: ProcessFactoryBuilder, mock_agent: type[MockAgent], make_response: ResponseFactory
):
    factory = process_factory(lambda: mock_agent([make_response(text="done")]))
    tool = make_tool(factory)
    tool_input = SpawnIdenticalSubagentsInput(system_prompt="sys", assignments=assignments("a"))

    await tool(tool_input)
    await tool(tool_input)

    owner_ids = [c["owner_id"] for c in factory.calls]
    assert owner_ids == ["parent.par.001.000-a", "parent.par.002.000-a"]


async def test_partial_failure(
    process_factory: ProcessFactoryBuilder,
    mock_agent: type[MockAgent],
    raising_agent: type[RaisingAgent],
    make_response: ResponseFactory,
):
    def agent_factory():
        agent_factory.n += 1
        if agent_factory.n == 2:
            return raising_agent(RuntimeError("boom"))
        return mock_agent([make_response(text="ok")])

    agent_factory.n = 0
    result = await make_tool(process_factory(agent_factory))(
        SpawnIdenticalSubagentsInput(system_prompt="s", assignments=assignments("a", "b", "c"))
    )
    assert result.success is True
    assert "FAILED" in result.data
    assert result.data.count("— ok") == 2


async def test_all_fail(process_factory: ProcessFactoryBuilder, raising_agent: type[RaisingAgent]):
    factory = process_factory(lambda: raising_agent(RuntimeError("boom")))
    result = await make_tool(factory)(
        SpawnIdenticalSubagentsInput(system_prompt="s", assignments=assignments("a", "b"))
    )
    assert result.success is False
    assert result.error == "All children failed."


async def test_max_tokens_notice(
    process_factory: ProcessFactoryBuilder, mock_agent: type[MockAgent], make_response: ResponseFactory
):
    factory = process_factory(lambda: mock_agent([make_response(text="partial", stop_reason=StopReason.MAX_TOKENS)]))
    result = await make_tool(factory)(SpawnIdenticalSubagentsInput(system_prompt="s", assignments=assignments("a")))
    assert result.success is True
    assert "TRUNCATED (max_tokens)" in result.data
    assert "SUBAGENT HIT MAX_TOKENS" in result.data


async def test_max_parallel_respected(
    process_factory: ProcessFactoryBuilder, mock_agent: type[MockAgent], make_response: ResponseFactory
):
    active = 0
    peak = 0

    class CountingAgent(mock_agent):
        def __init__(self):
            super().__init__([make_response(text="ok")])

        async def send(self, content, allowed_tools=None):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return await super().send(content, allowed_tools)

    factory = process_factory(CountingAgent)
    result = await make_tool(factory)(
        SpawnIdenticalSubagentsInput(
            system_prompt="s", max_parallel=2, assignments=assignments(*[f"a{i}" for i in range(6)])
        )
    )
    assert result.success is True
    assert peak <= 2
