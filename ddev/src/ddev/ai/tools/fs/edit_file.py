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


class EditFileInput(BaseToolInput):
    path: Annotated[str, Field(description="Path of the file to edit")]
    old_string: Annotated[
        str,
        Field(
            description=(
                "Exact text to replace. Must appear exactly once in the file "
                "(hint: include surrounding context if needed). "
                "Special case: pass an empty string to populate a file that is currently empty; "
                "the call fails if the file is not actually empty."
            ),
        ),
    ]
    new_string: Annotated[str, Field(description="Text to replace old_string with")]
    expected_hash: Annotated[
        str | None,
        Field(
            description=(
                "Optional sha256 hex digest of the file's current content. If provided and "
                "it matches the file on disk, the call skips the read-before-write check. "
                "Use the sha256 value returned in metadata by a previous call to any tool "
                "that reads or writes files on this path to avoid re-reading."
            ),
        ),
    ] = None


class EditFileTool(FileRegistryTool[EditFileInput]):
    """Edits a file by replacing an exact string with a new one.
    Fails if the file was modified since the last read (unless expected_hash is supplied and matches).
    old_string must appear exactly once in the file — if it appears multiple times, the call fails.

    The response metadata includes sha256=<hex>, the new content's hash."""

    @property
    def name(self) -> str:
        return "edit_file"

    def format_call(self, raw_input: dict[str, object]) -> str:
        path = raw_input.get('path', '')
        return f"{self.name} {pretty_path(path) if path else ''}".rstrip()

    async def __call__(self, tool_input: EditFileInput) -> ToolResult:
        if fail := self._assert_writable(tool_input.path):
            return fail
        path = Path(tool_input.path).resolve()

        async with self._registry.lock_for(str(path)):
            content, fail = self._read_verified(str(path), expected_hash=tool_input.expected_hash)
            if fail:
                return fail

            # Normalize line endings to avoid issues with different OSs
            old_string = tool_input.old_string.replace("\r\n", "\n")
            new_string = tool_input.new_string.replace("\r\n", "\n")

            if old_string == "":
                if content != "":
                    return ToolResult(
                        success=False,
                        error="old_string is empty but the file is not empty; provide the exact text to replace",
                    )
                new_content = new_string
            else:
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
            self._register(str(path), new_content)
        return ToolResult(
            success=True,
            data=f"File edited: {path}",
            metadata={"sha256": self._registry.hash(new_content)},
        )
