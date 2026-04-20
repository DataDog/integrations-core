# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from anthropic.types import ToolParam

from .protocol import ToolProtocol
from .types import ToolResult

_TOOL_NAMES: list[str] = [
    "read_file",
    "create_file",
    "edit_file",
    "append_file",
    "grep",
    "list_files",
    "mkdir",
    "http_get",
    "ddev_create",
    "ddev_test",
    "ddev_env_show",
    "ddev_env_start",
    "ddev_env_stop",
    "ddev_env_test",
    "ddev_release_changelog",
]


class ToolRegistry:
    """Registry holding all available tools."""

    def __init__(self, tools: list[ToolProtocol]) -> None:
        self._tools: dict[str, ToolProtocol] = {tool.name: tool for tool in tools}

    @staticmethod
    def available_tool_names() -> list[str]:
        """Return all tool names that from_names can resolve."""
        return list(_TOOL_NAMES)

    @classmethod
    def from_names(cls, tool_names: list[str]) -> "ToolRegistry":
        """Build a ToolRegistry from a list of tool name strings.

        All file-system tools in the same registry share a single FileRegistry.
        """
        from ddev.ai.tools.fs.append_file import AppendFileTool
        from ddev.ai.tools.fs.create_file import CreateFileTool
        from ddev.ai.tools.fs.edit_file import EditFileTool
        from ddev.ai.tools.fs.file_registry import FileRegistry
        from ddev.ai.tools.fs.read_file import ReadFileTool
        from ddev.ai.tools.http.http_get import HttpGetTool
        from ddev.ai.tools.shell.ddev.create import DdevCreateTool
        from ddev.ai.tools.shell.ddev.ddev_test import DdevTestTool
        from ddev.ai.tools.shell.ddev.env_show import DdevEnvShowTool
        from ddev.ai.tools.shell.ddev.env_start import DdevEnvStartTool
        from ddev.ai.tools.shell.ddev.env_stop import DdevEnvStopTool
        from ddev.ai.tools.shell.ddev.env_test import DdevEnvTestTool
        from ddev.ai.tools.shell.ddev.release_changelog import DdevReleaseChangelogTool
        from ddev.ai.tools.shell.grep import GrepTool
        from ddev.ai.tools.shell.list_files import ListFilesTool
        from ddev.ai.tools.shell.mkdir import MkdirTool

        file_registry = FileRegistry()
        tools: list[ToolProtocol] = []
        for name in tool_names:
            match name:
                case "read_file":
                    tools.append(ReadFileTool(file_registry))
                case "create_file":
                    tools.append(CreateFileTool(file_registry))
                case "edit_file":
                    tools.append(EditFileTool(file_registry))
                case "append_file":
                    tools.append(AppendFileTool(file_registry))
                case "grep":
                    tools.append(GrepTool())
                case "list_files":
                    tools.append(ListFilesTool())
                case "mkdir":
                    tools.append(MkdirTool())
                case "http_get":
                    tools.append(HttpGetTool())
                case "ddev_create":
                    tools.append(DdevCreateTool())
                case "ddev_test":
                    tools.append(DdevTestTool())
                case "ddev_env_show":
                    tools.append(DdevEnvShowTool())
                case "ddev_env_start":
                    tools.append(DdevEnvStartTool())
                case "ddev_env_stop":
                    tools.append(DdevEnvStopTool())
                case "ddev_env_test":
                    tools.append(DdevEnvTestTool())
                case "ddev_release_changelog":
                    tools.append(DdevReleaseChangelogTool())
                case _:
                    raise ValueError(f"Unknown tool name: {name!r}")
        return cls(tools)

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
