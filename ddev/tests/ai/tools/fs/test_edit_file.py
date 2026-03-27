# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import patch

import pytest

from ddev.ai.tools.fs.create_file import CreateFileTool
from ddev.ai.tools.fs.edit_file import EditFileTool
from ddev.ai.tools.fs.file_registry import FileRegistry


def test_tool_name(registry: FileRegistry) -> None:
    assert EditFileTool(registry).name == "edit_file"


async def test_edit_file_replaces_string(edit_tool: EditFileTool, known_file) -> None:
    result = await edit_tool.run({"path": str(known_file), "old_string": "line two", "new_string": "line TWO"})

    assert result.success is True
    content = known_file.read_text(encoding="utf-8")
    assert "line TWO" in content
    assert "line two" not in content


async def test_edit_file_deletes_line(edit_tool: EditFileTool, known_file) -> None:
    result = await edit_tool.run({"path": str(known_file), "old_string": "line two\n", "new_string": ""})

    assert result.success is True
    assert "line two" not in known_file.read_text(encoding="utf-8")


async def test_edit_file_fails_for_unregistered_file(edit_tool: EditFileTool, tmp_path) -> None:
    f = tmp_path / "unread.txt"
    f.write_text("content", encoding="utf-8")

    result = await edit_tool.run({"path": str(f), "old_string": "content", "new_string": "new"})

    assert result.success is False
    assert "Not authorized" in result.error


@pytest.mark.parametrize("old_string", ["does not exist", ""])
async def test_edit_file_fails_if_old_string_not_found_or_empty(
    edit_tool: EditFileTool, known_file, old_string
) -> None:
    result = await edit_tool.run({"path": str(known_file), "old_string": old_string, "new_string": "x"})

    assert result.success is False


async def test_edit_file_fails_if_old_string_ambiguous(
    edit_tool: EditFileTool, create_tool: CreateFileTool, tmp_path
) -> None:
    f = tmp_path / "dup.txt"
    await create_tool.run({"path": str(f), "content": "foo\nfoo\nfoo\n"})

    result = await edit_tool.run({"path": str(f), "old_string": "foo", "new_string": "bar"})

    assert result.success is False
    assert "3" in result.error
    assert result.hint is not None


async def test_edit_file_fails_if_file_changed_externally(edit_tool: EditFileTool, known_file) -> None:
    known_file.write_text("externally modified\n", encoding="utf-8")

    result = await edit_tool.run({"path": str(known_file), "old_string": "line one", "new_string": "x"})

    assert result.success is False
    assert "Re-read and retry" in result.error


async def test_edit_file_updates_registry(edit_tool: EditFileTool, registry: FileRegistry, known_file) -> None:
    await edit_tool.run({"path": str(known_file), "old_string": "line one", "new_string": "LINE ONE"})

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
async def test_edit_file_normalizes_crlf(
    edit_tool: EditFileTool, create_tool: CreateFileTool, tmp_path, file_content, old_string, new_string, expected
) -> None:
    f = tmp_path / "file.txt"
    await create_tool.run({"path": str(f), "content": file_content})

    result = await edit_tool.run({"path": str(f), "old_string": old_string, "new_string": new_string})

    assert result.success is True
    assert f.read_text(encoding="utf-8") == expected


async def test_edit_file_oserror_on_write(edit_tool: EditFileTool, registry: FileRegistry, known_file) -> None:
    original_content = known_file.read_text(encoding="utf-8")

    with patch("pathlib.Path.write_text", side_effect=PermissionError("permission denied")):
        result = await edit_tool.run({"path": str(known_file), "old_string": "line one", "new_string": "x"})

    assert result.success is False
    assert result.error is not None
    # File must be untouched and registry must still reflect the original content
    assert known_file.read_text(encoding="utf-8") == original_content
    assert registry.verify(str(known_file), original_content) is True
