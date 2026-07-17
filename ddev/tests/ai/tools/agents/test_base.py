# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.tools.agents.base import SPAWN_IDENTICAL_NAME, SPAWN_SUBAGENT_NAME, BaseSpawnTool
from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult
from tests.ai.config.utils import make_agent_config


class _ConcreteSpawnTool(BaseSpawnTool):
    @property
    def name(self) -> str:
        return "concrete"

    async def __call__(self, tool_input: BaseToolInput) -> ToolResult:
        return ToolResult(success=True)


def make_tool(tools: list[str]) -> _ConcreteSpawnTool:
    return _ConcreteSpawnTool(
        parent_scope=AgentScope(owner_id="p", role=AgentRole.PHASE, phase_id="p"),
        agent_config=make_agent_config(tools=tools),
        process_factory=None,
    )


def test_allowed_tools_excludes_both_spawn_tools():
    tool = make_tool(["read_file", "edit_file", SPAWN_SUBAGENT_NAME, SPAWN_IDENTICAL_NAME])
    assert tool._allowed_tools == {"read_file", "edit_file"}


@pytest.mark.parametrize(
    "requested,fragment",
    [
        ([SPAWN_SUBAGENT_NAME], "spawn further"),
        ([SPAWN_IDENTICAL_NAME], "spawn further"),
        (["edit_file"], "disallowed"),
        (["read_file"], None),
    ],
)
def test_validate_tools(requested: list[str], fragment: str | None):
    error = make_tool(["read_file"])._validate_tools(requested, "child")
    if fragment is None:
        assert error is None
    else:
        assert fragment in error
