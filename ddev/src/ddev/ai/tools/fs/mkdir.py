# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .base import FileRegistryTool


class MkdirInput(BaseToolInput):
    path: Annotated[str, Field(description="Path of the directory to create")]


class MkdirTool(FileRegistryTool[MkdirInput]):
    """Creates a directory at the given path, including any missing parent directories.
    Use to create directories for config files, logs, source code.
    Writes are restricted to the configured write root."""

    @property
    def name(self) -> str:
        return "mkdir"

    async def __call__(self, tool_input: MkdirInput) -> ToolResult:
        if fail := self._assert_writable(tool_input.path):
            return fail
        path = Path(tool_input.path).expanduser().resolve()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return ToolResult(success=False, error=str(e))
        return ToolResult(success=True, data=f"Directory created: {path}")
