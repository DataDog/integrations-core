# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput

from .base import CmdTool


class ReadFileInput(BaseToolInput):
    path: Annotated[str, Field(description="Absolute or relative path to the file to read")]
    offset: Annotated[int, Field(description="Line number to start reading from (0-indexed, default: 0). Must be >= 0.")] = 0
    limit: Annotated[int | None, Field(description="Number of lines to read (default: all remaining lines). Must be >= 1.")] = None


class ReadFileTool(CmdTool[ReadFileInput]):
    """Reads contents of a text file from the host filesystem.
    Use to inspect config files, logs, source code. Do not use for binary files.
    Supports offset/limit for paging through large files."""

    @property
    def name(self) -> str:
        return "read_file"

    def cmd(self, tool_input: ReadFileInput) -> list[str]:
        path = tool_input.path
        offset = max(0, tool_input.offset)
        limit = max(1, tool_input.limit) if tool_input.limit is not None else None
        if offset == 0 and limit is None:
            return ["cat", path]
        start = offset + 1
        if limit is not None:
            return ["awk", f"NR>={start} && NR<={start + limit - 1}", path]
        return ["awk", f"NR>={start}", path]
