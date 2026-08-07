# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio

import pytest

from ddev.ai.phases.base import FlowContext
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy


@pytest.fixture
def flow_dir(tmp_path):
    """Create a minimal flow directory with an agent definition."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "writer.md").write_text("---\ntype: agent\nmodel: sonnet\n---\n\nYou are a writer for ${phase_name}.")
    return tmp_path


@pytest.fixture
def flow_context(flow_dir):
    return FlowContext(
        runtime_variables={},
        flow_variables={},
    )


@pytest.fixture
def message_queue():
    """An asyncio.Queue that can be attached to a Phase for submit_message."""
    return asyncio.Queue()


@pytest.fixture
def file_access_policy(tmp_path) -> FileAccessPolicy:
    return FileAccessPolicy(write_root=tmp_path)
