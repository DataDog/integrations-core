# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""End-to-end policy enforcement: tools must refuse denied paths."""

from unittest.mock import AsyncMock, patch

import pytest

from ddev.ai.tools.fs.append_file import AppendFileTool
from ddev.ai.tools.fs.create_file import CreateFileTool
from ddev.ai.tools.fs.edit_file import EditFileTool
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.fs.mkdir import MkdirTool
from ddev.ai.tools.fs.read_file import ReadFileTool
from ddev.ai.tools.shell.grep import GrepTool

OWNER_ID = "test-agent"


@pytest.fixture
def sandbox(tmp_path):
    """Write root = tmp_path, with the default read denylist active."""
    return tmp_path


@pytest.fixture
def sandboxed_registry(sandbox) -> FileRegistry:
    return FileRegistry(policy=FileAccessPolicy(write_root=sandbox))


# ---------------------------------------------------------------------------
# Write tools refuse paths outside write_root
# ---------------------------------------------------------------------------


async def test_create_file_refuses_outside_write_root(tmp_path, sandboxed_registry) -> None:
    tool = CreateFileTool(sandboxed_registry, OWNER_ID)
    outside = tmp_path.parent / "outside.txt"
    result = await tool.run({"path": str(outside), "content": "x"})
    assert result.success is False
    assert "outside write root" in result.error
    assert not outside.exists()


async def test_create_file_allows_inside_write_root(sandbox, sandboxed_registry) -> None:
    tool = CreateFileTool(sandboxed_registry, OWNER_ID)
    target = sandbox / "nested" / "file.txt"
    result = await tool.run({"path": str(target), "content": "x"})
    assert result.success is True
    assert target.read_text() == "x"


async def test_edit_file_refuses_outside_write_root(tmp_path, sandboxed_registry) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("old")
    sandboxed_registry.record(OWNER_ID, str(outside), "old")

    tool = EditFileTool(sandboxed_registry, OWNER_ID)
    result = await tool.run({"path": str(outside), "old_string": "old", "new_string": "new"})
    assert result.success is False
    assert "outside write root" in result.error
    assert outside.read_text() == "old"


async def test_append_file_refuses_outside_write_root(tmp_path, sandboxed_registry) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("hello")
    sandboxed_registry.record(OWNER_ID, str(outside), "hello")

    tool = AppendFileTool(sandboxed_registry, OWNER_ID)
    result = await tool.run({"path": str(outside), "content": " world"})
    assert result.success is False
    assert "outside write root" in result.error


async def test_mkdir_refuses_outside_write_root(tmp_path, sandboxed_registry) -> None:
    tool = MkdirTool(sandboxed_registry.policy)
    outside = tmp_path.parent / "outside_dir"
    result = await tool.run({"path": str(outside)})
    assert result.success is False
    assert "outside write root" in result.error
    assert not outside.exists()


async def test_mkdir_allows_inside_write_root(sandbox, sandboxed_registry) -> None:
    tool = MkdirTool(sandboxed_registry.policy)
    target = sandbox / "a" / "b" / "c"
    result = await tool.run({"path": str(target)})
    assert result.success is True
    assert target.is_dir()


# ---------------------------------------------------------------------------
# Read denylist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", [".env", ".envrc", "id_rsa", "api.pem"])
async def test_read_file_refuses_denied_names(tmp_path, sandboxed_registry, filename) -> None:
    target = tmp_path / filename
    target.write_text("secret")

    tool = ReadFileTool(sandboxed_registry, OWNER_ID)
    result = await tool.run({"path": str(target)})
    assert result.success is False
    assert "Read denied" in result.error


async def test_read_file_allows_normal_files(tmp_path) -> None:
    registry = FileRegistry(policy=FileAccessPolicy(read_deny_roots=()))
    target = tmp_path / "data.txt"
    target.write_text("ok")

    tool = ReadFileTool(registry, OWNER_ID)
    result = await tool.run({"path": str(target)})
    assert result.success is True


async def test_write_to_denied_name_refused(sandbox, sandboxed_registry) -> None:
    tool = CreateFileTool(sandboxed_registry, OWNER_ID)
    target = sandbox / ".env"
    result = await tool.run({"path": str(target), "content": "SECRET=1"})
    assert result.success is False
    assert "Write denied" in result.error
    assert not target.exists()


