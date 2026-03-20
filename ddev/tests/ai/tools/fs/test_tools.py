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


@pytest.mark.parametrize(
    "tool_cls,expected_name",
    [
        (ReadFileTool, "read_file"),
        (CreateFileTool, "create_file"),
        (EditFileTool, "edit_file"),
        (AppendFileTool, "append_file"),
    ],
)
def test_tool_meta(tool_cls, expected_name) -> None:
    assert tool_cls(FileRegistry()).name == expected_name


# ---------------------------------------------------------------------------
# ReadFileTool
# ---------------------------------------------------------------------------


def test_read_file_success(read_tool: ReadFileTool, tmp_path) -> None:
    f = tmp_path / "config.txt"
    f.write_text("hello\nworld\n", encoding="utf-8")

    result = asyncio.run(read_tool.run({"path": str(f)}))

    assert result.success is True
    assert result.data == "0: hello\n1: world\n"


@pytest.mark.parametrize(
    "tool_fixture,content",
    [
        ("read_tool", "content"),
        ("create_tool", "hi"),
    ],
)
def test_tool_registers_in_registry(request, registry: FileRegistry, tmp_path, tool_fixture, content) -> None:
    tool = request.getfixturevalue(tool_fixture)
    f = tmp_path / "file.txt"
    if isinstance(tool, ReadFileTool):
        f.write_text(content, encoding="utf-8")
        asyncio.run(tool.run({"path": str(f)}))
    else:
        asyncio.run(tool.run({"path": str(f), "content": content}))

    assert registry.is_known(str(f)) is True
    assert registry.verify(str(f), content) is True


def test_read_file_missing_file(read_tool: ReadFileTool, tmp_path) -> None:
    result = asyncio.run(read_tool.run({"path": str(tmp_path / "ghost.txt")}))

    assert result.success is False
    assert result.error is not None


@pytest.mark.parametrize(
    "offset, limit, expected",
    [
        (1, None, "1: b\n2: c\n"),
        (0, 2, "0: a\n1: b\n"),
        (1, 2, "1: b\n2: c\n"),
        (1, 1, "1: b\n"),
        (2, 10, "2: c\n"),  # limit exceeds remaining lines
        (100, None, ""),  # offset beyond EOF
        (1.0, 1, "1: b\n"),
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
    assert result.data == "0: no newline at end"


# ---------------------------------------------------------------------------
# CreateFileTool
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# EditFileTool
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "old_string,new_string,expected_in,expected_out",
    [
        ("line two", "line TWO", "line TWO", "line two"),
        ("line two\n", "", None, "line two"),
    ],
)
def test_edit_file_success(
    edit_tool: EditFileTool, known_file, old_string, new_string, expected_in, expected_out
) -> None:
    result = asyncio.run(edit_tool.run({"path": str(known_file), "old_string": old_string, "new_string": new_string}))

    assert result.success is True
    content = known_file.read_text(encoding="utf-8")
    if expected_in is not None:
        assert expected_in in content
    assert expected_out not in content


def test_edit_file_requires_prior_read(edit_tool: EditFileTool, tmp_path) -> None:
    f = tmp_path / "unread.txt"
    f.write_text("content", encoding="utf-8")

    result = asyncio.run(edit_tool.run({"path": str(f), "old_string": "content", "new_string": "new"}))

    assert result.success is False
    assert "read the file first" in result.error


@pytest.mark.parametrize("old_string", ["does not exist", ""])
def test_edit_file_fails_if_old_string_not_found_or_empty(edit_tool: EditFileTool, known_file, old_string) -> None:
    result = asyncio.run(edit_tool.run({"path": str(known_file), "old_string": old_string, "new_string": "x"}))

    assert result.success is False
    assert "not found" in result.error


def test_edit_file_fails_if_old_string_ambiguous(edit_tool: EditFileTool, read_tool: ReadFileTool, tmp_path) -> None:
    f = tmp_path / "dup.txt"
    f.write_text("foo\nfoo\nfoo\n", encoding="utf-8")
    asyncio.run(read_tool.run({"path": str(f)}))

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


@pytest.mark.parametrize(
    "file_content,old_string,new_string,expected",
    [
        ("line one\nline two\n", "line one\r\nline two", "replaced", "replaced\n"),  # CRLF in old_string
        ("line one\n", "line one", "A\r\nB", "A\nB\n"),  # CRLF in new_string
    ],
)
def test_edit_file_normalizes_crlf(
    edit_tool: EditFileTool, read_tool: ReadFileTool, tmp_path, file_content, old_string, new_string, expected
) -> None:
    f = tmp_path / "file.txt"
    f.write_text(file_content, encoding="utf-8")
    asyncio.run(read_tool.run({"path": str(f)}))

    result = asyncio.run(edit_tool.run({"path": str(f), "old_string": old_string, "new_string": new_string}))

    assert result.success is True
    assert f.read_text(encoding="utf-8") == expected


# ---------------------------------------------------------------------------
# AppendFileTool
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content,expected_in,expected_not_in",
    [
        ("line four\n", "line four\n", None),
        ("appended", "three\nappended", None),
        ("A\r\nB\r\n", "A\nB\n", "\r"),
    ],
)
def test_append_file_success(append_tool: AppendFileTool, known_file, content, expected_in, expected_not_in) -> None:
    result = asyncio.run(append_tool.run({"path": str(known_file), "content": content}))

    assert result.success is True
    text = known_file.read_text(encoding="utf-8")
    assert expected_in in text
    if expected_not_in is not None:
        assert expected_not_in not in text


