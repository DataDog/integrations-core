# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Enforcement tests for the config-derived paths handed to the fdb client library.

`cluster_file`, `tls_certificate_file` and `tls_key_file` are opened by fdb
itself, so the read cannot be intercepted. They are validated and resolved at the
handoff instead.
"""

from unittest import mock

import pytest

from datadog_checks.foundationdb import FoundationdbCheck

pytestmark = pytest.mark.unit


@pytest.fixture
def enforcing_agent(datadog_agent, tmp_path):
    allowed = tmp_path / "allowed"
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
    check = FoundationdbCheck('foundationdb', {}, [instance])
    check.provider = 'untrusted'
    check._AgentCheck__security_config = None
    check._AgentCheck__os_interface = None
    return check


def test_disallowed_cluster_file_never_reaches_fdb(enforcing_agent):
    check = _untrusted_check({'cluster_file': '/tmp/evil/fdb.cluster'})
    with mock.patch('fdb.open') as fdb_open:
        with pytest.raises(PermissionError):
            check.construct_database()
    assert not fdb_open.called, "a disallowed cluster file must never reach fdb"


def test_disallowed_tls_certificate_never_reaches_fdb(enforcing_agent):
    check = _untrusted_check({'tls_certificate_file': '/tmp/evil/cert.pem'})
    with mock.patch('fdb.options.set_tls_cert_path') as set_cert, mock.patch('fdb.open'):
        with pytest.raises(PermissionError):
            check.construct_database()
    assert not set_cert.called, "a disallowed TLS certificate must never reach fdb"


def test_disallowed_tls_key_never_reaches_fdb(enforcing_agent):
    check = _untrusted_check({'tls_key_file': '/tmp/evil/key.pem'})
    with mock.patch('fdb.options.set_tls_key_path') as set_key, mock.patch('fdb.open'):
        with pytest.raises(PermissionError):
            check.construct_database()
    assert not set_key.called, "a disallowed TLS key must never reach fdb"


def test_allowlisted_cluster_file_is_used_unchanged(enforcing_agent):
    cluster = enforcing_agent / "fdb.cluster"
    cluster.write_text("")
    check = _untrusted_check({'cluster_file': str(cluster)})
    with mock.patch('fdb.open') as fdb_open:
        check.construct_database()
    assert fdb_open.called
    assert fdb_open.call_args.kwargs['cluster_file'] == str(cluster)
