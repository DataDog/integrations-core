# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
import pytest

from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.agents.spawn_subagent import SpawnSubagentTool
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry, filter_read_only

# ---------------------------------------------------------------------------
# Fake tools — implement ToolProtocol without depending on BaseTool
# ---------------------------------------------------------------------------


class FakeTool:
    """Minimal ToolProtocol implementation for registry tests."""

    def __init__(self, name: str, result: ToolResult | None = None) -> None:
        self._name = name
        self._result = result or ToolResult(success=True, data=f"{name} ok")
        self.last_raw: dict[str, object] | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Fake tool {self._name}"

    @property
    def definition(self) -> dict:
        return {"name": self._name, "description": self.description, "input_schema": {}}

    async def run(self, raw: dict[str, object]) -> ToolResult:
        self.last_raw = raw
        return self._result


# ---------------------------------------------------------------------------
# ToolRegistry.__init__
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tools,expected_names",
    [
        ([FakeTool("alpha")], {"alpha"}),
        ([], set()),
        ([FakeTool("a"), FakeTool("b"), FakeTool("c")], {"a", "b", "c"}),
    ],
)
def test_registry_registers_tools(tools, expected_names):
    registry = ToolRegistry(tools)
    assert set(registry._tools.keys()) == expected_names


def test_duplicate_name_last_one_wins():
    # This design is intentional to allow for tool overrides.
    first = FakeTool("dup")
    second = FakeTool("dup")
    registry = ToolRegistry([first, second])
    assert registry._tools["dup"] is second


# ---------------------------------------------------------------------------
# ToolRegistry.definitions
# ---------------------------------------------------------------------------


def test_empty_registry_returns_empty_list():
    assert ToolRegistry([]).definitions == []


def test_tool_registry_definitions_returns_all_tool_definitions():
    registry = ToolRegistry([FakeTool("a"), FakeTool("b")])
    assert len(registry.definitions) == 2


def test_definition_contains_tool_name():
    registry = ToolRegistry([FakeTool("mytool")])
    assert registry.definitions[0]["name"] == "mytool"


# ---------------------------------------------------------------------------
# ToolRegistry.run
# ---------------------------------------------------------------------------


async def test_run_dispatches_to_correct_tool():
    tool_a = FakeTool("a", ToolResult(success=True, data="from a"))
    tool_b = FakeTool("b", ToolResult(success=True, data="from b"))
    registry = ToolRegistry([tool_a, tool_b])

    result = await registry.run("b", {})
    assert result.success is True
    assert result.data == "from b"


async def test_passes_raw_dict_to_tool_unchanged():
    tool = FakeTool("t")
    registry = ToolRegistry([tool])
    raw = {"key": "value", "num": 42}

    await registry.run("t", raw)
    assert tool.last_raw == raw


async def test_returns_tool_result_on_tool_failure():
    registry = ToolRegistry([FakeTool("t", ToolResult(success=False, error="bad input"))])
    result = await registry.run("t", {})
    assert result.success is False
    assert result.error == "bad input"


async def test_unknown_tool_returns_failure():
    registry = ToolRegistry([FakeTool("known_tool")])
    result = await registry.run("unknown_tool", {})
    assert result.success is False
    assert "Unknown tool: 'unknown_tool'" in result.error


async def test_empty_registry_always_returns_unknown_error():
    registry = ToolRegistry([])
    result = await registry.run("anything", {})
    assert result.success is False
    assert result.error is not None


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
TOOLS_WITHOUT_EXTRA_DEPS = [n for n in ToolRegistry.available_tool_names() if n != "spawn_subagent"]

PROCESS_FACTORY = object()  # opaque sentinel — from_names only stores it on the spawn tool


def from_names(tool_names: list[str], tmp_path, *, owner_id: str = OWNER_ID) -> ToolRegistry:
    return ToolRegistry.from_names(
        tool_names,
        owner_id=owner_id,
        file_registry=FileRegistry(policy=FileAccessPolicy(write_root=tmp_path)),
        agent_config=AgentConfig.model_construct(name="test_agent", provider="anthropic", tools=tool_names, system_prompt_path=Path("/fake.md")),
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


def test_from_names_spawn_subagent_gets_runtime_context(tmp_path):
    registry = from_names(["read_file", "spawn_subagent"], tmp_path)

    tool = registry._tools["spawn_subagent"]
    assert isinstance(tool, SpawnSubagentTool)
    assert tool._agent_config == AgentConfig(name="test_agent", tools=["read_file", "spawn_subagent"], system_prompt_path=Path("/fake.md"))
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


def test_from_names_reuses_supplied_file_registry(tmp_path):
    """Multiple ToolRegistries can share one FileRegistry; tools carry their own owner_id."""
    shared = FileRegistry(policy=FileAccessPolicy(write_root=tmp_path))
    reg_a = ToolRegistry.from_names(
        ["read_file", "create_file"],
        owner_id="a",
        file_registry=shared,
        agent_config=AgentConfig(name="test_agent", tools=["read_file", "create_file"], system_prompt_path=Path("/fake.md")),
        process_factory=PROCESS_FACTORY,
    )
    reg_b = ToolRegistry.from_names(
        ["read_file", "create_file"],
        owner_id="b",
        file_registry=shared,
        agent_config=AgentConfig(name="test_agent", tools=["read_file", "create_file"], system_prompt_path=Path("/fake.md")),
        process_factory=PROCESS_FACTORY,
    )

    for tool in reg_a._tools.values():
        assert tool._registry is shared
        assert tool._owner_id == "a"
    for tool in reg_b._tools.values():
        assert tool._registry is shared
        assert tool._owner_id == "b"
