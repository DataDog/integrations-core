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


class TestGrepTool:
    def setup_method(self):
        self.tool = GrepTool()

    def test_name(self):
        assert self.tool.name == "grep"

    def test_timeout(self):
        assert GrepTool.timeout == 30

    def test_cmd_starts_with_grep_flags(self):
        cmd = self.tool.cmd(GrepInput(pattern="foo", path="/tmp"))
        assert cmd[:3] == ["grep", "-n", "-E"]

    def test_cmd_recursive_by_default(self):
        cmd = self.tool.cmd(GrepInput(pattern="foo", path="/tmp"))
        assert "-r" in cmd

    def test_cmd_recursive_true_includes_r_flag(self):
        cmd = self.tool.cmd(GrepInput(pattern="foo", path="/tmp", recursive=True))
        assert "-r" in cmd

    def test_cmd_recursive_false_excludes_r_flag(self):
        cmd = self.tool.cmd(GrepInput(pattern="foo", path="/tmp", recursive=False))
        assert "-r" not in cmd

    def test_cmd_pattern_is_second_to_last(self):
        cmd = self.tool.cmd(GrepInput(pattern="my_pattern", path="/some/path"))
        assert cmd[-2] == "my_pattern"

    def test_cmd_path_is_last(self):
        cmd = self.tool.cmd(GrepInput(pattern="foo", path="/some/path"))
        assert cmd[-1] == "/some/path"

    def test_cmd_full_recursive(self):
        cmd = self.tool.cmd(GrepInput(pattern="ERROR", path="/var/log", recursive=True))
        assert cmd == ["grep", "-n", "-E", "-r", "ERROR", "/var/log"]

    def test_cmd_full_non_recursive(self):
        cmd = self.tool.cmd(GrepInput(pattern="ERROR", path="/var/log", recursive=False))
        assert cmd == ["grep", "-n", "-E", "ERROR", "/var/log"]

    def test_cmd_special_regex_characters_passed_as_is(self):
        pattern = r"^\d+\.\d+\.\d+"
        cmd = self.tool.cmd(GrepInput(pattern=pattern, path="/tmp"))
        assert pattern in cmd

    def test_cmd_path_with_spaces(self):
        cmd = self.tool.cmd(GrepInput(pattern="foo", path="/my dir/sub dir"))
        assert cmd[-1] == "/my dir/sub dir"


# ---------------------------------------------------------------------------
# ListFilesTool
# ---------------------------------------------------------------------------


class TestListFilesTool:
    def setup_method(self):
        self.tool = ListFilesTool()

    def test_name(self):
        assert self.tool.name == "list_files"

    def test_timeout(self):
        assert ListFilesTool.timeout == 30

    def test_cmd_starts_with_find(self):
        cmd = self.tool.cmd(ListFilesInput(path="/tmp"))
        assert cmd[0] == "find"

    def test_cmd_path_is_second_element(self):
        cmd = self.tool.cmd(ListFilesInput(path="/some/path"))
        assert cmd[1] == "/some/path"

    def test_cmd_always_has_mindepth_1(self):
        for recursive in (True, False):
            cmd = self.tool.cmd(ListFilesInput(path="/tmp", recursive=recursive))
            assert "-mindepth" in cmd
            assert cmd[cmd.index("-mindepth") + 1] == "1"

    def test_cmd_non_recursive_by_default(self):
        cmd = self.tool.cmd(ListFilesInput(path="/tmp"))
        assert "-maxdepth" in cmd

    def test_cmd_non_recursive_has_maxdepth_1(self):
        cmd = self.tool.cmd(ListFilesInput(path="/tmp", recursive=False))
        assert cmd[cmd.index("-maxdepth") + 1] == "1"

    def test_cmd_recursive_excludes_maxdepth(self):
        cmd = self.tool.cmd(ListFilesInput(path="/tmp", recursive=True))
        assert "-maxdepth" not in cmd

    def test_cmd_full_non_recursive(self):
        cmd = self.tool.cmd(ListFilesInput(path="/var", recursive=False))
        assert cmd == ["find", "/var", "-mindepth", "1", "-maxdepth", "1"]

    def test_cmd_full_recursive(self):
        cmd = self.tool.cmd(ListFilesInput(path="/var", recursive=True))
        assert cmd == ["find", "/var", "-mindepth", "1"]

    def test_cmd_mindepth_before_maxdepth(self):
        cmd = self.tool.cmd(ListFilesInput(path="/tmp", recursive=False))
        assert cmd.index("-mindepth") < cmd.index("-maxdepth")


