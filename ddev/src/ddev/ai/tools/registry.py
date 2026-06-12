# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING

from anthropic.types import ToolParam

from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry

from .core.protocol import ToolProtocol
from .core.types import ToolResult

if TYPE_CHECKING:
    from ddev.ai.config.models import AgentConfig
    from ddev.ai.react.factory import ReActProcessFactory


@dataclass
class ToolContext:
    """Shared resources passed to every tool factory during construction."""

    file_registry: FileRegistry
    owner_id: str
    agent_config: AgentConfig
    process_factory: ReActProcessFactory

    @property
    def policy(self) -> FileAccessPolicy:
        return self.file_registry.policy


def _plain_factory(tool_cls: type[ToolProtocol], ctx: ToolContext) -> ToolProtocol:
    return tool_cls()


def _file_registry_factory(tool_cls: type, ctx: ToolContext) -> ToolProtocol:
    return tool_cls(ctx.file_registry, ctx.owner_id)


def _file_policy_factory(tool_cls: type, ctx: ToolContext) -> ToolProtocol:
    return tool_cls(ctx.policy)


def _spawn_subagent_factory(tool_cls: type, ctx: ToolContext) -> ToolProtocol:
    return tool_cls(
        owner_id=ctx.owner_id,
        agent_config=ctx.agent_config,
        process_factory=ctx.process_factory,
    )


@dataclass(frozen=True)
class ToolSpec:
    """Lazy pointer to a tool class and how to construct it.

    ``module`` is relative to the registry's package (e.g. ``"fs.read_file"``).
    ``factory`` receives the already-imported class and the shared ToolContext
    and returns a constructed tool instance.
    ``read_only`` marks tools that only inspect state and never mutate it.
    """

    module: str
    cls: str
    factory: Callable[[type, ToolContext], ToolProtocol] = _plain_factory
    read_only: bool = False


TOOL_MANIFEST: dict[str, ToolSpec] = {
    "read_file": ToolSpec("fs.read_file", "ReadFileTool", factory=_file_registry_factory, read_only=True),
    "create_file": ToolSpec("fs.create_file", "CreateFileTool", factory=_file_registry_factory, read_only=False),
    "edit_file": ToolSpec("fs.edit_file", "EditFileTool", factory=_file_registry_factory, read_only=False),
    "append_file": ToolSpec("fs.append_file", "AppendFileTool", factory=_file_registry_factory, read_only=False),
    "copy_path": ToolSpec("fs.copy_path", "CopyPathTool", factory=_file_policy_factory, read_only=False),
    "grep": ToolSpec("shell.grep", "GrepTool", factory=_file_policy_factory, read_only=True),
    "list_files": ToolSpec("shell.list_files", "ListFilesTool", read_only=True),
    "mkdir": ToolSpec("fs.mkdir", "MkdirTool", factory=_file_policy_factory, read_only=False),
    "http_get": ToolSpec("http.http_get", "HttpGetTool", read_only=True),
    "ddev_create": ToolSpec("shell.ddev.create", "DdevCreateTool", read_only=False),
    "ddev_test": ToolSpec("shell.ddev.ddev_test", "DdevTestTool", read_only=False),
    "ddev_env_show": ToolSpec("shell.ddev.env_show", "DdevEnvShowTool", read_only=True),
    "ddev_env_start": ToolSpec("shell.ddev.env_start", "DdevEnvStartTool", read_only=False),
    "ddev_env_stop": ToolSpec("shell.ddev.env_stop", "DdevEnvStopTool", read_only=False),
    "ddev_env_test": ToolSpec("shell.ddev.env_test", "DdevEnvTestTool", read_only=True),
    "ddev_release_changelog": ToolSpec("shell.ddev.release_changelog", "DdevReleaseChangelogTool", read_only=False),
    "ddev_validate": ToolSpec("shell.ddev.validate", "DdevValidateTool", read_only=False),
    "spawn_subagent": ToolSpec(
        "agents.spawn_subagent",
        "SpawnSubagentTool",
        factory=_spawn_subagent_factory,
        read_only=False,
    ),
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
        agent_config: AgentConfig,
        process_factory: ReActProcessFactory,
    ) -> ToolRegistry:
        """Build a ToolRegistry from a list of tool name strings.

        The file_registry is shared across all owners in a run so that the access
        policy applies globally; hashes inside it are partitioned by owner_id so
        each owner must still read-before-write on its own.

        ``process_factory`` is only consumed by tools that spawn child agents.
        """
        ctx = ToolContext(
            file_registry=file_registry,
            owner_id=owner_id,
            agent_config=agent_config,
            process_factory=process_factory,
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


def filter_read_only(tool_names: list[str]) -> list[str]:
    """Return only the names whose ToolSpec has read_only=True. Unknown names raise."""
    out: list[str] = []
    for name in tool_names:
        spec = TOOL_MANIFEST.get(name)
        if spec is None:
            raise ValueError(f"Unknown tool name: {name!r}")
        if spec.read_only:
            out.append(name)
    return out
