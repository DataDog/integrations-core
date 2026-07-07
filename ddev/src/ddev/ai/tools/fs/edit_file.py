# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Annotated

from pydantic import Field, model_validator

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .base import FileRegistryTool
from .file_access_policy import FileAccessError


class Edit(BaseToolInput):
    old_string: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Exact non-empty text to replace. Must appear exactly once in the file "
                "and must not be shared with any other edit in this call (hint: include "
                "surrounding context if needed). Keep this to the smallest unique region "
                "that needs changing — do not paste the whole file."
            ),
        ),
    ]
    new_string: Annotated[str, Field(description="Text to replace old_string with.")]


class EditFileInput(BaseToolInput):
    path: Annotated[str, Field(description="Path of the file to edit")]
    edits: Annotated[
        list[Edit],
        Field(
            min_length=1,
            description=(
                "One or more replacements to apply. Each edit is matched against the original "
                "file content, not applied incrementally, so edits must target distinct, "
                "non-overlapping regions. Order in this list does not matter."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _reject_duplicate_old_strings(self) -> EditFileInput:
        first_index: dict[str, int] = {}
        for i, edit in enumerate(self.edits):
            if edit.old_string in first_index:
                j = first_index[edit.old_string]
                raise ValueError(
                    f"edits[{i}].old_string duplicates edits[{j}].old_string; old_string values must be unique"
                )
            first_index[edit.old_string] = i
        return self


class EditFileTool(FileRegistryTool[EditFileInput]):
    """Edits a file by applying one or more exact string replacements in a single call.
    Fails if the file was modified since the last read.
    All edits are matched against the original file content and are applied all-or-nothing:
    if any edit fails, the file is left unchanged.
    Prefer small, targeted edits over large ones: a single edit that spans most of the file can
    exceed the response token limit and be truncated. Break big rewrites into several edits."""

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def truncated_call_hint(self) -> str:
        return (
            "Edit a single small unique region instead of rewriting a whole file. For a full "
            "rewrite, use create_file with a smaller initial chunk, then append_file for the rest."
        )

    async def __call__(self, tool_input: EditFileInput) -> ToolResult:
        try:
            path = self._assert_writable(tool_input.path)
        except FileAccessError as e:
            return ToolResult(success=False, error=str(e))

        async with self._registry.lock_for(str(path)):
            content, fail = self._read_verified(str(path))
            if fail:
                return fail

            # Normalize line endings to avoid issues with different OSs
            content = content.replace("\r\n", "\n")

            matches, fail = self._resolve_matches(content, tool_input.edits)
            if fail:
                return fail

            new_content = content
            for start, end, new_string in reversed(matches):
                new_content = new_content[:start] + new_string + new_content[end:]

            try:
                path.write_text(new_content, encoding="utf-8")
            except OSError as e:
                return ToolResult(success=False, error=str(e))
            self._register(str(path), new_content)
        return ToolResult(success=True, data=f"File edited: {path}")

    def _resolve_matches(self, content: str, edits: list[Edit]) -> tuple[list[tuple[int, int, str]], ToolResult | None]:
        """Match every edit against the original content and detect not-found, ambiguous, and
        overlapping cases. Returns matches sorted by start offset, or a failure ToolResult."""
        matches: list[tuple[int, int, str]] = []  # (start, end, new_string)
        for i, edit in enumerate(edits):
            old_string = edit.old_string.replace("\r\n", "\n")
            new_string = edit.new_string.replace("\r\n", "\n")
            count = content.count(old_string)
            if count == 0:
                return [], ToolResult(success=False, error=f"edits[{i}]: old_string not found in file")
            if count > 1:
                return [], ToolResult(
                    success=False,
                    error=f"edits[{i}]: old_string appears {count} times in the file",
                    hint="include more surrounding context to make it unique",
                )
            start = content.index(old_string)
            matches.append((start, start + len(old_string), new_string))

        matches.sort()
        for (_, prev_end, _), (next_start, _, _) in zip(matches, matches[1:], strict=False):
            if prev_end > next_start:
                return [], ToolResult(
                    success=False,
                    error="edits target overlapping regions of the file; merge them into a single edit",
                )
        return matches, None
