# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio

import pytest

from ddev.ai.tools.fs.append_file import AppendFileTool
from ddev.ai.tools.fs.create_file import CreateFileTool
from ddev.ai.tools.fs.edit_file import EditFileTool
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.fs.read_file import ReadFileTool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry() -> FileRegistry:
    return FileRegistry()


@pytest.fixture
def read_tool(registry: FileRegistry) -> ReadFileTool:
    return ReadFileTool(registry)


@pytest.fixture
def create_tool(registry: FileRegistry) -> CreateFileTool:
    return CreateFileTool(registry)


@pytest.fixture
def edit_tool(registry: FileRegistry) -> EditFileTool:
    return EditFileTool(registry)


@pytest.fixture
def append_tool(registry: FileRegistry) -> AppendFileTool:
    return AppendFileTool(registry)


@pytest.fixture
def known_file(tmp_path, read_tool: ReadFileTool):
    """A temp file pre-registered in the registry via a read."""
    f = tmp_path / "file.txt"
    f.write_text("line one\nline two\nline three\n", encoding="utf-8")
    asyncio.run(read_tool.run({"path": str(f)}))
    return f


# ---------------------------------------------------------------------------
# ReadFileTool
# ---------------------------------------------------------------------------


def test_read_file_tool_meta(read_tool: ReadFileTool) -> None:
    assert read_tool.name == "read_file"


def test_read_file_success(read_tool: ReadFileTool, tmp_path) -> None:
    f = tmp_path / "config.txt"
    f.write_text("hello\nworld\n", encoding="utf-8")

    result = asyncio.run(read_tool.run({"path": str(f)}))

    assert result.success is True
    assert result.data == "hello\nworld\n"


