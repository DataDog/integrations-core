# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .file_access_policy import FileAccessError
from .file_registry import FileRegistry


class FileRegistryTool[TInput: BaseToolInput](BaseTool[TInput]):
    """Abstract base for file system tools with hash-based consistency checks.

    Each tool instance is bound to an agent_id; all registry operations run
    under that identity so read-before-write is enforced per agent.
    """

    def __init__(self, file_registry: FileRegistry, agent_id: str) -> None:
        self._registry = file_registry
        self._agent_id = agent_id

    def _register(self, path: str, content: str) -> None:
        self._registry.record(self._agent_id, path, content)

    def _assert_writable(self, path: str) -> ToolResult | None:
        try:
            self._registry.policy.assert_writable(path)
        except FileAccessError as e:
            return ToolResult(success=False, error=str(e))
        return None

    def _assert_readable(self, path: str) -> ToolResult | None:
        try:
            self._registry.policy.assert_readable(path)
        except FileAccessError as e:
            return ToolResult(success=False, error=str(e))
        return None

    def _read_verified(self, path: str, expected_hash: str | None = None) -> tuple[str, ToolResult | None]:
        """Read file content and verify it matches either an expected_hash or this agent's last recorded hash.

        When expected_hash is provided, the on-disk hash is compared against it directly,
        bypassing the read-before-write registry check. On a match the registry is
        updated for this agent so subsequent writes work without re-supplying the hash.
        """
        if expected_hash is None and not self._registry.is_known(self._agent_id, path):
            return "", ToolResult(
                success=False,
                error=(
                    f"Not authorized to modify '{path}'. Read the file first, "
                    f"or pass expected_hash if you already know its current sha256."
                ),
            )

        try:
            content = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            return "", ToolResult(success=False, error=str(e))

        if expected_hash is not None:
            actual = self._registry.hash(content)
            if actual != expected_hash:
                return "", ToolResult(
                    success=False,
                    error=(
                        f"expected_hash mismatch for '{path}' "
                        f"(actual sha256={actual}). Re-read the file or drop expected_hash."
                    ),
                )
            self._register(path, content)
            return content, None

        if not self._registry.verify(self._agent_id, path, content):
            return "", ToolResult(success=False, error=f"File '{path}' has changed since last read. Re-read and retry.")
        return content, None
