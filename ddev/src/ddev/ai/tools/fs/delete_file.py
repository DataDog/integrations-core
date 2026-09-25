# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .base import FileRegistryTool
from .file_access_policy import FileAccessError


class DeleteFileInput(BaseToolInput):
    path: Annotated[str, Field(description="Path of the file to delete")]


class DeleteFileTool(FileRegistryTool[DeleteFileInput]):
    """Permanently deletes a single file. Deletion is regulated by the file access policy.
    You must have already read or created the file in this session.

    This cannot be undone, so only delete files you are sure about."""

    @property
    def name(self) -> str:
        return "delete_file"

    async def __call__(self, tool_input: DeleteFileInput) -> ToolResult:
        try:
            path = self._registry.policy.assert_deletable(tool_input.path)
        except FileAccessError as e:
            return ToolResult(success=False, error=str(e))

        async with self._registry.lock_for(str(path)):
            # Verified under the same lock create/edit/append use for their own mutations,
            # so a concurrent write to this path can't slip in between the check and the
            # unlink below and get silently destroyed.
            _, fail = self._read_verified(str(path))
            if fail:
                return fail
            try:
                path.unlink()
            except FileNotFoundError:
                return ToolResult(success=False, error=f"No such file: {path}")
            except OSError as e:
                return ToolResult(success=False, error=str(e))
            self._forget(str(path))
        return ToolResult(success=True, data=f"File deleted: {path}")
