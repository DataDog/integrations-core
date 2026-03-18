# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from typing import Annotated

import pytest

from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.fs.base import TextEdit
from ddev.ai.tools.fs.file_registry import FileRegistry

# ---------------------------------------------------------------------------
# Minimal concrete subclass for testing
# ---------------------------------------------------------------------------


@dataclass
class DummyInput:
    path: Annotated[str, "Path"]


class DummyTool(TextEdit[DummyInput]):
    """Dummy tool to test TextEdit base behavior."""

    @property
    def name(self) -> str:
        return "dummy"

    async def __call__(self, tool_input: DummyInput) -> ToolResult:
        return ToolResult(success=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry() -> FileRegistry:
    return FileRegistry()


@pytest.fixture
def tool(registry: FileRegistry) -> DummyTool:
    return DummyTool(registry)


# ---------------------------------------------------------------------------
# _read_verified
# ---------------------------------------------------------------------------


def test_read_verified_fails_if_not_known(tool: DummyTool, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    content, error = tool._read_verified(path)

    assert content == ""
    assert error is not None
    assert error.success is False
    assert "read the file first" in error.error


def test_read_verified_fails_if_file_changed_externally(tool: DummyTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("original", encoding="utf-8")
    registry.record(str(f), "original")

    f.write_text("modified", encoding="utf-8")

    content, error = tool._read_verified(str(f))

    assert content == ""
    assert error is not None
    assert error.success is False
    assert "Re-read and retry" in error.error


def test_read_verified_succeeds_if_content_matches(tool: DummyTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("hello", encoding="utf-8")
    registry.record(str(f), "hello")

    content, error = tool._read_verified(str(f))

    assert error is None
    assert content == "hello"


def test_read_verified_handles_oserror(tool: DummyTool, registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "ghost.txt")
    # Record the path so it passes the is_known check, but never create the file
    registry.record(path, "anything")

    content, error = tool._read_verified(path)

    assert content == ""
    assert error is not None
    assert error.success is False


# ---------------------------------------------------------------------------
# _on_read / _on_write
# ---------------------------------------------------------------------------


def test_on_read_registers_path(tool: DummyTool, registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    tool._on_read(path, "content")

    assert registry.is_known(path) is True
    assert registry.verify(path, "content") is True


def test_on_write_registers_path(tool: DummyTool, registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    tool._on_write(path, "written")

    assert registry.is_known(path) is True
    assert registry.verify(path, "written") is True


def test_on_write_updates_hash_after_on_read(tool: DummyTool, registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    tool._on_read(path, "old")
    tool._on_write(path, "new")

    assert registry.verify(path, "new") is True
    assert registry.verify(path, "old") is False
