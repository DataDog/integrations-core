# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from typing import Annotated

from .cmd import CmdTool


@dataclass
class ListFilesInput:
    path: Annotated[str, "Path to list files from"]
    recursive: Annotated[bool, "Whether to list recursively (default: false)"] = False


class ListFilesTool(CmdTool[ListFilesInput]):
    """Lists files and directories at the given path. Use to explore directory structure and find
    config files. Non-recursive by default - set recursive=true for a deep listing."""

    timeout = 30

    @property
    def name(self) -> str:
        return "list_files"

    def cmd(self, tool_input: ListFilesInput) -> list[str]:
        cmd = ["find", tool_input.path, "-mindepth", "1"]
        if not tool_input.recursive:
            cmd += ["-maxdepth", "1"]
        return cmd
