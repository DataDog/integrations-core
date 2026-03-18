# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.ai.tools.shell.grep import GrepInput, GrepTool
from ddev.ai.tools.shell.list_files import ListFilesInput, ListFilesTool
from ddev.ai.tools.shell.mkdir import MkdirInput, MkdirTool
from ddev.ai.tools.shell.read_file import ReadFileInput, ReadFileTool

# ---------------------------------------------------------------------------
# GrepTool
# ---------------------------------------------------------------------------


@pytest.fixture
def grep_tool() -> GrepTool:
    return GrepTool()


def test_grep_tool_meta(grep_tool: GrepTool):
    assert grep_tool.name == "grep"
    assert GrepTool.timeout == 30


def test_grep_cmd_recursive(grep_tool: GrepTool):
    # recursive=True (default) includes -r; recursive=False excludes it
    cmd_default = grep_tool.cmd(GrepInput(pattern="foo", path="/tmp"))
    cmd_recursive = grep_tool.cmd(GrepInput(pattern="foo", path="/tmp", recursive=True))
    cmd_non_recursive = grep_tool.cmd(GrepInput(pattern="foo", path="/tmp", recursive=False))

    assert "-r" in cmd_default
    assert "-r" in cmd_recursive
    assert "-r" not in cmd_non_recursive


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


# ---------------------------------------------------------------------------
# ListFilesTool
# ---------------------------------------------------------------------------


@pytest.fixture
def list_files_tool() -> ListFilesTool:
    return ListFilesTool()


def test_list_files_tool_meta(list_files_tool: ListFilesTool):
    assert list_files_tool.name == "list_files"
    assert ListFilesTool.timeout == 30


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


def test_mkdir_tool_meta(mkdir_tool: MkdirTool):
    assert mkdir_tool.name == "mkdir"
    assert MkdirTool.timeout == 5


def test_mkdir_cmd(mkdir_tool: MkdirTool):
    assert mkdir_tool.cmd(MkdirInput(path="/a/b/c")) == ["mkdir", "-p", "/a/b/c"]
    assert mkdir_tool.cmd(MkdirInput(path="/my dir/sub dir")) == ["mkdir", "-p", "/my dir/sub dir"]


# ---------------------------------------------------------------------------
# ReadFileTool
# ---------------------------------------------------------------------------


@pytest.fixture
def read_file_tool() -> ReadFileTool:
    return ReadFileTool()


@pytest.fixture
def path() -> str:
    return "/etc/config.conf"


def test_read_file_tool_meta(read_file_tool: ReadFileTool):
    assert read_file_tool.name == "read_file"
    assert ReadFileTool.timeout == 10


def test_read_file_cmd_cat(read_file_tool: ReadFileTool, path: str):
    # all three forms that should produce cat
    assert read_file_tool.cmd(ReadFileInput(path=path)) == ["cat", path]
    assert read_file_tool.cmd(ReadFileInput(path=path, offset=0, limit=None)) == ["cat", path]
    assert read_file_tool.cmd(ReadFileInput(path=path, offset=None, limit=None)) == ["cat", path]


def test_read_file_cmd_offset_only(read_file_tool: ReadFileTool, path: str):
    # offset is 0-indexed; awk NR is 1-indexed, so offset=5 → NR>=6
    assert read_file_tool.cmd(ReadFileInput(path=path, offset=1)) == ["awk", "NR>=2", path]
    assert read_file_tool.cmd(ReadFileInput(path=path, offset=5)) == ["awk", "NR>=6", path]


def test_read_file_cmd_limit_only(read_file_tool: ReadFileTool, path: str):
    assert read_file_tool.cmd(ReadFileInput(path=path, offset=0, limit=10)) == ["awk", "NR>=1 && NR<=10", path]
    assert read_file_tool.cmd(ReadFileInput(path=path, offset=0, limit=1)) == ["awk", "NR>=1 && NR<=1", path]


@pytest.mark.parametrize(
    "offset,limit,expected_expr",
    [
        (0, 10, "NR>=1 && NR<=10"),
        (1, 10, "NR>=2 && NR<=11"),
        (5, 1, "NR>=6 && NR<=6"),
        (10, 5, "NR>=11 && NR<=15"),
        (3, 5, "NR>=4 && NR<=8"),
    ],
)
def test_read_file_cmd_offset_and_limit(read_file_tool: ReadFileTool, path: str, offset, limit, expected_expr):
    cmd = read_file_tool.cmd(ReadFileInput(path=path, offset=offset, limit=limit))
    assert cmd == ["awk", expected_expr, path]


def test_read_file_cmd_safe_int_coercion(read_file_tool: ReadFileTool, path: str):
    # float offset truncated, None offset treated as 0
    assert read_file_tool.cmd(ReadFileInput(path=path, offset=3.7, limit=None)) == ["awk", "NR>=4", path]  # type: ignore[arg-type]
    assert read_file_tool.cmd(ReadFileInput(path=path, offset=None, limit=5)) == ["awk", "NR>=1 && NR<=5", path]
