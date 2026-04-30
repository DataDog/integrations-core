# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import patch

from ddev.ai.tools.fs.mkdir import MkdirTool


def test_tool_name(mkdir_tool: MkdirTool) -> None:
    assert mkdir_tool.name == "mkdir"


async def test_mkdir_creates_directory(mkdir_tool: MkdirTool, tmp_path) -> None:
    d = tmp_path / "new_dir"

    result = await mkdir_tool.run({"path": str(d)})

    assert result.success is True
    assert d.is_dir()


async def test_mkdir_creates_nested_directories(mkdir_tool: MkdirTool, tmp_path) -> None:
    d = tmp_path / "a" / "b" / "c"

    result = await mkdir_tool.run({"path": str(d)})

    assert result.success is True
    assert d.is_dir()


async def test_mkdir_is_idempotent(mkdir_tool: MkdirTool, tmp_path) -> None:
    d = tmp_path / "existing"
    d.mkdir()

    result = await mkdir_tool.run({"path": str(d)})

    assert result.success is True


async def test_mkdir_oserror_returns_failure(mkdir_tool: MkdirTool, tmp_path) -> None:
    d = tmp_path / "denied"

    with patch("pathlib.Path.mkdir", side_effect=PermissionError("permission denied")):
        result = await mkdir_tool.run({"path": str(d)})

    assert result.success is False
    assert result.error is not None
