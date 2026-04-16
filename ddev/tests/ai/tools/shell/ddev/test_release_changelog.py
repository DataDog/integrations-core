# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from pydantic import ValidationError

from ddev.ai.tools.shell.ddev.release_changelog import DdevReleaseChangelogTool, ReleaseChangelogInput


def test_tool_meta():
    assert DdevReleaseChangelogTool().name == "ddev_release_changelog"
    assert DdevReleaseChangelogTool.timeout == 30


@pytest.mark.parametrize("change_type", ["fixed", "added", "changed"])
def test_cmd_change_type(change_type: str):
    cmd = DdevReleaseChangelogTool().cmd(
        ReleaseChangelogInput(change_type=change_type, integration="mycheck", message="msg")
    )
    assert cmd[4] == change_type


def test_cmd_message_placement():
    tool = DdevReleaseChangelogTool()
    cmd = tool.cmd(ReleaseChangelogInput(change_type="fixed", integration="mycheck", message="Some message"))
    assert cmd[-2] == "-m"
    assert cmd[-1] == "Some message"


def test_invalid_change_type_raises():
    with pytest.raises(ValidationError):
        ReleaseChangelogInput(change_type="patch", integration="mycheck", message="Some message")
