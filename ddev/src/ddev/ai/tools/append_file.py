# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from .base import BaseTool
from .file_registry import FileRegistry
from .types import ToolResult


@dataclass
class AppendFileInput:
    path: Annotated[str, "Path of the file to append"]
    content: Annotated[str, "Content to append to the file"]


class AppendFileTool(BaseTool[AppendFileInput]):
    """Appends content to the end of an existing file.
    Only files registered in the FileRegistry can be appended to."""

    def __init__(self, file_registry: FileRegistry):
        self._file_registry = file_registry

    @property
    def name(self) -> str:
        return "append_file"

    async def __call__(self, tool_input: AppendFileInput) -> ToolResult:
        path = Path(tool_input.path)

        if not self._file_registry.is_registered(str(path)):
            return ToolResult(
                success=False, error=f"Not authorized to append to {path}: file is not registered in the FileRegistry"
            )

        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        with path.open("a") as f:
            f.write(tool_input.content)
        return ToolResult(success=True, data=f"Content appended to: {path}")
