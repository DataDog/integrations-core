# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import patch

import pytest

from ddev.ai.tools.fs.append_file import AppendFileTool
from ddev.ai.tools.fs.create_file import CreateFileTool
from ddev.ai.tools.fs.file_registry import FileRegistry


def test_tool_name(registry: FileRegistry) -> None:
    assert AppendFileTool(registry).name == "append_file"


@pytest.mark.parametrize(
    "content,expected_in,expected_not_in",
    [
        ("line four\n", "line four\n", None),
        ("appended", "three\nappended", None),
        ("A\r\nB\r\n", "A\nB\n", "\r"),
    ],
)
async def test_append_file_success(
    append_tool: AppendFileTool, known_file, content, expected_in, expected_not_in
) -> None:
    result = await append_tool.run({"path": str(known_file), "content": content})

    assert result.success is True
    text = known_file.read_text(encoding="utf-8")
    assert expected_in in text
    if expected_not_in is not None:
        assert expected_not_in not in text


async def test_append_file_fails_for_unregistered_file(append_tool: AppendFileTool, tmp_path) -> None:
    f = tmp_path / "unread.txt"
    f.write_text("content", encoding="utf-8")

    result = await append_tool.run({"path": str(f), "content": "more"})

    assert result.success is False
    assert "Not authorized" in result.error


@pytest.mark.parametrize(
    "initial,appended,expected",
    [
        ("no newline", "appended", "no newline\nappended"),
        ("", "first line", "first line"),
    ],
)
async def test_append_file_separator(
    append_tool: AppendFileTool, create_tool: CreateFileTool, tmp_path, initial, appended, expected
) -> None:
    f = tmp_path / "file.txt"
    await create_tool.run({"path": str(f), "content": initial})

    result = await append_tool.run({"path": str(f), "content": appended})

    assert result.success is True
    assert f.read_text(encoding="utf-8") == expected


async def test_append_file_fails_if_file_changed_externally(append_tool: AppendFileTool, known_file) -> None:
    known_file.write_text("externally modified\n", encoding="utf-8")

    result = await append_tool.run({"path": str(known_file), "content": "more"})

    assert result.success is False
    assert "Re-read and retry" in result.error


async def test_append_file_updates_registry(append_tool: AppendFileTool, registry: FileRegistry, known_file) -> None:
    await append_tool.run({"path": str(known_file), "content": "extra\n"})

    new_content = known_file.read_text(encoding="utf-8")
    assert registry.verify(str(known_file), new_content) is True


async def test_append_file_oserror_on_write(append_tool: AppendFileTool, registry: FileRegistry, known_file) -> None:
    original_content = known_file.read_text(encoding="utf-8")

    with patch("pathlib.Path.write_text", side_effect=PermissionError("permission denied")):
        result = await append_tool.run({"path": str(known_file), "content": "new line"})

    assert result.success is False
    assert result.error is not None
    # File must be untouched and registry must still reflect the original content
    assert known_file.read_text(encoding="utf-8") == original_content
    assert registry.verify(str(known_file), original_content) is True
