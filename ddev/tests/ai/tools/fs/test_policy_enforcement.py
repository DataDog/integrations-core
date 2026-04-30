# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""End-to-end policy enforcement: tools must respect the two-zone read/write model."""

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
    """Write root — a subdirectory of tmp_path so files at the tmp_path level are outside it."""
    s = tmp_path / "sandbox"
    s.mkdir()
    return s


@pytest.fixture
def sandboxed_registry(sandbox) -> FileRegistry:
    return FileRegistry(policy=FileAccessPolicy(write_root=sandbox))


# ---------------------------------------------------------------------------
# Write tools refuse paths outside write_root
# ---------------------------------------------------------------------------


async def test_create_file_refuses_outside_write_root(tmp_path, sandboxed_registry) -> None:
    tool = CreateFileTool(sandboxed_registry, OWNER_ID)
    outside = tmp_path / "outside.txt"
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
    outside = tmp_path / "outside.txt"
    outside.write_text("old")
    sandboxed_registry.record(OWNER_ID, str(outside), "old")

    tool = EditFileTool(sandboxed_registry, OWNER_ID)
    result = await tool.run({"path": str(outside), "old_string": "old", "new_string": "new"})
    assert result.success is False
    assert "outside write root" in result.error
    assert outside.read_text() == "old"


async def test_append_file_refuses_outside_write_root(tmp_path, sandboxed_registry) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("hello")
    sandboxed_registry.record(OWNER_ID, str(outside), "hello")

    tool = AppendFileTool(sandboxed_registry, OWNER_ID)
    result = await tool.run({"path": str(outside), "content": " world"})
    assert result.success is False
    assert "outside write root" in result.error


async def test_mkdir_refuses_outside_write_root(tmp_path, sandboxed_registry) -> None:
    tool = MkdirTool(sandboxed_registry.policy)
    outside = tmp_path / "outside_dir"
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
# Inside write_root: deny patterns are bypassed for reads and writes
# ---------------------------------------------------------------------------


async def test_write_denied_name_inside_write_root_is_allowed(sandbox, sandboxed_registry) -> None:
    """Agents must be able to write .env and similar files inside their sandbox."""
    tool = CreateFileTool(sandboxed_registry, OWNER_ID)
    target = sandbox / ".env"
    result = await tool.run({"path": str(target), "content": "SECRET=1"})
    assert result.success is True
    assert target.exists()
    assert target.read_text() == "SECRET=1"


async def test_read_denied_name_inside_write_root_is_allowed(sandbox, sandboxed_registry) -> None:
    """Agents must be able to read back files they created inside their sandbox."""
    target = sandbox / ".env"
    target.write_text("SECRET=1")
    sandboxed_registry.record(OWNER_ID, str(target), "SECRET=1")

    tool = ReadFileTool(sandboxed_registry, OWNER_ID)
    result = await tool.run({"path": str(target)})
    assert result.success is True


# ---------------------------------------------------------------------------
# Outside write_root: read denylist still applies
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", [".env", ".envrc", ".netrc", "api.pem", "private.key"])
async def test_read_file_refuses_denied_names_outside_write_root(tmp_path, sandboxed_registry, filename) -> None:
    # Files sit at tmp_path level, which is outside sandbox (the write_root).
    target = tmp_path / filename
    target.write_text("secret")

    tool = ReadFileTool(sandboxed_registry, OWNER_ID)
    result = await tool.run({"path": str(target)})
    assert result.success is False
    assert "Read denied" in result.error


async def test_read_file_allows_normal_files(tmp_path) -> None:
    registry = FileRegistry(policy=FileAccessPolicy(write_root=tmp_path, deny_patterns=()))
    target = tmp_path / "data.txt"
    target.write_text("ok")

    tool = ReadFileTool(registry, OWNER_ID)
    result = await tool.run({"path": str(target)})
    assert result.success is True


# ---------------------------------------------------------------------------
# Per-agent isolation: one agent's read does not authorize another agent's write
# ---------------------------------------------------------------------------


