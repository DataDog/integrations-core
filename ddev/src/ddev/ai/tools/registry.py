# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module

from anthropic.types import ToolParam

from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry

from .core.protocol import ToolProtocol
from .core.types import ToolResult


@dataclass
class ToolContext:
    """Shared resources passed to every tool factory during construction."""

    file_registry: FileRegistry
    owner_id: str

    @property
    def policy(self) -> FileAccessPolicy:
        return self.file_registry.policy


def _plain_factory(tool_cls: type[ToolProtocol], ctx: ToolContext) -> ToolProtocol:
    return tool_cls()


def _file_registry_factory(tool_cls: type, ctx: ToolContext) -> ToolProtocol:
    return tool_cls(ctx.file_registry, ctx.owner_id)


def _file_policy_factory(tool_cls: type, ctx: ToolContext) -> ToolProtocol:
    return tool_cls(ctx.policy)


@dataclass(frozen=True)
class ToolSpec:
    """Lazy pointer to a tool class and how to construct it.

    ``module`` is relative to the registry's package (e.g. ``"fs.read_file"``).
    ``factory`` receives the already-imported class and the shared ToolContext
    and returns a constructed tool instance.
    """

    module: str
    cls: str
    factory: Callable[[type, ToolContext], ToolProtocol] = _plain_factory


TOOL_MANIFEST: dict[str, ToolSpec] = {
    "read_file": ToolSpec("fs.read_file", "ReadFileTool", factory=_file_registry_factory),
    "create_file": ToolSpec("fs.create_file", "CreateFileTool", factory=_file_registry_factory),
    "edit_file": ToolSpec("fs.edit_file", "EditFileTool", factory=_file_registry_factory),
    "append_file": ToolSpec("fs.append_file", "AppendFileTool", factory=_file_registry_factory),
    "grep": ToolSpec("shell.grep", "GrepTool", factory=_file_policy_factory),
    "list_files": ToolSpec("shell.list_files", "ListFilesTool"),
    "mkdir": ToolSpec("fs.mkdir", "MkdirTool", factory=_file_policy_factory),
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
        owner_id: str,
        file_registry: FileRegistry,
    ) -> ToolRegistry:
        """Build a ToolRegistry from a list of tool name strings.

        The file_registry is shared across all owners in a run so that the access
        policy applies globally; hashes inside it are partitioned by owner_id so
        each owner must still read-before-write on its own.
        """
        ctx = ToolContext(
            file_registry=file_registry,
            owner_id=owner_id,
        )
        tools: list[ToolProtocol] = []
        for name in tool_names:
            spec = TOOL_MANIFEST.get(name)
            if spec is None:
                raise ValueError(f"Unknown tool name: {name!r}")
            tool_cls = getattr(import_module(f"{__package__}.{spec.module}"), spec.cls)
            tools.append(spec.factory(tool_cls, ctx))
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
