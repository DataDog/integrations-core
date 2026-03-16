# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from ddev.ai.tools.core.base import BaseTool
from ddev.ai.tools.core.types import ToolResult

from .file_registry import FileRegistry


@dataclass
class EditFileInput:
    path: Annotated[str, "Path of the file to edit"]
    old_string: Annotated[
        str,
        "Exact text to replace. Must appear exactly once in the file (hint: include surrounding context if needed)",
    ]
    new_string: Annotated[str, "Text to replace old_string with"]


class EditFileTool(BaseTool[EditFileInput]):
    """Edits a file by replacing an exact string with a new one.
    Only files registered in the FileRegistry can be edited.
    old_string must appear exactly once in the file — if it appears multiple times, the call fails.
    Read the file first with read_file to get the exact content to use as old_string."""

    def __init__(self, file_registry: FileRegistry) -> None:
        self._file_registry = file_registry

    @property
    def name(self) -> str:
        return "edit_file"

    async def __call__(self, tool_input: EditFileInput) -> ToolResult:
        path = Path(tool_input.path)

        if not self._file_registry.is_registered(str(path)):
            return ToolResult(
                success=False, error=f"Not authorized to edit {path}: file is not registered in the FileRegistry"
            )

        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        content: str = path.read_text().replace("\r\n", "\n")
        old_string: str = tool_input.old_string.replace("\r\n", "\n")
        new_string: str = tool_input.new_string.replace("\r\n", "\n")

        count = content.count(old_string)
        if count == 0:
            return ToolResult(success=False, error="old_string not found in file")
        if count > 1:
            return ToolResult(
                success=False,
                error=f"old_string appears {count} times in the file",
                hint="Include more surrounding context to make it unique",
            )

        path.write_text(content.replace(old_string, new_string, 1))
        return ToolResult(success=True, data=f"File edited: {path}")