# ---------------------------------------------------------------------------
# Per-agent isolation: one agent's read does not authorize another agent's write
# ---------------------------------------------------------------------------


async def test_read_by_one_agent_does_not_authorize_another_to_edit(sandbox) -> None:
    """Agent A reads a file; agent B tries to edit it without reading — must fail."""
    policy = FileAccessPolicy(write_root=sandbox, read_deny_names=(), read_deny_roots=())
    registry = FileRegistry(policy=policy)
    target = sandbox / "shared.txt"
    target.write_text("hello")

    reader_a = ReadFileTool(registry, "agent-a")
    result = await reader_a.run({"path": str(target)})
    assert result.success is True

    editor_b = EditFileTool(registry, "agent-b")
    result = await editor_b.run({"path": str(target), "old_string": "hello", "new_string": "world"})
    assert result.success is False
    assert "Not authorized" in result.error
    assert target.read_text() == "hello"


async def test_each_agent_can_edit_after_its_own_read(sandbox) -> None:
    policy = FileAccessPolicy(write_root=sandbox, read_deny_names=(), read_deny_roots=())
    registry = FileRegistry(policy=policy)
    target = sandbox / "shared.txt"
    target.write_text("one")

    # Agent A reads, then edits — ok.
    await ReadFileTool(registry, "agent-a").run({"path": str(target)})
    result = await EditFileTool(registry, "agent-a").run(
        {"path": str(target), "old_string": "one", "new_string": "two"}
    )
    assert result.success is True

    # Agent B must read first to refresh its own view, then may edit.
    await ReadFileTool(registry, "agent-b").run({"path": str(target)})
    result = await EditFileTool(registry, "agent-b").run(
        {"path": str(target), "old_string": "two", "new_string": "three"}
    )
    assert result.success is True
    assert target.read_text() == "three"


# ---------------------------------------------------------------------------
# GrepTool policy enforcement
# ---------------------------------------------------------------------------


async def test_grep_refuses_denied_root(tmp_path) -> None:
    policy = FileAccessPolicy(read_deny_names=(), read_deny_roots=(str(tmp_path),))
    tool = GrepTool(policy)
    with patch("ddev.ai.tools.shell.grep.run_command", new=AsyncMock()) as mock_run:
        result = await tool.run({"pattern": "secret", "path": str(tmp_path / "foo")})
    assert result.success is False
    assert "Read denied" in result.error
    mock_run.assert_not_called()


async def test_grep_refuses_denied_name(tmp_path) -> None:
    policy = FileAccessPolicy(read_deny_names=(".env",), read_deny_roots=())
    tool = GrepTool(policy)
    with patch("ddev.ai.tools.shell.grep.run_command", new=AsyncMock()) as mock_run:
        result = await tool.run({"pattern": "SECRET", "path": str(tmp_path / ".env")})
    assert result.success is False
    assert "Read denied" in result.error
    mock_run.assert_not_called()


async def test_grep_allows_normal_path(tmp_path) -> None:
    target = tmp_path / "data.txt"
    target.write_text("hello world")
    policy = FileAccessPolicy(read_deny_names=(), read_deny_roots=())
    tool = GrepTool(policy)
    result = await tool.run({"pattern": "hello", "path": str(target)})
    assert result.success is True


# ---------------------------------------------------------------------------
# Tilde-path canonicalization for write tools
# ---------------------------------------------------------------------------


async def test_create_file_with_tilde_path_writes_to_home_when_authorized(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows uses USERPROFILE, not HOME
    policy = FileAccessPolicy(write_root=tmp_path, read_deny_names=(), read_deny_roots=())
    registry = FileRegistry(policy=policy)
    tool = CreateFileTool(registry, OWNER_ID)

    result = await tool.run({"path": "~/x.txt", "content": "hello"})

    assert result.success is True
    assert (tmp_path / "x.txt").read_text() == "hello"


async def test_create_file_with_tilde_path_refused_when_outside_write_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    policy = FileAccessPolicy(write_root=tmp_path / "sub", read_deny_names=(), read_deny_roots=())
    registry = FileRegistry(policy=policy)
    tool = CreateFileTool(registry, OWNER_ID)

    result = await tool.run({"path": "~/x.txt", "content": "hello"})

    assert result.success is False
    assert "outside write root" in result.error
    assert not (tmp_path / "x.txt").exists()