def test_read_file_registers_in_registry(read_tool: ReadFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("content", encoding="utf-8")

    asyncio.run(read_tool.run({"path": str(f)}))

    assert registry.is_known(str(f)) is True
    assert registry.verify(str(f), "content") is True


def test_read_file_missing_file(read_tool: ReadFileTool, tmp_path) -> None:
    result = asyncio.run(read_tool.run({"path": str(tmp_path / "ghost.txt")}))

    assert result.success is False
    assert result.error is not None


@pytest.mark.parametrize(
    "offset, limit, expected",
    [
        (1, None, "b\nc\n"),
        (0, 2, "a\nb\n"),
        (1, 2, "b\nc\n"),
        (1, 1, "b\n"),
        (2, 10, "c\n"),  # limit exceeds remaining lines
        (100, None, ""),  # offset beyond EOF
        (0, 0, "a\n"),  # limit 0 is clamped to 1
        (1.9, 1, "b\n"),  # safe_int coercion
    ],
)
def test_read_file_with_offset_and_limit(read_tool: ReadFileTool, tmp_path, offset, limit, expected) -> None:
    f = tmp_path / "file.txt"
    f.write_text("a\nb\nc\n", encoding="utf-8")

    result = asyncio.run(read_tool.run({"path": str(f), "offset": offset, "limit": limit}))

    assert result.success is True
    assert result.data == expected


def test_read_file_no_trailing_newline(read_tool: ReadFileTool, tmp_path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("no newline at end", encoding="utf-8")

    result = asyncio.run(read_tool.run({"path": str(f)}))

    assert result.success is True
    assert result.data == "no newline at end"


# ---------------------------------------------------------------------------
# CreateFileTool
# ---------------------------------------------------------------------------


def test_create_file_tool_meta(create_tool: CreateFileTool) -> None:
    assert create_tool.name == "create_file"


def test_create_file_success(create_tool: CreateFileTool, tmp_path) -> None:
    f = tmp_path / "new.txt"

    result = asyncio.run(create_tool.run({"path": str(f), "content": "hello"}))

    assert result.success is True
    assert f.read_text(encoding="utf-8") == "hello"


def test_create_file_default_empty_content(create_tool: CreateFileTool, tmp_path) -> None:
    f = tmp_path / "empty.txt"

    result = asyncio.run(create_tool.run({"path": str(f)}))

    assert result.success is True
    assert f.read_text(encoding="utf-8") == ""


def test_create_file_creates_missing_parent_dirs(create_tool: CreateFileTool, tmp_path) -> None:
    f = tmp_path / "a" / "b" / "c" / "file.txt"

    result = asyncio.run(create_tool.run({"path": str(f), "content": "nested"}))

    assert result.success is True
    assert f.exists()
    assert f.read_text(encoding="utf-8") == "nested"


def test_create_file_fails_if_file_already_exists(create_tool: CreateFileTool, tmp_path) -> None:
    f = tmp_path / "existing.txt"
    f.write_text("original", encoding="utf-8")

    result = asyncio.run(create_tool.run({"path": str(f), "content": "new"}))

    assert result.success is False
    assert result.error is not None
    # Original file must be untouched
    assert f.read_text(encoding="utf-8") == "original"


def test_create_file_registers_in_registry(create_tool: CreateFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "file.txt"

    asyncio.run(create_tool.run({"path": str(f), "content": "hi"}))

    assert registry.is_known(str(f)) is True
    assert registry.verify(str(f), "hi") is True


# ---------------------------------------------------------------------------
# EditFileTool
# ---------------------------------------------------------------------------


def test_edit_file_tool_meta(edit_tool: EditFileTool) -> None:
    assert edit_tool.name == "edit_file"


def test_edit_file_success(edit_tool: EditFileTool, known_file) -> None:
    result = asyncio.run(edit_tool.run({"path": str(known_file), "old_string": "line two", "new_string": "line TWO"}))

    assert result.success is True
    assert "line TWO" in known_file.read_text(encoding="utf-8")
    assert "line two" not in known_file.read_text(encoding="utf-8")


def test_edit_file_requires_prior_read(edit_tool: EditFileTool, tmp_path) -> None:
    f = tmp_path / "unread.txt"
    f.write_text("content", encoding="utf-8")

    result = asyncio.run(edit_tool.run({"path": str(f), "old_string": "content", "new_string": "new"}))

    assert result.success is False
    assert "read the file first" in result.error


def test_edit_file_fails_if_old_string_not_found(edit_tool: EditFileTool, known_file) -> None:
    result = asyncio.run(edit_tool.run({"path": str(known_file), "old_string": "does not exist", "new_string": "x"}))

    assert result.success is False
    assert "not found" in result.error


def test_edit_file_fails_if_old_string_empty(edit_tool: EditFileTool, known_file) -> None:
    result = asyncio.run(edit_tool.run({"path": str(known_file), "old_string": "", "new_string": "x"}))

    assert result.success is False
    assert "not found" in result.error


def test_edit_file_fails_if_old_string_ambiguous(edit_tool: EditFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "dup.txt"
    f.write_text("foo\nfoo\nfoo\n", encoding="utf-8")
    asyncio.run(ReadFileTool(registry).run({"path": str(f)}))

    result = asyncio.run(edit_tool.run({"path": str(f), "old_string": "foo", "new_string": "bar"}))

    assert result.success is False
    assert "3" in result.error
    assert result.hint is not None


def test_edit_file_fails_if_file_changed_externally(edit_tool: EditFileTool, known_file) -> None:
    known_file.write_text("externally modified\n", encoding="utf-8")

    result = asyncio.run(edit_tool.run({"path": str(known_file), "old_string": "line one", "new_string": "x"}))

    assert result.success is False
    assert "Re-read and retry" in result.error


def test_edit_file_updates_registry(edit_tool: EditFileTool, registry: FileRegistry, known_file) -> None:
    asyncio.run(edit_tool.run({"path": str(known_file), "old_string": "line one", "new_string": "LINE ONE"}))

    new_content = known_file.read_text(encoding="utf-8")
    assert registry.verify(str(known_file), new_content) is True
    assert registry.verify(str(known_file), "line one\nline two\nline three\n") is False


def test_edit_file_normalizes_crlf_in_old_string(edit_tool: EditFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("line one\nline two\n", encoding="utf-8")
    asyncio.run(ReadFileTool(registry).run({"path": str(f)}))

    # old_string uses CRLF — should still match the LF content on disk
    result = asyncio.run(
        edit_tool.run({"path": str(f), "old_string": "line one\r\nline two", "new_string": "replaced"})
    )

    assert result.success is True
    assert f.read_text(encoding="utf-8") == "replaced\n"


def test_edit_file_normalizes_crlf_in_new_string(edit_tool: EditFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("line one\n", encoding="utf-8")
    asyncio.run(ReadFileTool(registry).run({"path": str(f)}))

    result = asyncio.run(edit_tool.run({"path": str(f), "old_string": "line one", "new_string": "A\r\nB"}))

    assert result.success is True
    assert f.read_text(encoding="utf-8") == "A\nB\n"


def test_edit_file_new_string_can_be_empty(edit_tool: EditFileTool, known_file) -> None:
    # Replacing with empty string is a valid deletion
    result = asyncio.run(edit_tool.run({"path": str(known_file), "old_string": "line two\n", "new_string": ""}))

    assert result.success is True
    assert "line two" not in known_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AppendFileTool
# ---------------------------------------------------------------------------


def test_append_file_tool_meta(append_tool: AppendFileTool) -> None:
    assert append_tool.name == "append_file"


def test_append_file_success(append_tool: AppendFileTool, known_file) -> None:
    result = asyncio.run(append_tool.run({"path": str(known_file), "content": "line four\n"}))

    assert result.success is True
    assert known_file.read_text(encoding="utf-8").endswith("line four\n")


def test_append_file_requires_prior_read(append_tool: AppendFileTool, tmp_path) -> None:
    f = tmp_path / "unread.txt"
    f.write_text("content", encoding="utf-8")

    result = asyncio.run(append_tool.run({"path": str(f), "content": "more"}))

    assert result.success is False
    assert "read the file first" in result.error


def test_append_file_adds_separator_when_no_trailing_newline(
    append_tool: AppendFileTool, registry: FileRegistry, tmp_path
) -> None:
    f = tmp_path / "file.txt"
    f.write_text("no newline", encoding="utf-8")
    asyncio.run(ReadFileTool(registry).run({"path": str(f)}))

    asyncio.run(append_tool.run({"path": str(f), "content": "appended"}))

    assert f.read_text(encoding="utf-8") == "no newline\nappended"


def test_append_file_no_separator_when_trailing_newline(append_tool: AppendFileTool, known_file) -> None:
    # known_file ends with \n already
    asyncio.run(append_tool.run({"path": str(known_file), "content": "appended"}))

    text = known_file.read_text(encoding="utf-8")
    assert "three\nappended" in text  # no double newline between existing content and appended


def test_append_file_empty_file(append_tool: AppendFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    asyncio.run(ReadFileTool(registry).run({"path": str(f)}))

    result = asyncio.run(append_tool.run({"path": str(f), "content": "first line"}))

    assert result.success is True
    assert f.read_text(encoding="utf-8") == "first line"


def test_append_file_fails_if_file_changed_externally(append_tool: AppendFileTool, known_file) -> None:
    known_file.write_text("externally modified\n", encoding="utf-8")

    result = asyncio.run(append_tool.run({"path": str(known_file), "content": "more"}))

    assert result.success is False
    assert "Re-read and retry" in result.error


def test_append_file_updates_registry(append_tool: AppendFileTool, registry: FileRegistry, known_file) -> None:
    asyncio.run(append_tool.run({"path": str(known_file), "content": "extra\n"}))

    new_content = known_file.read_text(encoding="utf-8")
    assert registry.verify(str(known_file), new_content) is True


def test_append_file_normalizes_crlf(append_tool: AppendFileTool, known_file) -> None:
    asyncio.run(append_tool.run({"path": str(known_file), "content": "A\r\nB\r\n"}))

    text = known_file.read_text(encoding="utf-8")
    assert "A\nB\n" in text
    assert "\r" not in text


# ---------------------------------------------------------------------------
# Workflow tests
# ---------------------------------------------------------------------------


def test_workflow_create_read_edit_append(
    create_tool: CreateFileTool,
    read_tool: ReadFileTool,
    edit_tool: EditFileTool,
    append_tool: AppendFileTool,
    registry: FileRegistry,
    tmp_path,
) -> None:
    f = tmp_path / "workflow.txt"

    # Step 1: create
    r = asyncio.run(create_tool.run({"path": str(f), "content": "version: 1\n"}))
    assert r.success is True

    # Step 2: read (registers current content)
    r = asyncio.run(read_tool.run({"path": str(f)}))
    assert r.success is True

    # Step 3: edit
    r = asyncio.run(edit_tool.run({"path": str(f), "old_string": "version: 1", "new_string": "version: 2"}))
    assert r.success is True
    assert "version: 2" in f.read_text(encoding="utf-8")

    # Step 4: append
    r = asyncio.run(append_tool.run({"path": str(f), "content": "# updated\n"}))
    assert r.success is True
    assert f.read_text(encoding="utf-8").endswith("# updated\n")

    # Registry must reflect the final state
    assert registry.verify(str(f), f.read_text(encoding="utf-8")) is True


def test_workflow_stale_file_blocks_edit(
    read_tool: ReadFileTool,
    edit_tool: EditFileTool,
    tmp_path,
) -> None:
    f = tmp_path / "shared.txt"
    f.write_text("original content\n", encoding="utf-8")

    asyncio.run(read_tool.run({"path": str(f)}))

    # Simulate an external process modifying the file
    f.write_text("content changed by someone else\n", encoding="utf-8")

    result = asyncio.run(edit_tool.run({"path": str(f), "old_string": "original content", "new_string": "my edit"}))

    assert result.success is False
    assert "Re-read and retry" in result.error


def test_workflow_stale_file_recoverable_after_re_read(
    read_tool: ReadFileTool,
    edit_tool: EditFileTool,
    tmp_path,
) -> None:
    f = tmp_path / "shared.txt"
    f.write_text("original\n", encoding="utf-8")

    asyncio.run(read_tool.run({"path": str(f)}))

    # External change
    f.write_text("updated externally\n", encoding="utf-8")

    # Edit fails
    r = asyncio.run(edit_tool.run({"path": str(f), "old_string": "original", "new_string": "x"}))
    assert r.success is False

    # Re-read to sync the registry
    asyncio.run(read_tool.run({"path": str(f)}))

    # Now edit succeeds against the new content
    r = asyncio.run(edit_tool.run({"path": str(f), "old_string": "updated externally", "new_string": "final"}))
    assert r.success is True
    assert f.read_text(encoding="utf-8") == "final\n"
