# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from abc import abstractmethod
from typing import ClassVar

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.truncation import TruncateResult, truncate
from ddev.ai.tools.core.types import ToolResult


class CmdTool[TInput: BaseToolInput](BaseTool[TInput]):
    """Base for tools that execute shell commands."""

    timeout: ClassVar[int] = 10

    @abstractmethod
    def cmd(self, tool_input: TInput) -> list[str]:
        """Builds the shell command from validated tool input."""
        ...

    async def __call__(self, tool_input: TInput) -> ToolResult:
        return await run_command(self.cmd(tool_input), timeout=self.timeout)


async def run_command(cmd: list[str], timeout: int = 10) -> ToolResult:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except FileNotFoundError:
        return ToolResult(success=False, error=f"Command not found: {cmd[0]!r}")
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return ToolResult(success=False, error=f"Command timed out after {timeout}s: {cmd}")
    except Exception as e:
        return ToolResult(success=False, error=f"{type(e).__name__}: {e}")

    # errors="replace" to keep output readable in case of non-UTF-8 characters
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    output = stdout
    if proc.returncode != 0 and stderr:
        output = (output + "\n" + stderr) if output else stderr
    elif not output and stderr:
        output = stderr

    if not output.strip():
        return ToolResult(success=proc.returncode == 0, data="(no output)")

    result: TruncateResult = truncate(output)

    if result.truncated and result.meta is not None:
        return ToolResult(
            success=proc.returncode == 0,
            data=result.output,
            truncated=True,
            total_size=result.meta.total_size,
            shown_size=result.meta.shown_size,
            hint=result.meta.hint,
        )

    return ToolResult(success=proc.returncode == 0, data=result.output)
