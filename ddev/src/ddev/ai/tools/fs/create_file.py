# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .base import FileRegistryTool
from .file_access_policy import FileAccessError


class CreateFileInput(BaseToolInput):
    path: Annotated[str, Field(description="Path of the file to create")]
    content: Annotated[str, Field(description="Content of the file to create")] = ""
    replace_if_existing: Annotated[
        bool,
        Field(description="If the file already exists, overwrite its content instead of failing"),
    ] = False


class CreateFileTool(FileRegistryTool[CreateFileInput]):
    """Creates a new file and writes content into it (default: empty content).
    Parent directories are created automatically if they do not exist (no need to call mkdir first).
    Registers the file in the file registry.
    Fails if the file already exists, unless replace_if_existing is set.
    Use edit_file to modify existing files."""

    @property
    def name(self) -> str:
        return "create_file"

    @property
    def truncated_call_hint(self) -> str:
        return (
            "Write a smaller initial chunk of the file now, then use append_file to add the "
            "remaining content across one or more follow-up calls."
        )

    async def __call__(self, tool_input: CreateFileInput) -> ToolResult:
        try:
            path = self._assert_writable(tool_input.path)
        except FileAccessError as e:
            return ToolResult(success=False, error=str(e))

        async with self._registry.lock_for(str(path)):
            if tool_input.replace_if_existing:
                already_existed = path.exists()
                if already_existed:
                    _, fail = self._read_verified(str(path))
                    if fail:
                        return fail
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(tool_input.content, encoding="utf-8")
                except OSError as e:
                    return ToolResult(success=False, error=str(e))
                self._register(str(path), tool_input.content)
                verb = "replaced" if already_existed else "created"
                return ToolResult(success=True, data=f"File {verb}: {path}")

            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "x", encoding="utf-8") as fh:
                    fh.write(tool_input.content)
            except FileExistsError:
                return ToolResult(success=False, error=f"File already exists: {path}")
            except OSError as e:
                return ToolResult(success=False, error=str(e))
            self._register(str(path), tool_input.content)
        return ToolResult(success=True, data=f"File created: {path}")
