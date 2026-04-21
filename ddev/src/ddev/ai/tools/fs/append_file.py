# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult
from ddev.utils.fs import pretty_path

from .base import FileRegistryTool


class AppendFileInput(BaseToolInput):
    path: Annotated[str, Field(description="Path of the file to append to")]
    content: Annotated[str, Field(description="Content to append to the file")]
    expected_hash: Annotated[
        str | None,
        Field(
            description=(
                "Optional sha256 hex digest of the file's current content. If provided and "
                "it matches the file on disk, the call skips the read-before-write check. "
                "Use the sha256 value returned in metadata by a previous read_file / create_file / "
                "edit_file / append_file on this path to avoid re-reading."
            ),
        ),
    ] = None


class AppendFileTool(FileRegistryTool[AppendFileInput]):
    """Appends content to the end of an existing file.
    Fails if the file was modified since the last read (unless expected_hash is supplied and matches).

    The response metadata includes sha256=<hex>, the new content's hash."""

    @property
    def name(self) -> str:
        return "append_file"

    def format_call(self, raw_input: dict[str, object]) -> str:
        path = raw_input.get('path', '')
        return f"{self.name} {pretty_path(path) if path else ''}".rstrip()

    async def __call__(self, tool_input: AppendFileInput) -> ToolResult:
        if fail := self._assert_writable(tool_input.path):
            return fail
        path = Path(tool_input.path).resolve()

        async with self._registry.lock_for(str(path)):
            current_content, fail = self._read_verified(str(path), expected_hash=tool_input.expected_hash)
            if fail:
                return fail

            content_to_append = tool_input.content.replace("\r\n", "\n")
            separator = "" if not current_content or current_content.endswith("\n") else "\n"
            new_content = current_content + separator + content_to_append

            try:
                path.write_text(new_content, encoding="utf-8")
            except OSError as e:
                return ToolResult(success=False, error=str(e))
            self._register(str(path), new_content)
        return ToolResult(
            success=True,
            data=f"Content appended to: {path}",
            metadata={"sha256": self._registry.hash(new_content)},
        )