# ---------------------------------------------------------------------------
# MkdirTool
# ---------------------------------------------------------------------------


class TestMkdirTool:
    def setup_method(self):
        self.tool = MkdirTool()

    def test_name(self):
        assert self.tool.name == "mkdir"

    def test_timeout(self):
        assert MkdirTool.timeout == 5

    def test_cmd_structure(self):
        cmd = self.tool.cmd(MkdirInput(path="/tmp/a/newdir"))
        assert cmd == ["mkdir", "-p", "/tmp/a/newdir"]

    def test_p_flag_is_present(self):
        cmd = self.tool.cmd(MkdirInput(path="/tmp/a/newdir"))
        assert "-p" in cmd

    def test_cmd_path_is_last(self):
        cmd = self.tool.cmd(MkdirInput(path="/a/b/c"))
        assert cmd[-1] == "/a/b/c"

    def test_cmd_path_with_spaces(self):
        cmd = self.tool.cmd(MkdirInput(path="/my dir/sub dir"))
        assert cmd[-1] == "/my dir/sub dir"


# ---------------------------------------------------------------------------
# ReadFileTool
# ---------------------------------------------------------------------------


class TestReadFileTool:
    def setup_method(self):
        self.tool = ReadFileTool()
        self.path = "/etc/config.conf"

    def test_name(self):
        assert self.tool.name == "read_file"

    def test_timeout_inherits_cmdtool_default(self):
        assert ReadFileTool.timeout == 10

    # --- cat path (no offset, no limit) ---

    def test_cmd_no_offset_no_limit_uses_cat(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path))
        assert cmd == ["cat", self.path]

    def test_cmd_explicit_zero_offset_and_none_limit_uses_cat(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=0, limit=None))
        assert cmd == ["cat", self.path]

    def test_cmd_none_offset_and_none_limit_uses_cat(self):
        # safe_int(None, 0) == 0, so this falls through to cat
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=None, limit=None))
        assert cmd == ["cat", self.path]

    # --- awk with offset only (no limit) ---

    def test_cmd_offset_only_uses_awk(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=5))
        assert cmd[0] == "awk"

    def test_cmd_offset_only_correct_start_line(self):
        # offset is 0-indexed, awk NR is 1-indexed — so offset=5 means start at line 6
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=5))
        assert cmd == ["awk", "NR>=6", self.path]

    def test_cmd_offset_one_starts_at_line_two(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=1))
        assert cmd == ["awk", "NR>=2", self.path]

    def test_cmd_offset_only_path_is_last(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=10))
        assert cmd[-1] == self.path

    # --- awk with limit only (offset=0) ---

    def test_cmd_limit_only_uses_awk(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=0, limit=10))
        assert cmd[0] == "awk"

    def test_cmd_limit_only_correct_range(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=0, limit=10))
        assert cmd == ["awk", "NR>=1 && NR<=10", self.path]

    def test_cmd_limit_one_reads_single_first_line(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=0, limit=1))
        assert cmd == ["awk", "NR>=1 && NR<=1", self.path]

    # --- awk with both offset and limit ---

    def test_cmd_offset_and_limit_correct_range(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=3, limit=5))
        assert cmd == ["awk", "NR>=4 && NR<=8", self.path]

    def test_cmd_offset_and_limit_single_line(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=2, limit=1))
        assert cmd == ["awk", "NR>=3 && NR<=3", self.path]

    def test_cmd_offset_and_limit_path_is_last(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=1, limit=3))
        assert cmd[-1] == self.path

    @pytest.mark.parametrize(
        "offset,limit,expected_expr",
        [
            (0, 10, "NR>=1 && NR<=10"),
            (1, 10, "NR>=2 && NR<=11"),
            (5, 1, "NR>=6 && NR<=6"),
            (10, 5, "NR>=11 && NR<=15"),
            (0, 1, "NR>=1 && NR<=1"),
        ],
    )
    def test_cmd_awk_expression_arithmetic(self, offset, limit, expected_expr):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=offset, limit=limit))
        assert cmd[1] == expected_expr

    # --- safe_int coercion ---

    def test_cmd_float_offset_is_truncated(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=3.7, limit=None))  # type: ignore[arg-type]
        assert cmd == ["awk", "NR>=4", self.path]

    def test_cmd_none_offset_with_limit_treated_as_zero(self):
        cmd = self.tool.cmd(ReadFileInput(path=self.path, offset=None, limit=5))
        assert cmd == ["awk", "NR>=1 && NR<=5", self.path]
