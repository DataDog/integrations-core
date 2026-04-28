# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.tools.fs.append_file import AppendFileTool
from ddev.ai.tools.fs.create_file import CreateFileTool
from ddev.ai.tools.fs.edit_file import EditFileTool
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.fs.mkdir import MkdirTool
from ddev.ai.tools.fs.read_file import ReadFileTool

OWNER_ID = "test-agent"


@pytest.fixture
def owner_id() -> str:
    return OWNER_ID


@pytest.fixture
def permissive_policy() -> FileAccessPolicy:
    return FileAccessPolicy(read_deny_names=(), read_deny_roots=())


@pytest.fixture
def registry(permissive_policy: FileAccessPolicy) -> FileRegistry:
    return FileRegistry(policy=permissive_policy)


@pytest.fixture
def read_tool(registry: FileRegistry, owner_id: str) -> ReadFileTool:
    return ReadFileTool(registry, owner_id)


@pytest.fixture
def create_tool(registry: FileRegistry, owner_id: str) -> CreateFileTool:
    return CreateFileTool(registry, owner_id)


@pytest.fixture
def edit_tool(registry: FileRegistry, owner_id: str) -> EditFileTool:
    return EditFileTool(registry, owner_id)


@pytest.fixture
def append_tool(registry: FileRegistry, owner_id: str) -> AppendFileTool:
    return AppendFileTool(registry, owner_id)


@pytest.fixture
def mkdir_tool(permissive_policy: FileAccessPolicy) -> MkdirTool:
    return MkdirTool(permissive_policy)


@pytest.fixture
async def known_file(tmp_path, create_tool: CreateFileTool):
    """A temp file registered in the registry via create."""
    f = tmp_path / "file.txt"
    await create_tool.run({"path": str(f), "content": "line one\nline two\nline three\n"})
    return f
