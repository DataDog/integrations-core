# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess
from abc import abstractmethod
from typing import Any

from .base import BaseTool
from .truncation import truncate
from .types import ToolResult


class CmdTool(BaseTool):
    """Base for tools that execute shell commands."""

    @abstractmethod
    def cmd(self, tool_input: Any) -> list[str]:
        """Builds the shell command from validated tool input."""
        ...

    async def __call__(self, tool_input: Any) -> ToolResult:
        return await run_command(self.cmd(tool_input))


async def run_command(cmd: list[str]) -> ToolResult:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        return ToolResult(success=False, error=f"Command not found: {cmd[0]!r}")
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, error=f"Command timed out after 10 seconds: {cmd}")

    output = proc.stdout
    if proc.returncode != 0 and proc.stderr:
        output = output + proc.stderr if output else proc.stderr

    if not output.strip():
        return ToolResult(success=proc.returncode == 0, data="(no output)")

    truncated_output, was_truncated, meta = truncate(output)

    if was_truncated and meta is not None:
        return ToolResult(
            success=proc.returncode == 0,
            data=truncated_output,
            truncated=True,
            total_size=meta["total_size"],
            shown_size=meta["shown_size"],
            hint=meta["hint"],
        )

    return ToolResult(success=proc.returncode == 0, data=output)
