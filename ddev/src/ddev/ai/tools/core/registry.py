# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from anthropic.types import ToolParam

from .protocol import ToolProtocol
from .types import ToolResult


class ToolRegistry:
    """Registry holding all available tools."""

    def __init__(self, tools: list[ToolProtocol]) -> None:
        self._tools: dict[str, ToolProtocol] = {tool.name: tool for tool in tools}

    @property
    def definitions(self) -> list[ToolParam]:
        """Return Anthropic SDK tool definitions for all registered tools."""
        return [tool.definition for tool in self._tools.values()]

    async def run(self, name: str, raw: dict[str, object]) -> ToolResult:
        """Execute a tool by name, returning an error result if not found."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(success=False, error=f"Unknown tool: {name!r}")
        return await tool.run(raw)
