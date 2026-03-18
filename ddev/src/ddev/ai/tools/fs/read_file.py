# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from ddev.ai.tools.core.base import safe_int
from ddev.ai.tools.core.types import ToolResult

from .base import TextEdit


class ReadFileInput(BaseToolInput):
    path: Annotated[str, Field(description="Absolute or relative path to the file to read")]
    offset: Annotated[int, Field(description="Line number to start reading from (0-indexed, default: 0). Must be >= 0.")] = 0
    limit: Annotated[int | None, Field(description="Number of lines to read (default: all remaining lines). Must be >= 1.")] = None


class ReadFileTool(TextEdit[ReadFileInput]):
    """Reads contents of a text file from the host filesystem.
    Use to inspect config files, logs, source code. Do not use for binary files.
    Supports offset/limit for paging through large files."""

    @property
    def name(self) -> str:
        return "read_file"

    async def __call__(self, tool_input: ReadFileInput) -> ToolResult:
        try:
            content = Path(tool_input.path).read_text(encoding="utf-8")
        except OSError as e:
            return ToolResult(success=False, error=str(e))

        self._on_read(tool_input.path, content)

        offset = max(0, safe_int(tool_input.offset, 0))
        limit = max(1, safe_int(tool_input.limit, 1)) if tool_input.limit is not None else None
        lines = content.splitlines(keepends=True)
        slice_ = lines[offset : offset + limit] if limit is not None else lines[offset:]
        return ToolResult(success=True, data="".join(slice_))
