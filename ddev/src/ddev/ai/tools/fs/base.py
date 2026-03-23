# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .file_registry import FileRegistry


class FileRegistryTool[TInput: BaseToolInput](BaseTool[TInput]):
    """Abstract base for file system tools with hash-based consistency checks."""

    def __init__(self, file_registry: FileRegistry) -> None:
        self._registry = file_registry

    def _refresh_if_known(self, path: str, content: str) -> None:
        if self._registry.is_known(path):
            self._registry.record(path, content)

    def _register(self, path: str, content: str) -> None:
        self._registry.record(path, content)

    def _read_verified(self, path: str) -> tuple[str, ToolResult | None]:
        """Read file content and verify it matches the last recorded hash."""
        if not self._registry.is_known(path):
            return "", ToolResult(success=False, error=f"Not authorized to modify '{path}'.")
        try:
            content = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            return "", ToolResult(success=False, error=str(e))
        if not self._registry.verify(path, content):
            return "", ToolResult(success=False, error=f"File '{path}' has changed since last read. Re-read and retry.")
        return content, None
