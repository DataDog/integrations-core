# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""End-to-end enforcement tests.

The rest of the suite proves parity: the check behaves as it always did. These
tests prove the other half, that a config-derived binary outside the allowlist is
never launched. They exercise the real check, its real config parsing and its
real interface binding, so they would fail if the check reached the OS through
the unenforcing module-level singleton instead of `self.os`.
"""

from unittest import mock

import pytest

from datadog_checks.slurm.check import SlurmCheck

pytestmark = pytest.mark.unit


@pytest.fixture
def enforcing_agent(datadog_agent, tmp_path):
    """Agent config with point-of-use enforcement on and a narrow allowlist."""
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


def _untrusted_check(instance):
    check = SlurmCheck('slurm', {}, [instance])
    check.provider = 'untrusted'
    # Drop caches so the new provider/agent config is picked up.
    check._AgentCheck__security_config = None
    check._AgentCheck__os = None
    return check


def test_disallowed_sinfo_binary_is_never_launched(enforcing_agent, instance):
    instance = dict(instance, collect_sinfo_stats=True, sinfo_path='/tmp/evil/sinfo')
    check = _untrusted_check(instance)

    with mock.patch('subprocess.run') as real_run:
        check.check(None)

    assert not real_run.called, "enforcement did not stop a disallowed binary from being executed"


def test_allowlisted_sinfo_binary_is_launched(enforcing_agent, instance):
    allowed_sinfo = enforcing_agent / "sinfo"
    allowed_sinfo.write_text("#!/bin/sh\n")
    allowed_sinfo.chmod(0o755)
    instance = dict(instance, collect_sinfo_stats=True, sinfo_path=str(allowed_sinfo))
    check = _untrusted_check(instance)

    with mock.patch('subprocess.run') as real_run:
        real_run.return_value = mock.MagicMock(stdout='', stderr='', returncode=0)
        check.check(None)

    assert real_run.called, "an allowlisted binary must still run"


def test_trusted_provider_is_not_blocked(enforcing_agent, instance):
    instance = dict(instance, collect_sinfo_stats=True, sinfo_path='/tmp/evil/sinfo')
    check = SlurmCheck('slurm', {}, [instance])
    check.provider = 'file'  # trusted
    check._AgentCheck__security_config = None
    check._AgentCheck__os = None

    with mock.patch('subprocess.run') as real_run:
        real_run.return_value = mock.MagicMock(stdout='', stderr='', returncode=0)
        check.check(None)

    assert real_run.called, "a trusted provider must not be subject to the allowlist"
