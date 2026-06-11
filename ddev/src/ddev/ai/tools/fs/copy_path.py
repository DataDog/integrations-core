# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import shutil
from pathlib import Path
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .file_access_policy import FileAccessError, FileAccessPolicy


class CopyPathInput(BaseToolInput):
    source: Annotated[str, Field(description="Path to copy from (a file or a directory).")]
    destination: Annotated[
        str,
        Field(
            description="Path to copy to. For a file source this is the target file path;"
            " for a directory source it is the target directory."
        ),
    ]


class CopyPathTool(BaseTool[CopyPathInput]):
    """Copies a file or a whole directory tree from source to destination, byte-for-byte,
    without reading the content into the conversation.
    It is the only correct way to copy large or binary files.
    Missing parent directories are created."""

    def __init__(self, policy: FileAccessPolicy) -> None:
        self._policy = policy

    @property
    def name(self) -> str:
        return "copy_path"

    async def __call__(self, tool_input: CopyPathInput) -> ToolResult:
        try:
            source = self._policy.assert_readable(tool_input.source)
            destination = self._policy.assert_writable(tool_input.destination)
        except FileAccessError as e:
            return ToolResult(success=False, error=str(e))

        if not source.exists():
            return ToolResult(success=False, error=f"Source does not exist: {source}")

        try:
            if source.is_dir():
                for entry in source.rglob("*"):
                    try:
                        self._policy.assert_readable(entry)
                    except FileAccessError as e:
                        return ToolResult(success=False, error=str(e))
                shutil.copytree(source, destination, dirs_exist_ok=True)
                file_count = sum(1 for p in destination.rglob("*") if p.is_file())
                return ToolResult(success=True, data=f"Copied directory tree to {destination} ({file_count} files).")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            size = Path(destination).stat().st_size
            return ToolResult(success=True, data=f"Copied file to {destination} ({size} bytes).")
        except OSError as e:
            return ToolResult(success=False, error=str(e))