async def test_read_by_one_agent_does_not_authorize_another_to_edit(sandbox) -> None:
    """Agent A reads a file; agent B tries to edit it without reading — must fail."""
    policy = FileAccessPolicy(write_root=sandbox, deny_patterns=())
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
    policy = FileAccessPolicy(write_root=sandbox, deny_patterns=())
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
    # write_root is a subdirectory; the search path at tmp_path level is outside it and denied.
    write_root = tmp_path / "sandbox"
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{tmp_path}/*",))
    tool = GrepTool(policy)
    with patch("ddev.ai.tools.shell.grep.run_command", new=AsyncMock()) as mock_run:
        result = await tool.run({"pattern": "secret", "path": str(tmp_path / "foo")})
    assert result.success is False
    assert "Read denied" in result.error
    mock_run.assert_not_called()


async def test_grep_refuses_denied_name(tmp_path) -> None:
    write_root = tmp_path / "sandbox"
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(".env",))
    tool = GrepTool(policy)
    with patch("ddev.ai.tools.shell.grep.run_command", new=AsyncMock()) as mock_run:
        result = await tool.run({"pattern": "SECRET", "path": str(tmp_path / ".env")})
    assert result.success is False
    assert "Read denied" in result.error
    mock_run.assert_not_called()


async def test_grep_allows_normal_path(tmp_path) -> None:
    target = tmp_path / "data.txt"
    target.write_text("hello world")
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    tool = GrepTool(policy)
    result = await tool.run({"pattern": "hello", "path": str(target)})
    assert result.success is True


async def test_grep_non_recursive_returns_file_matches(tmp_path) -> None:
    """Non-recursive grep on a single file returns actual matches (no post-filter applied)."""
    target = tmp_path / "data.txt"
    target.write_text("hello world\n")
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    tool = GrepTool(policy)
    result = await tool.run({"pattern": "hello", "path": str(target), "recursive": False})
    assert result.success is True
    assert "hello" in (result.data or "")


async def test_grep_inside_write_root_returns_denied_name_files(tmp_path) -> None:
    """Recursive grep inside write_root returns .env and other denied-name files."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / ".env").write_text("SECRET=hello\n")
    policy = FileAccessPolicy(write_root=sandbox, deny_patterns=(".env",))
    tool = GrepTool(policy)
    result = await tool.run({"pattern": "hello", "path": str(sandbox), "recursive": True})
    assert result.success is True
    assert ".env" in (result.data or "")


async def test_grep_post_filter_strips_denied_path_pattern_matches(tmp_path) -> None:
    """Denied path-pattern files are stripped from grep output even when grep walks them."""
    write_root = tmp_path / "sandbox"
    project = tmp_path / "project"
    secrets = tmp_path / "secrets"
    project.mkdir()
    secrets.mkdir()
    (project / "ok.txt").write_text("hello world\n")
    (secrets / "leak.txt").write_text("hello world\n")

    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{secrets}/*",))
    tool = GrepTool(policy)
    result = await tool.run({"pattern": "hello", "path": str(tmp_path), "recursive": True})
    assert result.success is True
    assert "ok.txt" in result.data
    assert "leak.txt: Read denied by policy" in result.data


async def test_grep_post_filter_strips_symlink_to_denied(tmp_path) -> None:
    """A symlink in the search root resolving into a denied tree is filtered out."""
    write_root = tmp_path / "sandbox"
    project = tmp_path / "project"
    secrets = tmp_path / "secrets"
    project.mkdir()
    secrets.mkdir()
    (secrets / "key.txt").write_text("hello world\n")
    (project / "link.txt").symlink_to(secrets / "key.txt")

    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{secrets}/*",))
    tool = GrepTool(policy)
    result = await tool.run({"pattern": "hello", "path": str(project), "recursive": True})
    assert result.success is True
    # link.txt may appear as a denial notice but must not appear as a match line.
    assert "link.txt" not in result.data
    assert result.data


async def test_grep_excludes_basename_pattern_matches(tmp_path) -> None:
    """Basename patterns ride on grep's --exclude flag; verify denied files are absent."""
    write_root = tmp_path / "sandbox"
    project = tmp_path / "project"
    project.mkdir()
    (project / "config.py").write_text("token=abc\n")
    (project / ".env").write_text("token=abc\n")

    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(".env",))
    tool = GrepTool(policy)
    result = await tool.run({"pattern": "token", "path": str(project), "recursive": True})
    assert result.success is True
    assert "config.py" in result.data
    assert ".env" not in result.data


# ---------------------------------------------------------------------------
# Tilde-path canonicalization for write tools
# ---------------------------------------------------------------------------


async def test_create_file_with_tilde_path_writes_to_home_when_authorized(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows uses USERPROFILE, not HOME
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    registry = FileRegistry(policy=policy)
    tool = CreateFileTool(registry, OWNER_ID)

    result = await tool.run({"path": "~/x.txt", "content": "hello"})

    assert result.success is True
    assert (tmp_path / "x.txt").read_text() == "hello"


async def test_create_file_with_tilde_path_refused_when_outside_write_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    policy = FileAccessPolicy(write_root=tmp_path / "sub", deny_patterns=())
    registry = FileRegistry(policy=policy)
    tool = CreateFileTool(registry, OWNER_ID)

    result = await tool.run({"path": "~/x.txt", "content": "hello"})

    assert result.success is False
    assert "outside write root" in result.error
    assert not (tmp_path / "x.txt").exists()
