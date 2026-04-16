# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.ai.tools.shell.ddev.env_start import DdevEnvStartTool, EnvStartInput


def test_tool_meta():
    assert DdevEnvStartTool().name == "ddev_env_start"
    assert DdevEnvStartTool.timeout == 300


def test_cmd_without_dev():
    tool = DdevEnvStartTool()
    assert tool.cmd(EnvStartInput(integration="mycheck", environment="py3.11-1.23")) == [
        "ddev",
        "--no-interactive",
        "env",
        "start",
        "mycheck",
        "py3.11-1.23",
    ]


def test_cmd_with_dev():
    tool = DdevEnvStartTool()
    assert tool.cmd(EnvStartInput(integration="mycheck", environment="py3.11-1.23", dev=True)) == [
        "ddev",
        "--no-interactive",
        "env",
        "start",
        "--dev",
        "mycheck",
        "py3.11-1.23",
    ]


def test_cmd_integration_and_env_order():
    tool = DdevEnvStartTool()
    cmd = tool.cmd(EnvStartInput(integration="mycheck", environment="py3.11-1.23"))
    assert cmd[-2] == "mycheck"
    assert cmd[-1] == "py3.11-1.23"
