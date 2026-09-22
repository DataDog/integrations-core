# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import os
import ssl

import mock
import pytest

import tests.configs as configs
from datadog_checks.dev.http import MockHTTPResponse

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(os.environ.get('OPENSTACK_E2E_LEGACY') == 'true', reason='Not Legacy test'),
]


@pytest.mark.parametrize(
    ('mock_http_post', 'connection_authorize', 'instance'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/auth/tokens': MockHTTPResponse(status_code=500)}},
            None,
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': MockHTTPResponse(status_code=500)},
            configs.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_post', 'connection_authorize'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_auth_http_error(check, dd_run_check, caplog):
    caplog.set_level(logging.INFO)
    dd_run_check(check)
    assert 'Error while authorizing user' in caplog.text
    assert 'User successfully authorized' not in caplog.text


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_auth_ok(check, dd_run_check, caplog):
    caplog.set_level(logging.INFO)
    dd_run_check(check)
    assert 'Error while authorizing user' not in caplog.text
    assert 'User successfully authorized' in caplog.text


def build_sdk_transport(check):
    """Authorize against a real keystoneauth session and return the requests transport it built.

    Only the openstacksdk connection is mocked, so assertions cover the transport that
    openstacksdk actually issues requests on.
    """
    check.run_check_initializations()
    captured = {}

    def connection(cloud, session, region_name):
        captured['session'] = session
        return mock.MagicMock(session=session)

    with mock.patch('openstack.connection.Connection', side_effect=connection):
        check.api.authorize_user()

    return captured['session'].session


@pytest.mark.parametrize(
    ('instance_overrides', 'expected_proxies'),
    [
        pytest.param({}, {}, id='no proxy configured'),
        pytest.param(
            {'proxy': {'http': 'http://proxy:3128', 'https': 'http://proxy:3128'}},
            {'http': 'http://proxy:3128', 'https': 'http://proxy:3128'},
            id='proxy configured',
        ),
        pytest.param({'skip_proxy': True}, {'http': '', 'https': ''}, id='skip_proxy disables proxying'),
    ],
)
@pytest.mark.usefixtures('openstack_v3_password')
def test_sdk_transport_uses_configured_proxy(openstack_controller_check, instance_overrides, expected_proxies):
    """Proxy settings must reach openstacksdk traffic.

    keystoneauth1 takes no proxy argument, so the only place they can apply is the transport it
    builds.
    """
    transport = build_sdk_transport(openstack_controller_check({**configs.SDK, **instance_overrides}))

    assert transport.proxies == expected_proxies


@pytest.mark.parametrize(
    ('instance_overrides', 'expected_auth'),
    [
        pytest.param({}, None, id='no auth configured'),
        pytest.param({'username': 'user', 'password': 'pass'}, ('user', 'pass'), id='basic auth configured'),
    ],
)
@pytest.mark.usefixtures('openstack_v3_password')
def test_sdk_transport_uses_configured_auth(openstack_controller_check, instance_overrides, expected_auth):
    """Configured HTTP auth must reach openstacksdk traffic.

    keystoneauth1 takes no auth argument, so the transport it builds is the only place it can go.
    Leaving the transport without it also hands the requests .netrc lookup an opening, because that
    lookup only runs when the session carries no auth of its own.
    """
    transport = build_sdk_transport(openstack_controller_check({**configs.SDK, **instance_overrides}))

    assert transport.auth == expected_auth


@pytest.mark.parametrize(
    ('instance_overrides', 'expected_check_hostname', 'expected_verify_mode'),
    [
        pytest.param({}, True, ssl.CERT_REQUIRED, id='defaults verify and validate hostname'),
        pytest.param(
            {'tls_verify': True, 'tls_validate_hostname': False},
            False,
            ssl.CERT_REQUIRED,
            id='hostname validation disabled',
        ),
        pytest.param({'tls_verify': False}, False, ssl.CERT_NONE, id='verification disabled'),
    ],
)
@pytest.mark.usefixtures('openstack_v3_password')
def test_sdk_transport_applies_tls_config(
    openstack_controller_check, instance_overrides, expected_check_hostname, expected_verify_mode
):
    """TLS settings must reach openstacksdk traffic.

    keystoneauth1 accepts only verify and cert, which cannot express tls_validate_hostname,
    tls_ciphers, tls_private_key_password or tls_intermediate_ca_certs. Those live on the
    SSLContext, so the HTTPS adapter carrying it has to be applied to the transport keystoneauth
    builds, otherwise the four options are silently dropped on this path.
    """
    transport = build_sdk_transport(openstack_controller_check({**configs.SDK, **instance_overrides}))

    context = transport.get_adapter('https://').ssl_context
    assert context.check_hostname is expected_check_hostname
    assert context.verify_mode == expected_verify_mode
