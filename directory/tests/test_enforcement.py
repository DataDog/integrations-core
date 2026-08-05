# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""End-to-end enforcement tests for the configured traversal root.

This check exists to scan a user-supplied directory, which makes it the clearest
path-traversal case in the repository. These tests assert that a root outside the
allowlist is never actually read, exercising the real check and its real config
parsing rather than the interface in isolation.
"""

from unittest import mock

import pytest

from datadog_checks.directory import DirectoryCheck

pytestmark = pytest.mark.unit


@pytest.fixture
def enforcing_agent(datadog_agent, tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "a.txt").write_text("x")
    datadog_agent._config['integration_ignore_untrusted_file_params'] = True
    datadog_agent._config['integration_file_paths_allowlist'] = [str(allowed)]
    datadog_agent._config['integration_trusted_providers'] = ['file']
    yield allowed
    # The stub is a module-level singleton and only resets for tests that request
    # the fixture, so leaving enforcement enabled would silently gate unrelated
    # tests that do not.
    datadog_agent.reset()


def _untrusted_check(directory):
    check = DirectoryCheck('directory', {}, [{'directory': str(directory)}])
    check.provider = 'untrusted'
    check._AgentCheck__security_config = None
    check._AgentCheck__os_interface = None
    return check


def test_directory_outside_allowlist_is_never_read(enforcing_agent, tmp_path, aggregator):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("x")
    check = _untrusted_check(outside)

    with mock.patch('os.scandir') as real_scandir:
        with pytest.raises(PermissionError):
            check.check(None)

    assert not real_scandir.called, "enforcement did not stop the traversal of a disallowed directory"


def test_allowlisted_directory_is_scanned(enforcing_agent, aggregator):
    check = _untrusted_check(enforcing_agent)
    check.check(None)
    aggregator.assert_metric('system.disk.directory.files', count=1)
