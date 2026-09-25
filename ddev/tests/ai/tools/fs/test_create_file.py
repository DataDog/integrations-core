# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import patch

from ddev.ai.tools.fs.create_file import CreateFileTool
from ddev.ai.tools.fs.file_registry import FileRegistry

from .conftest import OWNER_ID


def test_tool_name(registry: FileRegistry) -> None:
    assert CreateFileTool(registry, OWNER_ID).name == "create_file"


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
    assert "File already exists" in result.error
    assert f.read_text(encoding="utf-8") == "original"
    assert not registry.is_known(OWNER_ID, str(f))


async def test_create_file_replace_if_existing_overwrites_known_file(
    create_tool: CreateFileTool, registry: FileRegistry, known_file
) -> None:
    result = await create_tool.run({"path": str(known_file), "content": "new", "replace_if_existing": True})

    assert result.success is True
    assert "replaced" in result.data.lower()
    assert known_file.read_text(encoding="utf-8") == "new"
    assert registry.verify(OWNER_ID, str(known_file), "new") is True


async def test_create_file_replace_if_existing_fails_if_file_not_previously_read(
    create_tool: CreateFileTool, registry: FileRegistry, tmp_path
) -> None:
    f = tmp_path / "existing.txt"
    f.write_text("original", encoding="utf-8")

    result = await create_tool.run({"path": str(f), "content": "new", "replace_if_existing": True})

    assert result.success is False
    assert "Not authorized" in result.error
    assert f.read_text(encoding="utf-8") == "original"


async def test_create_file_replace_if_existing_fails_if_file_changed_since_last_read(
    create_tool: CreateFileTool, known_file
) -> None:
    known_file.write_text("modified externally", encoding="utf-8")

    result = await create_tool.run({"path": str(known_file), "content": "new", "replace_if_existing": True})

    assert result.success is False
    assert "changed since last read" in result.error
    assert known_file.read_text(encoding="utf-8") == "modified externally"


async def test_create_file_replace_if_existing_creates_new_file(create_tool: CreateFileTool, tmp_path) -> None:
    f = tmp_path / "new.txt"

    result = await create_tool.run({"path": str(f), "content": "hello", "replace_if_existing": True})

    assert result.success is True
    assert "created" in result.data.lower()
    assert "replaced" not in result.data.lower()
    assert f.read_text(encoding="utf-8") == "hello"


async def test_create_tool_registers_in_registry(create_tool: CreateFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "file.txt"
    await create_tool.run({"path": str(f), "content": "hi"})

    assert registry.is_known(OWNER_ID, str(f)) is True
    assert registry.verify(OWNER_ID, str(f), "hi") is True


async def test_create_file_oserror_on_mkdir(create_tool: CreateFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "a" / "b" / "new.txt"

    with patch("pathlib.Path.mkdir", side_effect=PermissionError("permission denied")):
        result = await create_tool.run({"path": str(f), "content": "hi"})

    assert result.success is False
    assert result.error is not None
    assert not f.exists()
    assert not registry.is_known(OWNER_ID, str(f))


async def test_create_file_oserror_on_write(create_tool: CreateFileTool, registry: FileRegistry, tmp_path) -> None:
    f = tmp_path / "new.txt"

    with patch("builtins.open", side_effect=PermissionError("permission denied")):
        result = await create_tool.run({"path": str(f), "content": "hi"})

    assert result.success is False
    assert result.error is not None
    assert not registry.is_known(OWNER_ID, str(f))
