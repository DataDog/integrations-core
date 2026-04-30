# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .file_registry import FileRegistry


class FileRegistryTool[TInput: BaseToolInput](BaseTool[TInput]):
    """Abstract base for file system tools with hash-based consistency checks.

    Each tool instance is bound to an owner_id; all registry operations run
    under that identity so read-before-write is enforced per owner.
    """

    def __init__(self, file_registry: FileRegistry, owner_id: str) -> None:
        self._registry = file_registry
        self._owner_id = owner_id

    def _register(self, path: str, content: str) -> None:
        self._registry.record(self._owner_id, path, content)

    def _assert_writable(self, path: str) -> Path:
        return self._registry.policy.assert_writable(path)

    def _assert_readable(self, path: str) -> Path:
        return self._registry.policy.assert_readable(path)

    def _read_verified(self, path: str) -> tuple[str, ToolResult | None]:
        """Read file content and verify it matches this agent's last recorded hash."""
        if not self._registry.is_known(self._owner_id, path):
            return "", ToolResult(success=False, error=f"Not authorized to modify '{path}'.")
        try:
            content = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return "", ToolResult(success=False, error=str(e))
        if not self._registry.verify(self._owner_id, path, content):
            return "", ToolResult(success=False, error=f"File '{path}' has changed since last read. Re-read and retry.")
        return content, None
