# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from pydantic import ValidationError

from ddev.ai.tools.shell.ddev.create import CreateInput, DdevCreateTool
from ddev.ai.tools.shell.ddev.ddev_test import DdevTestInput, DdevTestTool
from ddev.ai.tools.shell.ddev.env_show import DdevEnvShowTool, EnvShowInput
from ddev.ai.tools.shell.ddev.env_start import DdevEnvStartTool, EnvStartInput
from ddev.ai.tools.shell.ddev.env_stop import DdevEnvStopTool, EnvStopInput
from ddev.ai.tools.shell.ddev.env_test import DdevEnvTestTool, EnvTestInput
from ddev.ai.tools.shell.ddev.release_changelog import DdevReleaseChangelogTool, ReleaseChangelogInput

# --- ddev create ---


def test_create_cmd_basic():
    tool = DdevCreateTool()
    assert tool.cmd(CreateInput(integration="my_check", integration_type="check")) == [
        "ddev",
        "--no-interactive",
        "create",
        "--type",
        "check",
        "--skip-manifest",
        "My_check",
    ]


@pytest.mark.parametrize(
    "integration_type", ["check", "check_only", "event", "jmx", "logs", "metrics_crawler", "snmp_tile", "tile"]
)
def test_create_cmd_all_types(integration_type: str):
    cmd = DdevCreateTool().cmd(CreateInput(integration="my_check", integration_type=integration_type))
    assert cmd[cmd.index("--type") + 1] == integration_type


def test_create_invalid_type_raises():
    with pytest.raises(ValidationError):
        CreateInput(integration="my_check", integration_type="custom")


# --- ddev test ---


def test_ddev_test_cmd_no_flags():
    cmd = DdevTestTool().cmd(DdevTestInput(integration="mycheck"))
    assert "--no-interactive" in cmd
    assert "-s" not in cmd
    assert "-fs" not in cmd


def test_ddev_test_cmd_lint_only():
    cmd = DdevTestTool().cmd(DdevTestInput(integration="mycheck", lint=True))
    assert "-s" in cmd
    assert "-fs" not in cmd


def test_ddev_test_cmd_fmt_only():
    cmd = DdevTestTool().cmd(DdevTestInput(integration="mycheck", fmt=True))
    assert "-fs" in cmd
    assert "-s" not in cmd


def test_ddev_test_cmd_fmt_and_lint():
    cmd = DdevTestTool().cmd(DdevTestInput(integration="mycheck", fmt=True, lint=True))
    assert "-fs" in cmd
    assert "-s" in cmd


def test_ddev_test_cmd_integration_last():
    cmd = DdevTestTool().cmd(DdevTestInput(integration="mycheck", fmt=True, lint=True))
    assert cmd[-1] == "mycheck"


def test_ddev_test_cmd_pytest_args():
    cmd = DdevTestTool().cmd(DdevTestInput(integration="mycheck", pytest_args=["-k", "test_my_func", "-s"]))
    separator_idx = cmd.index("--")
    assert cmd[separator_idx + 1 :] == ["-k", "test_my_func", "-s"]
    assert cmd[separator_idx - 1] == "mycheck"


def test_ddev_test_cmd_no_pytest_args_omits_separator():
    cmd = DdevTestTool().cmd(DdevTestInput(integration="mycheck"))
    assert "--" not in cmd


# --- ddev env show ---


def test_env_show_cmd():
    assert DdevEnvShowTool().cmd(EnvShowInput(integration="mycheck")) == [
        "ddev",
        "--no-interactive",
        "env",
        "show",
        "mycheck",
    ]


# --- ddev env start ---


@pytest.mark.parametrize(
    "dev,expected",
    [
        (False, ["ddev", "--no-interactive", "env", "start", "mycheck", "py3.11-1.23"]),
        (True, ["ddev", "--no-interactive", "env", "start", "--dev", "mycheck", "py3.11-1.23"]),
    ],
)
def test_env_start_cmd(dev, expected):
    assert DdevEnvStartTool().cmd(EnvStartInput(integration="mycheck", environment="py3.11-1.23", dev=dev)) == expected


# --- ddev env test ---


@pytest.mark.parametrize(
    "dev,expected",
    [
        (False, ["ddev", "--no-interactive", "env", "test", "mycheck", "py3.11-1.23"]),
        (True, ["ddev", "--no-interactive", "env", "test", "--dev", "mycheck", "py3.11-1.23"]),
    ],
)
def test_env_test_cmd(dev, expected):
    assert DdevEnvTestTool().cmd(EnvTestInput(integration="mycheck", environment="py3.11-1.23", dev=dev)) == expected


# --- ddev env stop ---


def test_env_stop_cmd():
    assert DdevEnvStopTool().cmd(EnvStopInput(integration="mycheck", environment="py3.11-1.23")) == [
        "ddev",
        "--no-interactive",
        "env",
        "stop",
        "mycheck",
        "py3.11-1.23",
    ]


# --- ddev release changelog ---


@pytest.mark.parametrize("change_type", ["fixed", "added", "changed"])
def test_release_changelog_cmd_change_type(change_type: str):
    cmd = DdevReleaseChangelogTool().cmd(
        ReleaseChangelogInput(change_type=change_type, integration="mycheck", message="msg")
    )
    assert cmd[4] == change_type


def test_release_changelog_cmd_message_placement():
    cmd = DdevReleaseChangelogTool().cmd(
        ReleaseChangelogInput(change_type="fixed", integration="mycheck", message="Some message")
    )
    assert cmd[-2] == "-m"
    assert cmd[-1] == "Some message"


def test_release_changelog_invalid_change_type_raises():
    with pytest.raises(ValidationError):
        ReleaseChangelogInput(change_type="patch", integration="mycheck", message="Some message")
