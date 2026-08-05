# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.safe_os import safe_os as singleton

pytestmark = pytest.mark.unit


def test_fixture_redirects_check_property(mock_safe_os):
    """A check's self.safe_os resolves to the injected double."""
    mock_safe_os.add_file("/etc/conf", "data")

    check = AgentCheck("test", {}, [{}])
    assert check.safe_os is mock_safe_os
    assert check.safe_os.exists("/etc/conf") is True
    assert check.safe_os.exists("/missing") is False


def test_fixture_redirects_module_singleton(mock_safe_os):
    """Module-level helpers that use the safe_os singleton are covered too."""
    mock_safe_os.set_command_output("id -u", stdout="0")

    # This mirrors how a module-level helper calls the shared singleton.
    out, err, code = singleton.get_subprocess_output("id -u", None)
    assert (out, err, code) == ("0", "", 0)
    assert singleton.exists("/anything") is False


def test_singleton_restored_after_fixture():
    """Outside the fixture the singleton is the real, unpatched interface."""
    # The real interface delegates to the stdlib; a nonexistent path is False,
    # but the method is the genuine bound method, not a MagicMock.
    assert not hasattr(singleton.exists, "assert_called")
