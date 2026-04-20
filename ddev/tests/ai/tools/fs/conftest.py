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

AGENT_ID = "test-agent"


@pytest.fixture
def agent_id() -> str:
    return AGENT_ID


@pytest.fixture
def permissive_policy() -> FileAccessPolicy:
    return FileAccessPolicy(read_deny_names=(), read_deny_roots=())


@pytest.fixture
def registry(permissive_policy: FileAccessPolicy) -> FileRegistry:
    return FileRegistry(policy=permissive_policy)


@pytest.fixture
def read_tool(registry: FileRegistry, agent_id: str) -> ReadFileTool:
    return ReadFileTool(registry, agent_id)


@pytest.fixture
def create_tool(registry: FileRegistry, agent_id: str) -> CreateFileTool:
    return CreateFileTool(registry, agent_id)


@pytest.fixture
def edit_tool(registry: FileRegistry, agent_id: str) -> EditFileTool:
    return EditFileTool(registry, agent_id)


@pytest.fixture
def append_tool(registry: FileRegistry, agent_id: str) -> AppendFileTool:
    return AppendFileTool(registry, agent_id)


@pytest.fixture
def mkdir_tool(registry: FileRegistry, agent_id: str) -> MkdirTool:
    return MkdirTool(registry, agent_id)


@pytest.fixture
async def known_file(tmp_path, create_tool: CreateFileTool):
    """A temp file registered in the registry via create."""
    f = tmp_path / "file.txt"
    await create_tool.run({"path": str(f), "content": "line one\nline two\nline three\n"})
    return f
