# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.tools.core.registry import ToolRegistry
from ddev.ai.tools.core.types import ToolResult

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
# ToolRegistry.from_names
# ---------------------------------------------------------------------------


def test_from_names_empty_list_creates_empty_registry():
    registry = ToolRegistry.from_names([])
    assert registry.definitions == []


def test_from_names_creates_registry_with_correct_tool_names():
    registry = ToolRegistry.from_names(["read_file", "http_get"])
    names = {d["name"] for d in registry.definitions}
    assert names == {"read_file", "http_get"}


def test_from_names_unknown_tool_raises():
    with pytest.raises(ValueError, match="Unknown tool: 'does_not_exist'"):
        ToolRegistry.from_names(["does_not_exist"])


def test_from_names_fs_tools_share_file_registry():
    # fs tools in the same registry must share a FileRegistry so that
    # hash-based consistency checks work across tool calls within a phase.
    registry = ToolRegistry.from_names(["create_file", "read_file"])
    create_tool = registry._tools["create_file"]
    read_tool = registry._tools["read_file"]
    assert create_tool._registry is read_tool._registry
