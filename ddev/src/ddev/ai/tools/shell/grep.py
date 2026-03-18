# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput

from .base import CmdTool


class GrepInput(BaseToolInput):
    pattern: Annotated[str, Field(description="Regex pattern to search for")]
    path: Annotated[str, Field(description="File or directory to search in")]
    recursive: Annotated[bool, Field(description="Search recursively in directories (default: true)")] = True


class GrepTool(CmdTool[GrepInput]):
    """Searches for a regex pattern in files. Returns matching lines with file path and line
    numbers. Use to find specific config values, ports, hostnames across files. Supports extended
    regex syntax. Output might be truncated for large results."""

    timeout = 30

    @property
    def name(self) -> str:
        return "grep"

    def cmd(self, tool_input: GrepInput) -> list[str]:
        cmd = ["grep", "-n", "-E"]
        if tool_input.recursive:
            cmd.append("-r")
        cmd += ["--", tool_input.pattern, tool_input.path]
        return cmd
