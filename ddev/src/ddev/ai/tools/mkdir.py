# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from typing import Annotated

from .cmd import CmdTool


@dataclass
class MkdirInput:
    path: Annotated[str, "Path of the directory to create"]


class MkdirTool(CmdTool[MkdirInput]):
    """Creates a directory at the given path, including any missing parent directories.
    Use to create directories for config files, logs, source code."""

    @property
    def name(self) -> str:
        return "mkdir"

    def cmd(self, tool_input: MkdirInput) -> list[str]:
        return ["mkdir", "-p", tool_input.path]
