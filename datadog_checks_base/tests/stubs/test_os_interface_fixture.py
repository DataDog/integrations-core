# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.os_interface import os_interface as singleton

pytestmark = pytest.mark.unit


def test_fixture_redirects_check_property(mock_os_interface):
    """A check's self.os_interface resolves to the injected double."""
    mock_os_interface.add_file("/etc/conf", "data")

    check = AgentCheck("test", {}, [{}])
    assert check.os_interface is mock_os_interface
    assert check.os_interface.exists("/etc/conf") is True
    assert check.os_interface.exists("/missing") is False


def test_fixture_redirects_module_singleton(mock_os_interface):
    """Module-level helpers that use the os_interface singleton are covered too."""
    mock_os_interface.set_command_output("id -u", stdout="0")

    # This mirrors how a module-level helper calls the shared singleton.
    out, err, code = singleton.get_subprocess_output("id -u", None)
    assert (out, err, code) == ("0", "", 0)
    assert singleton.exists("/anything") is False


def test_singleton_restored_after_fixture():
    """Outside the fixture the singleton is the real, unpatched interface."""
    # The real interface delegates to the stdlib; a nonexistent path is False,
    # but the method is the genuine bound method, not a MagicMock.
    assert not hasattr(singleton.exists, "assert_called")
