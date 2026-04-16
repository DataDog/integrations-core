# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from pydantic import ValidationError

from ddev.ai.tools.shell.ddev.create import CreateInput, DdevCreateTool


def test_tool_meta():
    assert DdevCreateTool().name == "ddev_create"
    assert DdevCreateTool.timeout == 60


def test_cmd_basic():
    tool = DdevCreateTool()
    assert tool.cmd(CreateInput(integration="my_check", integration_type="check")) == [
        "ddev",
        "--no-interactive",
        "create",
        "--type",
        "check",
        "--skip-manifest",
        "my_check",
    ]


@pytest.mark.parametrize(
    "integration_type", ["check", "check_only", "event", "jmx", "logs", "metrics_crawler", "snmp_tile", "tile"]
)
def test_cmd_all_types(integration_type: str):
    tool = DdevCreateTool()
    cmd = tool.cmd(CreateInput(integration="my_check", integration_type=integration_type))
    assert "--type" in cmd
    assert cmd[cmd.index("--type") + 1] == integration_type


def test_cmd_integration_name_last():
    tool = DdevCreateTool()
    cmd = tool.cmd(CreateInput(integration="my_check", integration_type="jmx"))
    assert cmd[-1] == "my_check"


def test_invalid_type_raises():
    with pytest.raises(ValidationError):
        CreateInput(integration="my_check", integration_type="custom")
