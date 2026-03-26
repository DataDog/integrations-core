# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import patch

from ddev.ai.tools.fs.create_file import CreateFileTool
from ddev.ai.tools.fs.file_registry import FileRegistry


def test_tool_name(registry: FileRegistry) -> None:
    assert CreateFileTool(registry).name == "create_file"


async def test_create_file_success(create_tool: CreateFileTool, tmp_path) -> None:
    f = tmp_path / "new.txt"

    result = await create_tool.run({"path": str(f), "content": "hello"})

    assert result.success is True
    assert f.read_text(encoding="utf-8") == "hello"


async def test_create_file_default_empty_content(create_tool: CreateFileTool, tmp_path) -> None:
    f = tmp_path / "empty.txt"

    result = await create_tool.run({"path": str(f)})

    assert result.success is True
    assert f.read_text(encoding="utf-8") == ""


async def test_create_file_creates_missing_parent_dirs(create_tool: CreateFileTool, tmp_path) -> None:
    f = tmp_path / "a" / "b" / "c" / "file.txt"

    result = await create_tool.run({"path": str(f), "content": "nested"})

    assert result.success is True
    assert f.exists()
    assert f.read_text(encoding="utf-8") == "nested"


async def test_create_file_fails_if_file_already_exists(
    create_tool: CreateFileTool, registry: FileRegistry, tmp_path
) -> None:
    f = tmp_path / "existing.txt"
    f.write_text("original", encoding="utf-8")

    result = await create_tool.run({"path": str(f), "content": "new"})

    assert result.success is False
    assert result.error is not None
    assert f.read_text(encoding="utf-8") == "original"
    assert not registry.is_known(str(f))


async def test_create_tool_registers_in_registry(create_tool: CreateFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "file.txt"
    await create_tool.run({"path": str(f), "content": "hi"})

    assert registry.is_known(str(f)) is True
    assert registry.verify(str(f), "hi") is True


async def test_create_file_oserror_on_mkdir(create_tool: CreateFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "a" / "b" / "new.txt"

    with patch("pathlib.Path.mkdir", side_effect=PermissionError("permission denied")):
        result = await create_tool.run({"path": str(f), "content": "hi"})

    assert result.success is False
    assert result.error is not None
    assert not f.exists()
    assert not registry.is_known(str(f))


async def test_create_file_oserror_on_write(create_tool: CreateFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "new.txt"

    with patch("pathlib.Path.write_text", side_effect=PermissionError("permission denied")):
        result = await create_tool.run({"path": str(f), "content": "hi"})

    assert result.success is False
    assert result.error is not None
    assert not registry.is_known(str(f))
