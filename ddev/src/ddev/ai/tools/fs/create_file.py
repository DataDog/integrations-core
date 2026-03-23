# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .base import FileRegistryTool


class CreateFileInput(BaseToolInput):
    path: Annotated[str, Field(description="Path of the file to create")]
    content: Annotated[str, Field(description="Content of the file to create")] = ""


class CreateFileTool(FileRegistryTool[CreateFileInput]):
    """Creates a new file and writes content into it (default: empty content).
    Parent directories are created automatically if they do not exist (no need to call mkdir first).
    Registers the file in the file registry.
    Fails if the file already exists.
    Use edit_file to modify existing files."""

    @property
    def name(self) -> str:
        return "create_file"

    async def __call__(self, tool_input: CreateFileInput) -> ToolResult:
        path = Path(tool_input.path).resolve()

        async with self._registry.lock_for(str(path)):
            if path.exists():
                return ToolResult(success=False, error=f"File already exists: {path}")

            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(tool_input.content, encoding="utf-8")
            except OSError as e:
                return ToolResult(success=False, error=str(e))
            self._register(str(path), tool_input.content)
        return ToolResult(success=True, data=f"File created: {path}")
