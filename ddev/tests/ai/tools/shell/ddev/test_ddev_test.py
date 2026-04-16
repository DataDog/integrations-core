# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.ai.tools.shell.ddev.ddev_test import DdevTestTool, TestInput


def test_tool_meta():
    assert DdevTestTool().name == "ddev_test"
    assert DdevTestTool.timeout == 600


def test_cmd_no_flags():
    tool = DdevTestTool()
    cmd = tool.cmd(TestInput(integration="mycheck"))
    assert "--no-interactive" in cmd
    assert "-f" not in cmd
    assert "-s" not in cmd
    assert "-fs" not in cmd


def test_cmd_fmt_only():
    tool = DdevTestTool()
    cmd = tool.cmd(TestInput(integration="mycheck", fmt=True))
    assert "-f" in cmd
    assert "-s" not in cmd
    assert "-fs" not in cmd


def test_cmd_style_only():
    tool = DdevTestTool()
    cmd = tool.cmd(TestInput(integration="mycheck", style=True))
    assert "-s" in cmd
    assert "-f" not in cmd
    assert "-fs" not in cmd


def test_cmd_fmt_and_style():
    tool = DdevTestTool()
    cmd = tool.cmd(TestInput(integration="mycheck", fmt=True, style=True))
    assert "-fs" in cmd
    assert "-f" not in cmd
    assert "-s" not in cmd


def test_cmd_integration_last():
    tool = DdevTestTool()
    cmd = tool.cmd(TestInput(integration="mycheck", fmt=True, style=True))
    assert cmd[-1] == "mycheck"