def test_append_file_requires_prior_read(append_tool: AppendFileTool, tmp_path) -> None:
    f = tmp_path / "unread.txt"
    f.write_text("content", encoding="utf-8")

    result = asyncio.run(append_tool.run({"path": str(f), "content": "more"}))

    assert result.success is False
    assert "read the file first" in result.error


@pytest.mark.parametrize(
    "initial,appended,expected",
    [
        ("no newline", "appended", "no newline\nappended"),
        ("", "first line", "first line"),
    ],
)
def test_append_file_separator(
    append_tool: AppendFileTool, read_tool: ReadFileTool, tmp_path, initial, appended, expected
) -> None:
    f = tmp_path / "file.txt"
    f.write_text(initial, encoding="utf-8")
    asyncio.run(read_tool.run({"path": str(f)}))

    result = asyncio.run(append_tool.run({"path": str(f), "content": appended}))

    assert result.success is True
    assert f.read_text(encoding="utf-8") == expected


def test_append_file_fails_if_file_changed_externally(append_tool: AppendFileTool, known_file) -> None:
    known_file.write_text("externally modified\n", encoding="utf-8")

    result = asyncio.run(append_tool.run({"path": str(known_file), "content": "more"}))

    assert result.success is False
    assert "Re-read and retry" in result.error


def test_append_file_updates_registry(append_tool: AppendFileTool, registry: FileRegistry, known_file) -> None:
    asyncio.run(append_tool.run({"path": str(known_file), "content": "extra\n"}))

    new_content = known_file.read_text(encoding="utf-8")
    assert registry.verify(str(known_file), new_content) is True


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


def test_workflow_stale_file(
    read_tool: ReadFileTool,
    edit_tool: EditFileTool,
    tmp_path,
) -> None:
    f = tmp_path / "shared.txt"
    f.write_text("original\n", encoding="utf-8")

    asyncio.run(read_tool.run({"path": str(f)}))
    f.write_text("updated externally\n", encoding="utf-8")

    result = asyncio.run(edit_tool.run({"path": str(f), "old_string": "original", "new_string": "my edit"}))
    assert result.success is False
    assert "Re-read and retry" in result.error

    asyncio.run(read_tool.run({"path": str(f)}))

    result = asyncio.run(edit_tool.run({"path": str(f), "old_string": "updated externally", "new_string": "final"}))
    assert result.success is True
    assert f.read_text(encoding="utf-8") == "final\n"
