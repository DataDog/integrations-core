# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from pydantic import ValidationError

from ddev.ai.tools.shell.ddev.release_changelog import DdevReleaseChangelogTool, ReleaseChangelogInput


def test_tool_meta():
    assert DdevReleaseChangelogTool().name == "ddev_release_changelog"
    assert DdevReleaseChangelogTool.timeout == 30


def test_cmd_fixed():
    tool = DdevReleaseChangelogTool()
    assert tool.cmd(ReleaseChangelogInput(change_type="fixed", integration="mycheck", message="Fix a bug")) == [
        "ddev",
        "release",
        "changelog",
        "new",
        "fixed",
        "mycheck",
        "-m",
        "Fix a bug",
    ]


def test_cmd_added():
    tool = DdevReleaseChangelogTool()
    assert tool.cmd(ReleaseChangelogInput(change_type="added", integration="mycheck", message="Add new feature")) == [
        "ddev",
        "release",
        "changelog",
        "new",
        "added",
        "mycheck",
        "-m",
        "Add new feature",
    ]


def test_cmd_changed():
    tool = DdevReleaseChangelogTool()
    assert tool.cmd(ReleaseChangelogInput(change_type="changed", integration="mycheck", message="Breaking change")) == [
        "ddev",
        "release",
        "changelog",
        "new",
        "changed",
        "mycheck",
        "-m",
        "Breaking change",
    ]


def test_cmd_message_placement():
    tool = DdevReleaseChangelogTool()
    cmd = tool.cmd(ReleaseChangelogInput(change_type="fixed", integration="mycheck", message="Some message"))
    assert cmd[-2] == "-m"
    assert cmd[-1] == "Some message"


def test_invalid_change_type_raises():
    with pytest.raises(ValidationError):
        ReleaseChangelogInput(change_type="patch", integration="mycheck", message="Some message")
