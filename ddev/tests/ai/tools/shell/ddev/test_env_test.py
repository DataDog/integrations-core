# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.ai.tools.shell.ddev.env_test import DdevEnvTestTool, EnvTestInput


def test_tool_meta():
    assert DdevEnvTestTool().name == "ddev_env_test"
    assert DdevEnvTestTool.timeout == 600


def test_cmd_without_dev():
    tool = DdevEnvTestTool()
    assert tool.cmd(EnvTestInput(integration="mycheck", environment="py3.11-1.23")) == [
        "ddev",
        "--no-interactive",
        "env",
        "test",
        "mycheck",
        "py3.11-1.23",
    ]


def test_cmd_with_dev():
    tool = DdevEnvTestTool()
    assert tool.cmd(EnvTestInput(integration="mycheck", environment="py3.11-1.23", dev=True)) == [
        "ddev",
        "--no-interactive",
        "env",
        "test",
        "--dev",
        "mycheck",
        "py3.11-1.23",
    ]


def test_cmd_integration_and_env_order():
    tool = DdevEnvTestTool()
    cmd = tool.cmd(EnvTestInput(integration="mycheck", environment="py3.11-1.23"))
    assert cmd[-2] == "mycheck"
    assert cmd[-1] == "py3.11-1.23"
