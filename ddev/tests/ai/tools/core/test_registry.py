# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio

from ddev.ai.tools.core.registry import ALLOWED_TOOL_CALLERS, ToolRegistry
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


class TestToolRegistryInit:
    def test_registers_tools_by_name(self):
        tool = FakeTool("alpha")
        registry = ToolRegistry([tool])
        assert registry._tools["alpha"] is tool

    def test_empty_list_creates_empty_registry(self):
        registry = ToolRegistry([])
        assert registry._tools == {}

    def test_multiple_tools_all_registered(self):
        tools = [FakeTool("a"), FakeTool("b"), FakeTool("c")]
        registry = ToolRegistry(tools)
        assert set(registry._tools.keys()) == {"a", "b", "c"}

    def test_duplicate_name_last_one_wins(self):
        first = FakeTool("dup")
        second = FakeTool("dup")
        registry = ToolRegistry([first, second])
        assert registry._tools["dup"] is second


# ---------------------------------------------------------------------------
# ToolRegistry.definitions
# ---------------------------------------------------------------------------


class TestToolRegistryDefinitions:
    def test_empty_registry_returns_empty_list(self):
        assert ToolRegistry([]).definitions == []

    def test_returns_one_definition_per_tool(self):
        registry = ToolRegistry([FakeTool("a"), FakeTool("b")])
        assert len(registry.definitions) == 2

    def test_each_definition_has_allowed_callers(self):
        registry = ToolRegistry([FakeTool("a"), FakeTool("b")])
        for defn in registry.definitions:
            assert defn["allowed_callers"] == ALLOWED_TOOL_CALLERS

    def test_allowed_callers_value_is_correct(self):
        registry = ToolRegistry([FakeTool("x")])
        assert registry.definitions[0]["allowed_callers"] == ["code_execution_20260120"]

    def test_definition_contains_tool_name(self):
        registry = ToolRegistry([FakeTool("mytool")])
        assert registry.definitions[0]["name"] == "mytool"

    def test_calling_definitions_twice_is_consistent(self):
        registry = ToolRegistry([FakeTool("a")])
        first = registry.definitions
        second = registry.definitions
        assert first[0]["name"] == second[0]["name"]
        assert first[0]["allowed_callers"] == second[0]["allowed_callers"]


# ---------------------------------------------------------------------------
# ToolRegistry.run
# ---------------------------------------------------------------------------


class TestToolRegistryRun:
    def test_dispatches_to_correct_tool(self):
        tool_a = FakeTool("a", ToolResult(success=True, data="from a"))
        tool_b = FakeTool("b", ToolResult(success=True, data="from b"))
        registry = ToolRegistry([tool_a, tool_b])

        result = asyncio.run(registry.run("b", {}))
        assert result.data == "from b"

    def test_passes_raw_dict_to_tool_unchanged(self):
        tool = FakeTool("t")
        registry = ToolRegistry([tool])
        raw = {"key": "value", "num": 42}

        asyncio.run(registry.run("t", raw))
        assert tool.last_raw == raw

    def test_returns_tool_result_on_success(self):
        registry = ToolRegistry([FakeTool("t", ToolResult(success=True, data="ok"))])
        result = asyncio.run(registry.run("t", {}))
        assert result.success is True
        assert result.data == "ok"

    def test_returns_tool_result_on_tool_failure(self):
        registry = ToolRegistry([FakeTool("t", ToolResult(success=False, error="bad input"))])
        result = asyncio.run(registry.run("t", {}))
        assert result.success is False
        assert result.error == "bad input"

    def test_unknown_tool_returns_failure(self):
        registry = ToolRegistry([FakeTool("known")])
        result = asyncio.run(registry.run("unknown", {}))
        assert result.success is False

    def test_unknown_tool_error_contains_tool_name(self):
        registry = ToolRegistry([])
        result = asyncio.run(registry.run("missing_tool", {}))
        assert "missing_tool" in result.error

    def test_empty_registry_always_returns_unknown_error(self):
        registry = ToolRegistry([])
        result = asyncio.run(registry.run("anything", {}))
        assert result.success is False
        assert result.error is not None
