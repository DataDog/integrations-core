# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.agents.spawn_identical_subagents import SpawnIdenticalSubagentsTool
from ddev.ai.tools.agents.spawn_subagent import SpawnSubagentTool
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import NATIVE_TOOL_NAMES, ToolRegistry, filter_read_only
from tests.ai.config.utils import make_agent_config

if TYPE_CHECKING:
    from tests.ai.conftest import FakeToolFactory

# ---------------------------------------------------------------------------
# ToolRegistry.__init__
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "names,expected_names",
    [
        (["alpha"], {"alpha"}),
        ([], set()),
        (["a", "b", "c"], {"a", "b", "c"}),
    ],
)
def test_registry_registers_tools(names: list[str], expected_names: set[str], fake_tool: FakeToolFactory) -> None:
    registry = ToolRegistry([fake_tool(n) for n in names])
    assert set(registry._tools.keys()) == expected_names


def test_duplicate_name_last_one_wins(fake_tool: FakeToolFactory) -> None:
    # This design is intentional to allow for tool overrides.
    first = fake_tool("dup")
    second = fake_tool("dup")
    registry = ToolRegistry([first, second])
    assert registry._tools["dup"] is second


# ---------------------------------------------------------------------------
# ToolRegistry.definitions
# ---------------------------------------------------------------------------


def test_empty_registry_returns_empty_list():
    assert ToolRegistry([]).definitions == []


def test_tool_registry_definitions_returns_all_tool_definitions(fake_tool: FakeToolFactory) -> None:
    registry = ToolRegistry([fake_tool("a"), fake_tool("b")])
    assert len(registry.definitions) == 2


def test_definition_contains_tool_name(fake_tool: FakeToolFactory) -> None:
    registry = ToolRegistry([fake_tool("mytool")])
    assert registry.definitions[0]["name"] == "mytool"


# ---------------------------------------------------------------------------
# ToolRegistry.run
# ---------------------------------------------------------------------------


async def test_run_dispatches_to_correct_tool(fake_tool: FakeToolFactory) -> None:
    tool_a = fake_tool("a", ToolResult(success=True, data="from a"))
    tool_b = fake_tool("b", ToolResult(success=True, data="from b"))
    registry = ToolRegistry([tool_a, tool_b])

    result = await registry.run("b", {})
    assert result.success is True
    assert result.data == "from b"


async def test_passes_raw_dict_to_tool_unchanged(fake_tool: FakeToolFactory) -> None:
    tool = fake_tool("t")
    registry = ToolRegistry([tool])
    raw = {"key": "value", "num": 42}

    await registry.run("t", raw)
    assert tool.calls == [raw]


async def test_returns_tool_result_on_tool_failure(fake_tool: FakeToolFactory) -> None:
    registry = ToolRegistry([fake_tool("t", ToolResult(success=False, error="bad input"))])
    result = await registry.run("t", {})
    assert result.success is False
    assert result.error == "bad input"


async def test_unknown_tool_returns_failure(fake_tool: FakeToolFactory) -> None:
    registry = ToolRegistry([fake_tool("known_tool")])
    result = await registry.run("unknown_tool", {})
    assert result.success is False
    assert "Unknown tool: 'unknown_tool'" in result.error


async def test_empty_registry_always_returns_unknown_error():
    registry = ToolRegistry([])
    result = await registry.run("anything", {})
    assert result.success is False
    assert result.error is not None


# ---------------------------------------------------------------------------
# ToolRegistry.get
# ---------------------------------------------------------------------------


def test_get_returns_registered_tool_by_name(fake_tool: FakeToolFactory) -> None:
    tool = fake_tool("edit_file", truncated_call_hint="shrink the edit")
    registry = ToolRegistry([tool])

    found = registry.get("edit_file")

    assert found is tool
    assert found.truncated_call_hint == "shrink the edit"


def test_get_returns_none_for_unknown_tool(fake_tool: FakeToolFactory) -> None:
    registry = ToolRegistry([fake_tool("edit_file")])
    assert registry.get("unknown_tool") is None


# ---------------------------------------------------------------------------
# ToolRegistry.available_tool_names
# ---------------------------------------------------------------------------


def test_available_tool_names_returns_non_empty_list():
    names = ToolRegistry.available_tool_names()
    assert isinstance(names, list)
    assert len(names) > 0


def test_available_tool_names_returns_fresh_copy():
    a = ToolRegistry.available_tool_names()
    b = ToolRegistry.available_tool_names()
    assert a == b
    assert a is not b


# ---------------------------------------------------------------------------
# ToolRegistry.from_names
# ---------------------------------------------------------------------------


OWNER_ID = "test-agent"
SCOPE = AgentScope(owner_id=OWNER_ID, role=AgentRole.PHASE, phase_id=OWNER_ID)
SPAWN_TOOL_TYPES = (
    ("spawn_subagent", SpawnSubagentTool),
    ("spawn_identical_subagents", SpawnIdenticalSubagentsTool),
)
# Spawn tools have dedicated runtime-context coverage; native tools have no ToolProtocol instance.
TOOLS_WITHOUT_EXTRA_DEPS = [
    name for name in ToolRegistry.available_tool_names() if name not in {*dict(SPAWN_TOOL_TYPES), *NATIVE_TOOL_NAMES}
]

PROCESS_FACTORY = object()  # opaque sentinel — from_names only stores it on the spawn tool


def from_names(tool_names: list[str], tmp_path, *, scope: AgentScope = SCOPE) -> ToolRegistry:
    return ToolRegistry.from_names(
        tool_names,
        scope=scope,
        file_registry=FileRegistry(policy=FileAccessPolicy(write_root=tmp_path)),
        agent_config=AgentConfig.model_construct(tools=tool_names),
        process_factory=PROCESS_FACTORY,
    )


