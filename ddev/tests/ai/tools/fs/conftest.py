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
def known_file(tmp_path, create_tool: CreateFileTool):
    """A temp file registered in the registry via create."""
    f = tmp_path / "file.txt"
    asyncio.run(create_tool.run({"path": str(f), "content": "line one\nline two\nline three\n"}))
    return f
