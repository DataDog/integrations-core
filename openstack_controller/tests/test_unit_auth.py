# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import os

import pytest

import tests.configs as configs
from datadog_checks.dev.http import MockResponse

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(os.environ.get('OPENSTACK_E2E_LEGACY') == 'true', reason='Not Legacy test'),
]


@pytest.mark.parametrize(
    ('mock_http_post', 'connection_authorize', 'instance'),
    [
        pytest.param(
            {'exception': {'/identity/v3/auth/tokens': Exception()}},
            None,
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'exception': Exception()},
            configs.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_post', 'connection_authorize'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_auth_exception(check, dd_run_check, caplog):
    caplog.set_level(logging.INFO)
    dd_run_check(check)
    assert 'Error while authorizing user' in caplog.text
    assert 'User successfully authorized' not in caplog.text


@pytest.mark.parametrize(
    ('mock_http_post', 'connection_authorize', 'instance'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/auth/tokens': MockResponse(status_code=500)}},
            None,
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': MockResponse(status_code=500)},
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
