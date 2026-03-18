# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from ddev.ai.tools.shell.grep import GrepInput, GrepTool
from ddev.ai.tools.shell.list_files import ListFilesInput, ListFilesTool
from ddev.ai.tools.shell.mkdir import MkdirInput, MkdirTool

# ---------------------------------------------------------------------------
# Tool metadata
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool_cls,expected_name,expected_timeout",
    [
        (GrepTool, "grep", 30),
        (ListFilesTool, "list_files", 30),
        (MkdirTool, "mkdir", 5),
        (ReadFileTool, "read_file", 10),
    ],
)
def test_tool_meta(tool_cls, expected_name, expected_timeout):
    assert tool_cls().name == expected_name
    assert tool_cls.timeout == expected_timeout


# ---------------------------------------------------------------------------
# GrepTool
# ---------------------------------------------------------------------------


@pytest.fixture
def grep_tool() -> GrepTool:
    return GrepTool()


def test_grep_cmd_full_command(grep_tool: GrepTool):
    assert grep_tool.cmd(GrepInput(pattern="ERROR", path="/var/log", recursive=True)) == [
        "grep",
        "-n",
        "-E",
        "-r",
        "--",
        "ERROR",
        "/var/log",
    ]
    assert grep_tool.cmd(GrepInput(pattern="ERROR", path="/var/log", recursive=False)) == [
        "grep",
        "-n",
        "-E",
        "--",
        "ERROR",
        "/var/log",
    ]


def test_grep_cmd_pattern_and_path_placement(grep_tool: GrepTool):
    # pattern is always second-to-last, path is always last
    pattern = r"^\d+\.\d+\.\d+"
    cmd = grep_tool.cmd(GrepInput(pattern=pattern, path="/my dir/sub dir"))
    assert cmd[-2] == pattern
    assert cmd[-1] == "/my dir/sub dir"


def test_grep_no_matches_returns_success(grep_tool: GrepTool):
    from ddev.ai.tools.core.types import ToolResult

    no_match_result = ToolResult(success=False, data="(no output)", error=None)
    with patch("ddev.ai.tools.shell.grep.run_command", new=AsyncMock(return_value=no_match_result)):
        result = asyncio.run(grep_tool(GrepInput(pattern="nomatch", path="/tmp")))
    assert result.success is True
    assert result.data == "(no output)"


# ---------------------------------------------------------------------------
# ListFilesTool
# ---------------------------------------------------------------------------


@pytest.fixture
def list_files_tool() -> ListFilesTool:
    return ListFilesTool()


def test_list_files_cmd_non_recursive(list_files_tool: ListFilesTool):
    # non-recursive by default — maxdepth 1 present, mindepth before maxdepth
    cmd_default = list_files_tool.cmd(ListFilesInput(path="/tmp"))
    cmd_explicit = list_files_tool.cmd(ListFilesInput(path="/var", recursive=False))

    assert cmd_default == ["find", "/tmp", "-mindepth", "1", "-maxdepth", "1"]
    assert cmd_explicit == ["find", "/var", "-mindepth", "1", "-maxdepth", "1"]


def test_list_files_cmd_recursive(list_files_tool: ListFilesTool):
    cmd = list_files_tool.cmd(ListFilesInput(path="/var", recursive=True))
    assert cmd == ["find", "/var", "-mindepth", "1"]


# ---------------------------------------------------------------------------
# MkdirTool
# ---------------------------------------------------------------------------


@pytest.fixture
def mkdir_tool() -> MkdirTool:
    return MkdirTool()


def test_mkdir_cmd(mkdir_tool: MkdirTool):
    assert mkdir_tool.cmd(MkdirInput(path="/a/b/c")) == ["mkdir", "-p", "/a/b/c"]
    assert mkdir_tool.cmd(MkdirInput(path="/my dir/sub dir")) == ["mkdir", "-p", "/my dir/sub dir"]
