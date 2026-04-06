# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from anthropic.types import ToolParam

from ddev.ai.tools.fs.file_registry import FileRegistry

from .protocol import ToolProtocol
from .types import ToolResult


class ToolRegistry:
    """Registry holding all available tools."""

    def __init__(self, tools: list[ToolProtocol]) -> None:
        self._tools: dict[str, ToolProtocol] = {tool.name: tool for tool in tools}

    @classmethod
    def from_names(cls, tool_names: list[str]) -> ToolRegistry:
        """Create a ToolRegistry from a list of tool name strings.

        All fs tools within the same registry share a single FileRegistry instance.
        """
        file_registry = FileRegistry()
        return cls([cls._create(name, file_registry) for name in tool_names])

    @staticmethod
    def _create(name: str, file_registry: FileRegistry) -> ToolProtocol:
        from ddev.ai.tools.fs.append_file import AppendFileTool
        from ddev.ai.tools.fs.create_file import CreateFileTool
        from ddev.ai.tools.fs.edit_file import EditFileTool
        from ddev.ai.tools.fs.read_file import ReadFileTool
        from ddev.ai.tools.http.http_get import HttpGetTool
        from ddev.ai.tools.shell.grep import GrepTool
        from ddev.ai.tools.shell.list_files import ListFilesTool
        from ddev.ai.tools.shell.mkdir import MkdirTool

        match name:
            case "read_file":
                return ReadFileTool(file_registry)
            case "create_file":
                return CreateFileTool(file_registry)
            case "edit_file":
                return EditFileTool(file_registry)
            case "append_file":
                return AppendFileTool(file_registry)
            case "http_get":
                return HttpGetTool()
            case "list_files":
                return ListFilesTool()
            case "grep":
                return GrepTool()
            case "mkdir":
                return MkdirTool()
            case _:
                raise ValueError(f"Unknown tool: {name!r}")

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
