# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import os

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
    builds. A real keystoneauth session is constructed here so the assertion covers the transport
    that openstacksdk actually uses.
    """
    check = openstack_controller_check({**configs.SDK, **instance_overrides})
    check.run_check_initializations()
    captured = {}

    def connection(cloud, session, region_name):
        captured['session'] = session
        return mock.MagicMock(session=session)

    with mock.patch('openstack.connection.Connection', side_effect=connection):
        check.api.authorize_user()

    assert captured['session'].session.proxies == expected_proxies
