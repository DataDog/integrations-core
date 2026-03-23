# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .base import FileRegistryTool


class EditFileInput(BaseToolInput):
    path: Annotated[str, Field(description="Path of the file to edit")]
    old_string: Annotated[
        str,
        Field(
            description="Exact non-empty text to replace. Must appear exactly once in the file \
        (hint: include surrounding context if needed)."
        ),
    ]
    new_string: Annotated[str, Field(description="Text to replace old_string with")]


class EditFileTool(FileRegistryTool[EditFileInput]):
    """Edits a file by replacing an exact string with a new one.
    Can only edit files registered in the file registry.
    Fails if the file was modified since the last read.
    old_string must appear exactly once in the file — if it appears multiple times, the call fails."""

    @property
    def name(self) -> str:
        return "edit_file"

    async def __call__(self, tool_input: EditFileInput) -> ToolResult:
        path = Path(tool_input.path)

        async with self._registry.lock_for(str(path)):
            content, fail = self._read_verified(str(path))
            if fail:
                return fail

            # Normalize line endings to avoid issues with different OSs
            old_string = tool_input.old_string.replace("\r\n", "\n")
            new_string = tool_input.new_string.replace("\r\n", "\n")

            if not old_string:
                return ToolResult(success=False, error="old_string must not be empty")

            count = content.count(old_string)
            if count == 0:
                return ToolResult(success=False, error="old_string not found in file")
            if count > 1:
                return ToolResult(
                    success=False,
                    error=f"old_string appears {count} times in the file",
                    hint="Include more surrounding context to make it unique",
                )

            new_content = content.replace(old_string, new_string, 1)
            try:
                path.write_text(new_content, encoding="utf-8")
            except OSError as e:
                return ToolResult(success=False, error=str(e))
            self._record(str(path), new_content)
        return ToolResult(success=True, data=f"File edited: {path}")
