# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.ai.tools.shell.ddev.env_stop import DdevEnvStopTool, EnvStopInput


def test_tool_meta():
    assert DdevEnvStopTool().name == "ddev_env_stop"
    assert DdevEnvStopTool.timeout == 120


def test_cmd():
    tool = DdevEnvStopTool()
    assert tool.cmd(EnvStopInput(integration="mycheck", environment="py3.11-1.23")) == [
        "ddev",
        "env",
        "stop",
        "mycheck",
        "py3.11-1.23",
    ]


def test_cmd_integration_and_env_order():
    tool = DdevEnvStopTool()
    cmd = tool.cmd(EnvStopInput(integration="mycheck", environment="py3.11-1.23"))
    assert cmd[-2] == "mycheck"
    assert cmd[-1] == "py3.11-1.23"
