# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from fnmatch import fnmatch
from pathlib import Path
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .base import FileRegistryTool
from .file_access_policy import FileAccessError, canonicalize_path
from .file_registry import FileRegistry

# Relative to the integration root. These are owned by `ddev validate`/scaffolding rather
# than the agent, so the correct way to change them is to edit the spec and regenerate, not
# delete and recreate. fnmatch treats "*" as matching any characters including "/", so "**"
# below is equivalent to "*" and matches any depth.
PROTECTED_STRUCTURAL_PATTERNS: tuple[str, ...] = (
    "manifest.json",
    "pyproject.toml",
    "hatch.toml",
    "metadata.csv",
    "README.md",
    "assets/configuration/spec.yaml",
    "datadog_checks/*/config_models/**",
    "datadog_checks/*/data/conf.yaml.example",
)


def is_protected_structural_path(relative: Path) -> bool:
    """Whether a path, relative to the integration root, is a protected structural file."""
    rel = relative.as_posix()
    return any(fnmatch(rel, pattern) for pattern in PROTECTED_STRUCTURAL_PATTERNS)


class DeleteFileInput(BaseToolInput):
    path: Annotated[str, Field(description="Path of the file to delete")]


class DeleteFileTool(FileRegistryTool[DeleteFileInput]):
    """Permanently deletes a single file inside the current integration's directory.
    Use this to remove a file you created or read earlier in this session that turned out
    to be wrong or unwanted. You must have already read or created the file in this session;
    read it first if you haven't.

    This cannot be undone, so only delete files you are sure about."""

    def __init__(self, file_registry: FileRegistry, owner_id: str, integration_root: Path | None) -> None:
        super().__init__(file_registry, owner_id)
        # Canonicalized so the boundary check below compares against the same resolved
        # form `_assert_writable` produces, even if a parent directory is a symlink
        # (e.g. macOS's /tmp -> /private/tmp).
        self._integration_root = canonicalize_path(integration_root) if integration_root is not None else None

    @property
    def name(self) -> str:
        return "delete_file"

    async def __call__(self, tool_input: DeleteFileInput) -> ToolResult:
        if self._integration_root is None:
            return ToolResult(
                success=False,
                error="delete_file is unavailable: this run has no resolved integration directory.",
            )

        # `canonicalize_path` (via `_assert_writable`) fully resolves symlinks, including a
        # symlink leaf itself, so it can never be used to detect that the leaf is a symlink.
        # Check that on the pre-resolution path instead, before it's resolved away.
        is_symlink_leaf = Path(tool_input.path).expanduser().is_symlink()

        try:
            path = self._assert_writable(tool_input.path)
        except FileAccessError as e:
            return ToolResult(success=False, error=str(e))

        if not path.is_relative_to(self._integration_root):
            return ToolResult(
                success=False,
                error=f"Delete denied: {path} is outside the integration directory {self._integration_root}",
            )

        if is_symlink_leaf:
            return ToolResult(success=False, error=f"Delete denied: {path} is a symlink")

        if path.is_dir():
            return ToolResult(success=False, error=f"Delete denied: {path} is a directory")

        if is_protected_structural_path(path.relative_to(self._integration_root)):
            return ToolResult(success=False, error=f"Delete denied: {path} is a protected structural file")

        if self._registry.policy.matches_deny_pattern(path):
            return ToolResult(success=False, error=f"Delete denied by policy: {path}")

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
