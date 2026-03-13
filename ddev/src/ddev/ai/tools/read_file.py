# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from typing import Annotated

from .base import safe_int
from .cmd import CmdTool


@dataclass
class ReadFileInput:
    path: Annotated[str, "Absolute or relative path to the file to read"]
    offset: Annotated[int | None, "Line number to start reading from (0-indexed, default: 0)"] = None
    limit: Annotated[int | None, "Number of lines to read (default: all remaining lines)"] = None


class ReadFileTool(CmdTool[ReadFileInput]):
    """Reads contents of a text file from the host filesystem.
    Use to inspect config files, logs, source code. Do not use for binary files.
    Supports offset/limit for paging through large files."""

    @property
    def name(self) -> str:
        return "read_file"

    def cmd(self, tool_input: ReadFileInput) -> list[str]:
        path = tool_input.path
        offset = safe_int(tool_input.offset, 0)
        limit = safe_int(tool_input.limit, None)
        if offset == 0 and limit is None:
            return ["cat", path]
        start = offset + 1
        if limit is not None:
            return ["awk", f"NR>={start} && NR<={start + limit - 1}", path]
        return ["awk", f"NR>={start}", path]
