# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""End-to-end enforcement tests for the config-derived `gunicorn` binary.

Proves that the version probe reaches the OS through the check-bound, enforcing
interface rather than the unenforcing module-level singleton.
"""

from unittest import mock

import pytest

from datadog_checks.gunicorn import GUnicornCheck

pytestmark = pytest.mark.unit


@pytest.fixture
def enforcing_agent(datadog_agent, tmp_path):
    allowed = tmp_path / "allowed_bin"
    allowed.mkdir()
    datadog_agent._config['integration_ignore_untrusted_file_params'] = True
    datadog_agent._config['integration_file_paths_allowlist'] = [str(allowed)]
    datadog_agent._config['integration_trusted_providers'] = ['file']
    yield allowed
    # The stub is a module-level singleton and only resets for tests that request
    # the fixture, so leaving enforcement enabled would silently gate unrelated
    # tests that do not.
    datadog_agent.reset()


def _untrusted_check(gunicorn_path):
    check = GUnicornCheck('gunicorn', {}, [{'proc_name': 'web', 'gunicorn': gunicorn_path}])
    check.provider = 'untrusted'
    check._AgentCheck__security_config = None
    check._AgentCheck__os = None
    return check


def test_disallowed_gunicorn_binary_is_never_launched(enforcing_agent):
    check = _untrusted_check('/tmp/evil/gunicorn')
    with mock.patch('subprocess.run') as real_run:
        # A usable return value, so that a failure here is the enforcement
        # assertion below rather than an incidental error further downstream.
        real_run.return_value = mock.MagicMock(stdout='gunicorn (version 20.1.0)', stderr='', returncode=0)
        check._get_version()
    assert not real_run.called, "enforcement did not stop a disallowed binary from being executed"


def test_allowlisted_gunicorn_binary_is_launched(enforcing_agent):
    allowed = enforcing_agent / "gunicorn"
    allowed.write_text("#!/bin/sh\n")
    allowed.chmod(0o755)
    check = _untrusted_check(str(allowed))
    with mock.patch('subprocess.run') as real_run:
        real_run.return_value = mock.MagicMock(stdout='gunicorn (version 20.1.0)', stderr='', returncode=0)
        check._get_version()
    assert real_run.called, "an allowlisted binary must still run"