def test_from_names_empty(tmp_path):
    registry = from_names([], tmp_path)
    assert registry.definitions == []


def test_from_names_unknown_raises(tmp_path):
    with pytest.raises(ValueError, match="Unknown tool name: 'teleport'"):
        from_names(["teleport"], tmp_path)


@pytest.mark.parametrize("name", TOOLS_WITHOUT_EXTRA_DEPS)
def test_from_names_each_known_tool(name, tmp_path):
    registry = from_names([name], tmp_path)
    assert len(registry.definitions) == 1
    assert registry.definitions[0]["name"] == name


def test_from_names_all_at_once(tmp_path):
    all_names = TOOLS_WITHOUT_EXTRA_DEPS
    registry = from_names(all_names, tmp_path)
    built_names = {d["name"] for d in registry.definitions}
    assert built_names == set(all_names)


@pytest.mark.parametrize(("name", "tool_type"), SPAWN_TOOL_TYPES)
def test_from_names_spawn_tools_get_runtime_context(name, tool_type, tmp_path):
    registry = from_names(["read_file", name], tmp_path)

    tool = registry._tools[name]
    assert isinstance(tool, tool_type)
    assert tool._parent_scope is SCOPE
    assert tool._agent_config == make_agent_config(tools=["read_file", name])
    assert tool._process_factory is PROCESS_FACTORY
    assert tool._allowed_tools == {"read_file"}


def test_from_names_fs_tools_share_file_registry(tmp_path):
    """All tools that use the file registry in the same ToolRegistry share a single instance."""
    all_names = TOOLS_WITHOUT_EXTRA_DEPS
    registry = from_names(all_names, tmp_path)
    fs_tools = [t for t in registry._tools.values() if hasattr(t, "_registry")]
    if len(fs_tools) < 2:
        pytest.skip("Need at least 2 fs tools to test shared registry")
    registries = [t._registry for t in fs_tools]
    assert all(r is registries[0] for r in registries)


# ---------------------------------------------------------------------------
# read_only manifest annotations and filter_read_only
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "input_names,expected",
    [
        (["read_file", "edit_file", "grep", "create_file"], ["read_file", "grep"]),
        (["edit_file", "create_file"], []),
        ([], []),
        (["read_file", "list_files"], ["read_file", "list_files"]),
    ],
    ids=["mixed", "all_writes", "empty", "all_reads"],
)
def test_filter_read_only(input_names, expected):
    assert filter_read_only(input_names) == expected


def test_filter_read_only_unknown_name_raises():
    with pytest.raises(ValueError, match="Unknown tool name"):
        filter_read_only(["read_file", "teleport"])


# ---------------------------------------------------------------------------
# Native (server) tool support
# ---------------------------------------------------------------------------


def test_available_tool_names_includes_web_search():
    assert "web_search" in ToolRegistry.available_tool_names()


def test_available_tool_names_includes_web_fetch():
    assert "web_fetch" in ToolRegistry.available_tool_names()


def test_from_names_multiple_native(tmp_path):
    registry = from_names(["web_search", "web_fetch"], tmp_path)
    assert registry.definitions == []
    assert registry.native_tool_names == ("web_search", "web_fetch")


def test_from_names_native_only(tmp_path):
    registry = from_names(["web_search"], tmp_path)
    assert registry.definitions == []
    assert registry.native_tool_names == ("web_search",)


def test_from_names_client_and_native(tmp_path):
    registry = from_names(["read_file", "web_search"], tmp_path)
    assert len(registry.definitions) == 1
    assert registry.definitions[0]["name"] == "read_file"
    assert registry.native_tool_names == ("web_search",)


def test_from_names_native_not_in_tools_dict(tmp_path):
    registry = from_names(["web_search"], tmp_path)
    assert "web_search" not in registry._tools


def test_from_names_bogus_raises(tmp_path):
    with pytest.raises(ValueError, match="Unknown tool name: 'bogus'"):
        from_names(["bogus"], tmp_path)


def test_native_tool_names_not_affected_by_input_mutation():
    names = ["web_search"]
    registry = ToolRegistry([], native_tool_names=names)
    names.append("web_fetch")
    assert registry.native_tool_names == ("web_search",)


def test_filter_read_only_includes_native_read_only():
    result = filter_read_only(["read_file", "web_search", "web_fetch", "create_file"])
    assert result == ["read_file", "web_search", "web_fetch"]


def test_filter_read_only_unknown_still_raises():
    with pytest.raises(ValueError, match="Unknown tool name"):
        filter_read_only(["web_search", "bogus"])


def test_from_names_reuses_supplied_file_registry(tmp_path):
    """Multiple ToolRegistries can share one FileRegistry; tools carry their own owner_id."""
    shared = FileRegistry(policy=FileAccessPolicy(write_root=tmp_path))
    reg_a = ToolRegistry.from_names(
        ["read_file", "create_file"],
        scope=AgentScope(owner_id="a", role=AgentRole.PHASE, phase_id="a"),
        file_registry=shared,
        agent_config=make_agent_config(tools=["read_file", "create_file"]),
        process_factory=PROCESS_FACTORY,
    )
    reg_b = ToolRegistry.from_names(
        ["read_file", "create_file"],
        scope=AgentScope(owner_id="b", role=AgentRole.PHASE, phase_id="b"),
        file_registry=shared,
        agent_config=make_agent_config(tools=["read_file", "create_file"]),
        process_factory=PROCESS_FACTORY,
    )

    for tool in reg_a._tools.values():
        assert tool._registry is shared
        assert tool._owner_id == "a"
    for tool in reg_b._tools.values():
        assert tool._registry is shared
        assert tool._owner_id == "b"
