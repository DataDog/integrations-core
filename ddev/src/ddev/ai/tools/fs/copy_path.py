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
    overwrite: Annotated[
        bool,
        Field(
            description="If True, overwrite existing files at the destination. "
            "Defaults to False; set to True only when you are sure you want to replace existing files.",
        ),
    ] = False


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
            if source.is_dir():
                for entry in source.rglob("*"):
                    if entry.is_file() or entry.is_symlink():
                        try:
                            self._policy.assert_readable(entry)
                        except FileAccessError as e:
                            return ToolResult(success=False, error=str(e))
            destination = self._policy.assert_writable(tool_input.destination)
            if destination.is_dir():
                for entry in destination.rglob("*"):
                    if entry.is_symlink() and entry.is_dir():
                        self._policy.assert_writable(entry.resolve())
        except FileAccessError as e:
            return ToolResult(success=False, error=str(e))

        if not source.exists():
            return ToolResult(success=False, error=f"Source does not exist: {source}")

        try:
            if source.is_dir():
                if not tool_input.overwrite:
                    conflicts = [
                        str(destination / p.relative_to(source))
                        for p in source.rglob("*")
                        if p.is_file() and (destination / p.relative_to(source)).exists()
                    ]
                    if conflicts:
                        listed = "\n".join(f"  {c}" for c in conflicts)
                        return ToolResult(
                            success=False,
                            error=(
                                f"Copy aborted: {len(conflicts)} file(s) already exist at the destination "
                                f"and would be overwritten:\n{listed}"
                            ),
                            hint="Set overwrite=True to replace them.",
                        )
                shutil.copytree(source, destination, dirs_exist_ok=True)
                file_count = sum(1 for p in source.rglob("*") if p.is_file())
                return ToolResult(success=True, data=f"Copied directory tree to {destination} ({file_count} files).")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not tool_input.overwrite and destination.exists():
                return ToolResult(
                    success=False,
                    error=(f"Copy aborted: destination already exists: {destination}. "),
                    hint="Set overwrite=True to replace it.",
                )
            shutil.copy2(source, destination)
            size = Path(destination).stat().st_size
            return ToolResult(success=True, data=f"Copied file to {destination} ({size} bytes).")
        except OSError as e:
            return ToolResult(success=False, error=str(e))
