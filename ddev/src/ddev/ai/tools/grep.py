# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from typing import Annotated

from .cmd import CmdTool


@dataclass
class GrepInput:
    pattern: Annotated[str, "Regex pattern to search for"]
    path: Annotated[str, "File or directory to search in"]
    recursive: Annotated[bool, "Search recursively in directories (default: true)"] = True


class GrepTool(CmdTool):
    """Searches for a regex pattern in files. Returns matching lines with file path and line
    numbers. Use to find specific config values, ports, hostnames across files. Supports extended
    regex syntax. Output might be truncated for large results."""

    Input = GrepInput

    @property
    def name(self) -> str:
        return "grep"

    def cmd(self, tool_input: GrepInput) -> list[str]:
        cmd = ["grep", "-n", "-E", tool_input.pattern]
        if tool_input.recursive:
            cmd.append("-r")
        cmd.append(tool_input.path)
        return cmd
