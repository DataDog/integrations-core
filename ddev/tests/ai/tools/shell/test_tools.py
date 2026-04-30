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


def test_grep_tool_meta(tmp_path) -> None:
    tool = GrepTool(FileAccessPolicy(write_root=tmp_path))
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
def grep_tool(tmp_path) -> GrepTool:
    return GrepTool(FileAccessPolicy(write_root=tmp_path, deny_patterns=()))


def test_grep_cmd_full_command(grep_tool: GrepTool):
    # deny_patterns=() so no --exclude= flags; paths outside write_root still produce no flags.
    assert grep_tool.cmd(GrepInput(pattern="ERROR", path="/var/log", recursive=True)) == [
        "grep",
        "-n",
        "-E",
        "--null",
        "-I",
        "--no-messages",
        "-r",
        "--",
        "ERROR",
        "/var/log",
    ]
    assert grep_tool.cmd(GrepInput(pattern="ERROR", path="/var/log", recursive=False)) == [
        "grep",
        "-n",
        "-E",
        "--null",
        "-I",
        "--no-messages",
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


def test_grep_cmd_recursive_outside_write_root_adds_basename_excludes(tmp_path) -> None:
    """--exclude= flags are added only for basename patterns when search is outside write_root."""
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=(".env", "*.pem", f"{tmp_path}/secrets/*"))
    tool = GrepTool(policy)
    # /project is outside tmp_path (write_root)
    cmd = tool.cmd(GrepInput(pattern="SECRET", path="/project", recursive=True))
    flags_before_sep = cmd[: cmd.index("--")]
    assert "--exclude=.env" in flags_before_sep
    assert "--exclude=*.pem" in flags_before_sep
    # Path patterns must NOT become flags — they ride on the post-filter.
    assert not any(f.startswith("--exclude-dir") for f in flags_before_sep)
    assert not any("secrets" in f for f in flags_before_sep)
    assert cmd[-2] == "SECRET"
    assert cmd[-1] == "/project"


def test_grep_cmd_recursive_inside_write_root_no_excludes(tmp_path) -> None:
    """No --exclude= flags when search path is inside write_root."""
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=(".env", "*.pem"))
    tool = GrepTool(policy)
    # Search inside write_root — deny patterns are bypassed, so no excludes.
    cmd = tool.cmd(GrepInput(pattern="SECRET", path=str(tmp_path / "project"), recursive=True))
    assert not any(arg.startswith("--exclude") for arg in cmd)


def test_grep_cmd_recursive_spanning_write_root_no_excludes(tmp_path) -> None:
    """No --exclude= flags when write_root is inside the search path (mixed zone)."""
    write_root = tmp_path / "sandbox"
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(".env", "*.pem"))
    tool = GrepTool(policy)
    # Search starts at tmp_path which is a parent of write_root — spanning case.
    cmd = tool.cmd(GrepInput(pattern="SECRET", path=str(tmp_path), recursive=True))
    assert not any(arg.startswith("--exclude") for arg in cmd)


def test_grep_cmd_non_recursive_no_exclude_flags(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=(".env", "*.pem", f"{tmp_path}/secrets/*"))
    tool = GrepTool(policy)
    cmd = tool.cmd(GrepInput(pattern="SECRET", path="/project/file.txt", recursive=False))
    assert not any(arg.startswith("--exclude") for arg in cmd)


# ---------------------------------------------------------------------------
# GrepTool post-filter — unit tests on the parsing/decision logic
# ---------------------------------------------------------------------------


def test_filter_stdout_keeps_allowed_lines(tmp_path) -> None:
    f = tmp_path / "ok.txt"
    f.write_text("x")
    tool = GrepTool(FileAccessPolicy(write_root=tmp_path, deny_patterns=()))
    raw = f"{f}\x0042:hello\n{f}\x0043:world\n"
    out = tool._filter_stdout(raw)
    assert out == f"{f}:42:hello\n{f}:43:world"


def test_filter_stdout_filters_denied_path_lines(tmp_path) -> None:
    write_root = tmp_path / "sandbox"
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    leak = secrets / "leak.txt"
    leak.write_text("x")
    public = tmp_path / "ok.txt"
    public.write_text("x")

    # write_root is a subdirectory; secrets/ and ok.txt are outside it, so deny patterns apply.
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{secrets}/*",))
    tool = GrepTool(policy)
    raw = f"{leak}\x001:hit\n{public}\x002:hit\n"
    out = tool._filter_stdout(raw)
    assert f"{leak}: Read denied by policy" in out
    assert f"{public}:2:hit" in out


def test_filter_stdout_drops_lines_without_nul(tmp_path) -> None:
    """Defensive: stderr noise / malformed output is dropped, not passed through."""
    tool = GrepTool(FileAccessPolicy(write_root=tmp_path, deny_patterns=()))
    assert tool._filter_stdout("grep: something: Permission denied\n") == ""


def test_filter_stdout_caches_per_filename(tmp_path, monkeypatch) -> None:
    f = tmp_path / "ok.txt"
    f.write_text("x")
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    calls = {"n": 0}
    real = policy.assert_readable

    def counting(p):
        calls["n"] += 1
        return real(p)

    monkeypatch.setattr(policy, "assert_readable", counting)
    tool = GrepTool(policy)
    raw = "".join(f"{f}\x00{i}:line\n" for i in range(10))
    tool._filter_stdout(raw)
    assert calls["n"] == 1


def test_filter_stdout_resolves_symlink_to_denied(tmp_path) -> None:
    write_root = tmp_path / "sandbox"
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    target = secrets / "real.txt"
    target.write_text("x")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    # secrets/ is outside write_root, so its deny pattern applies.
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{secrets}/*",))
    tool = GrepTool(policy)
    raw = f"{link}\x001:hit\n"
    out = tool._filter_stdout(raw)
    assert out == f"{link}: Read denied by policy"


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
