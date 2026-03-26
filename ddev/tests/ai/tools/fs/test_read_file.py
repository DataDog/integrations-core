# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import patch

import pytest

from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.fs.read_file import ReadFileTool


def test_tool_name(registry: FileRegistry) -> None:
    assert ReadFileTool(registry).name == "read_file"


async def test_read_file_success(read_tool: ReadFileTool, tmp_path) -> None:
    f = tmp_path / "config.txt"
    f.write_text("hello\nworld\n", encoding="utf-8")

    result = await read_tool.run({"path": str(f)})

    assert result.success is True
    assert result.data == "0: hello\n1: world\n"


async def test_read_registers_unknown_file(read_tool: ReadFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("content", encoding="utf-8")
    await read_tool.run({"path": str(f)})

    assert registry.is_known(str(f)) is True


async def test_read_file_missing_file(read_tool: ReadFileTool, tmp_path) -> None:
    result = await read_tool.run({"path": str(tmp_path / "ghost.txt")})

    assert result.success is False
    assert str(tmp_path / "ghost.txt") in result.error


async def test_read_file_permission_error(read_tool: ReadFileTool, tmp_path) -> None:
    f = tmp_path / "secret.txt"
    f.write_text("secret", encoding="utf-8")

    with patch("pathlib.Path.read_text", side_effect=PermissionError("permission denied")):
        result = await read_tool.run({"path": str(f)})

    assert result.success is False
    assert result.error is not None


async def test_read_file_binary_file(read_tool: ReadFileTool, tmp_path) -> None:
    f = tmp_path / "binary.bin"
    f.write_bytes(b"\xff\xfe\x00binary")

    result = await read_tool.run({"path": str(f)})

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
    ],
)
async def test_read_file_with_offset_and_limit(read_tool: ReadFileTool, tmp_path, offset, limit, expected) -> None:
    f = tmp_path / "file.txt"
    f.write_text("a\nb\nc\n", encoding="utf-8")

    result = await read_tool.run({"path": str(f), "offset": offset, "limit": limit})

    assert result.success is True
    assert result.data == expected


async def test_read_file_truncated(read_tool: ReadFileTool, tmp_path) -> None:
    from ddev.ai.tools.core.truncation import MAX_CHARS

    f = tmp_path / "large.txt"
    f.write_text("x" * (MAX_CHARS + 1000), encoding="utf-8")

    result = await read_tool.run({"path": str(f)})

    assert result.success is True
    assert result.truncated is True
    assert result.total_size is not None
    assert result.hint is not None


async def test_read_file_no_trailing_newline(read_tool: ReadFileTool, tmp_path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("no newline at end", encoding="utf-8")

    result = await read_tool.run({"path": str(f)})

    assert result.success is True
    assert result.data == "0: no newline at end"
