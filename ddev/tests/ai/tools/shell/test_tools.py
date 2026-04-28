# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import AsyncMock, patch

import pytest

from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.shell.grep import GrepInput, GrepTool
from ddev.ai.tools.shell.list_files import ListFilesInput, ListFilesTool

# ---------------------------------------------------------------------------
# Tool metadata
# ---------------------------------------------------------------------------


def test_grep_tool_meta() -> None:
    tool = GrepTool(FileAccessPolicy())
    assert tool.name == "grep"
    assert GrepTool.timeout == 30


def test_list_files_tool_meta() -> None:
    tool = ListFilesTool()
    assert tool.name == "list_files"
    assert ListFilesTool.timeout == 30


# ---------------------------------------------------------------------------
# GrepTool
# ---------------------------------------------------------------------------


@pytest.fixture
def grep_tool() -> GrepTool:
    return GrepTool(FileAccessPolicy(read_deny_names=(), read_deny_roots=()))


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


def test_grep_cmd_recursive_adds_exclude_flags(tmp_path) -> None:
    policy = FileAccessPolicy(
        read_deny_names=(".env", "*.pem"),
        read_deny_roots=(str(tmp_path / "secrets"),),
    )
    tool = GrepTool(policy)
    cmd = tool.cmd(GrepInput(pattern="SECRET", path="/project", recursive=True))
    sep = cmd.index("--")
    flags_before_sep = cmd[:sep]
    assert "--exclude=.env" in flags_before_sep
    assert "--exclude=*.pem" in flags_before_sep
    assert "--exclude-dir=secrets" in flags_before_sep
    assert cmd[-2] == "SECRET"
    assert cmd[-1] == "/project"


def test_grep_cmd_non_recursive_no_exclude_flags(tmp_path) -> None:
    policy = FileAccessPolicy(
        read_deny_names=(".env", "*.pem"),
        read_deny_roots=(str(tmp_path / "secrets"),),
    )
    tool = GrepTool(policy)
    cmd = tool.cmd(GrepInput(pattern="SECRET", path="/project/file.txt", recursive=False))
    assert not any(arg.startswith("--exclude") for arg in cmd)


async def test_grep_no_matches_returns_success(grep_tool: GrepTool):
    from ddev.ai.tools.core.types import ToolResult

    no_match_result = ToolResult(success=False, data="(no output)", error=None)
    with patch("ddev.ai.tools.shell.grep.run_command", new=AsyncMock(return_value=no_match_result)):
        result = await grep_tool(GrepInput(pattern="nomatch", path="/tmp"))
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
