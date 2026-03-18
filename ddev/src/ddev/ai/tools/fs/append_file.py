# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from ddev.ai.tools.core.types import ToolResult

from .base import TextEdit


@dataclass
class AppendFileInput:
    path: Annotated[str, "Path of the file to append to"]
    content: Annotated[str, "Content to append to the file"]


class AppendFileTool(TextEdit[AppendFileInput]):
    """Appends content to the end of an existing file.
    The file must have been read first. Fails if the file was modified since the last read."""

    @property
    def name(self) -> str:
        return "append_file"

    async def __call__(self, tool_input: AppendFileInput) -> ToolResult:
        path = Path(tool_input.path)

        async with self._registry.get_lock(str(path)):
            current_content, fail = self._read_verified(str(path))
            if fail:
                return fail

            content_to_append = tool_input.content.replace("\r\n", "\n")
            separator = "" if not current_content or current_content.endswith("\n") else "\n"
            new_content = current_content + separator + content_to_append

            path.write_text(new_content, encoding="utf-8")
            self._on_write(str(path), new_content)
        return ToolResult(success=True, data=f"Content appended to: {path}")
