# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .base import CmdTool, run_command


class DockerInput(BaseToolInput):
    args: Annotated[list[str], Field(min_length=1, description="Arguments after `docker`.")]
    cwd: Annotated[str | None, Field(description="Working directory; defaults to the flow process directory")] = None


class DockerTool(CmdTool[DockerInput]):
    """Runs Docker CLI arguments without a shell.
    Commands time out after 300 seconds; daemon operations may continue afterward.
    Use detached mode for services and avoid following logs.
    """

    timeout = 300

    @property
    def name(self) -> str:
        return "docker"

    def cmd(self, tool_input: DockerInput) -> list[str]:
        return ["docker", *tool_input.args]

    async def __call__(self, tool_input: DockerInput) -> ToolResult:
        return await run_command(self.cmd(tool_input), timeout=self.timeout, cwd=tool_input.cwd)
