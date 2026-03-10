# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from abc import abstractmethod

from .base import BaseTool
from .types import ToolResult


class CmdTool(BaseTool):
    """Base for tools that execute shell commands."""

    @abstractmethod
    def cmd(self, tool_input: dict[str, object]) -> list[str]:
        """Builds the shell command from validated tool input."""
        ...

    async def __call__(self, tool_input: dict[str, object]) -> ToolResult:
        return await run_command(self.cmd(tool_input))


async def run_command(cmd: list[str]) -> ToolResult:
    return ToolResult(success=False, error="Not implemented yet")
