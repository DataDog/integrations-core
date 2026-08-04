# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Enforcement tests for the config-derived TLS trust paths.

`ssl_cafile` and `ssl_capath` are handed to `ssl.SSLContext`, which opens them
itself. A Python-level interface cannot intercept that read, so the path is
validated through `resolve_path` before the handoff. These tests prove the
validation happens and that the resolved path is what ssl receives.
"""

from unittest import mock

import pytest

from datadog_checks.esxi import EsxiCheck

pytestmark = pytest.mark.unit


@pytest.fixture
def enforcing_agent(datadog_agent, tmp_path):
    allowed = tmp_path / "allowed_certs"
    allowed.mkdir()
    datadog_agent._config['integration_ignore_untrusted_file_params'] = True
    datadog_agent._config['integration_path_enforcement_mode'] = 'enforce'
    datadog_agent._config['integration_file_paths_allowlist'] = [str(allowed)]
    datadog_agent._config['integration_trusted_providers'] = ['file']
    yield allowed


def _untrusted_check(instance):
    check = EsxiCheck('esxi', {}, [instance])
    check.provider = 'untrusted'
    check._AgentCheck__security_config = None
    check._AgentCheck__os_interface = None
    return check


def _base_instance(**kw):
    instance = {'host': 'esxi.example.com', 'username': 'u', 'password': 'p', 'ssl_verify': True}
    instance.update(kw)
    return instance


def test_disallowed_cafile_is_rejected_before_ssl_sees_it(enforcing_agent):
    check = _untrusted_check(_base_instance(ssl_cafile='/tmp/evil/ca.pem'))
    with (
        mock.patch('ssl.SSLContext.load_verify_locations') as load,
        mock.patch('datadog_checks.esxi.check.connect.SmartConnect', side_effect=RuntimeError('stop here')),
    ):
        with pytest.raises(PermissionError):
            check.initiate_api_connection()
    assert not load.called, "a disallowed CA file must never reach ssl"


def test_disallowed_capath_is_rejected_before_ssl_sees_it(enforcing_agent):
    check = _untrusted_check(_base_instance(ssl_capath='/tmp/evil/certs'))
    with (
        mock.patch('ssl.SSLContext.load_verify_locations') as load,
        mock.patch('datadog_checks.esxi.check.connect.SmartConnect', side_effect=RuntimeError('stop here')),
    ):
        with pytest.raises(PermissionError):
            check.initiate_api_connection()
    assert not load.called, "a disallowed CA path must never reach ssl"


def test_allowlisted_cafile_is_passed_to_ssl(enforcing_agent):
    cafile = enforcing_agent / "ca.pem"
    cafile.write_text("")
    check = _untrusted_check(_base_instance(ssl_cafile=str(cafile)))
    with (
        mock.patch('ssl.SSLContext.load_verify_locations') as load,
        mock.patch.object(check, 'log'),
        mock.patch('datadog_checks.esxi.check.connect.SmartConnect', side_effect=RuntimeError('stop here')),
    ):
        with pytest.raises(Exception):
            check.initiate_api_connection()
    assert load.called, "an allowlisted CA file must still be used"
    # The resolved (realpath) form is what ssl receives.
    assert load.call_args.kwargs['cafile'] == str(cafile.resolve())


def test_enforcement_off_by_default_allows_any_cafile(datadog_agent):
    datadog_agent._config['integration_ignore_untrusted_file_params'] = True
    datadog_agent._config['integration_file_paths_allowlist'] = []
    datadog_agent._config['integration_trusted_providers'] = ['file']
    check = _untrusted_check(_base_instance(ssl_cafile='/tmp/evil/ca.pem'))
    with (
        mock.patch('ssl.SSLContext.load_verify_locations') as load,
        mock.patch('datadog_checks.esxi.check.connect.SmartConnect', side_effect=RuntimeError('stop here')),
    ):
        with pytest.raises(Exception):
            check.initiate_api_connection()
    assert load.called, "enforcement must default to off"
