# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

from anthropic.types import ToolParam

from ddev.ai.tools.fs.file_registry import FileRegistry

from .protocol import ToolProtocol
from .types import ToolResult

TOOLS_PACKAGE = "ddev.ai.tools"


@dataclass(frozen=True)
class ToolSpec:
    """Lazy pointer to a tool class and how to construct it.

    ``module`` is relative to ``TOOLS_PACKAGE`` (e.g. ``"fs.read_file"``).
    """

    module: str
    cls: str
    requires_file_registry: bool = False


TOOL_MANIFEST: dict[str, ToolSpec] = {
    "read_file": ToolSpec("fs.read_file", "ReadFileTool", requires_file_registry=True),
    "create_file": ToolSpec("fs.create_file", "CreateFileTool", requires_file_registry=True),
    "edit_file": ToolSpec("fs.edit_file", "EditFileTool", requires_file_registry=True),
    "append_file": ToolSpec("fs.append_file", "AppendFileTool", requires_file_registry=True),
    "grep": ToolSpec("shell.grep", "GrepTool"),
    "list_files": ToolSpec("shell.list_files", "ListFilesTool"),
    "mkdir": ToolSpec("fs.mkdir", "MkdirTool", requires_file_registry=True),
    "http_get": ToolSpec("http.http_get", "HttpGetTool"),
    "ddev_create": ToolSpec("shell.ddev.create", "DdevCreateTool"),
    "ddev_test": ToolSpec("shell.ddev.ddev_test", "DdevTestTool"),
    "ddev_env_show": ToolSpec("shell.ddev.env_show", "DdevEnvShowTool"),
    "ddev_env_start": ToolSpec("shell.ddev.env_start", "DdevEnvStartTool"),
    "ddev_env_stop": ToolSpec("shell.ddev.env_stop", "DdevEnvStopTool"),
    "ddev_env_test": ToolSpec("shell.ddev.env_test", "DdevEnvTestTool"),
    "ddev_release_changelog": ToolSpec("shell.ddev.release_changelog", "DdevReleaseChangelogTool"),
}


class ToolRegistry:
    """Registry holding all available tools."""

    def __init__(self, tools: list[ToolProtocol]) -> None:
        self._tools: dict[str, ToolProtocol] = {tool.name: tool for tool in tools}

    @staticmethod
    def available_tool_names() -> list[str]:
        """Return all tool names that from_names can resolve."""
        return list(TOOL_MANIFEST)

    @classmethod
    def from_names(
        cls,
        tool_names: list[str],
        *,
        agent_id: str,
        file_registry: FileRegistry | None = None,
    ) -> ToolRegistry:
        """Build a ToolRegistry from a list of tool name strings.

        The file_registry is expected to be shared across all agents in a run so
        that the access policy applies globally; hashes inside it are partitioned
        by agent_id so each agent must still read-before-write on its own.
        A new (unshared) FileRegistry is created if one is not supplied.
        """
        tools: list[ToolProtocol] = []
        shared_registry = file_registry if file_registry is not None else FileRegistry()
        for name in tool_names:
            spec = TOOL_MANIFEST.get(name)
            if spec is None:
                raise ValueError(f"Unknown tool name: {name!r}")
            tool_cls = getattr(import_module(f"{TOOLS_PACKAGE}.{spec.module}"), spec.cls)
            if spec.requires_file_registry:
                tools.append(tool_cls(shared_registry, agent_id))
            else:
                tools.append(tool_cls())
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

    def format_call(self, name: str, raw: dict[str, object]) -> str:
        """Delegate to the tool's format_call for a UI-friendly string. Falls back to name."""
        tool = self._tools.get(name)
        if tool is None:
            return name
        return tool.format_call(raw)
