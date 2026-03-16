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
class CreateFileInput:
    path: Annotated[str, "Path of the file to create"]
    content: Annotated[str, "Content of the file to create"] = ""


class CreateFileTool(BaseTool[CreateFileInput]):
    """Creates a new file and writes content into it (default: empty content).
    Parent directories are created automatically if they do not exist (no need to call mkdir first).
    Fails if the file already exists.
    Use edit_file to modify existing files."""

    def __init__(self, file_registry: FileRegistry):
        self._file_registry = file_registry

    @property
    def name(self) -> str:
        return "create_file"

    async def __call__(self, tool_input: CreateFileInput) -> ToolResult:
        path = Path(tool_input.path)

        if path.exists():
            return ToolResult(success=False, error=f"File already exists: {path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(tool_input.content)
        self._file_registry.register_file(str(path))
        return ToolResult(success=True, data=f"File created: {path}")
