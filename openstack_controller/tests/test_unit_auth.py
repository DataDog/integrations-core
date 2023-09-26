# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck
from datadog_checks.openstack_controller.api.type import ApiType
from tests.common import CONFIG_REST, CONFIG_SDK

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ('mock_http_post', 'connection_authorize', 'instance', 'api_type'),
    [
        pytest.param(
            {'exception': {'/identity/v3/auth/tokens': Exception()}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'exception': Exception()},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_post', 'connection_authorize'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_auth_exception(dd_run_check, caplog, instance, mock_http_post, connection_authorize, api_type):
    caplog.set_level(logging.INFO)
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Error while authorizing user' in caplog.text
    assert 'User successfully authorized' not in caplog.text


@pytest.mark.parametrize(
    ('mock_http_post', 'connection_authorize', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/auth/tokens': MockResponse(status_code=500)}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': MockResponse(status_code=500)},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_post', 'connection_authorize'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_auth_http_error(dd_run_check, caplog, instance, mock_http_post, connection_authorize, api_type):
    caplog.set_level(logging.INFO)
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Error while authorizing user' in caplog.text
    assert 'User successfully authorized' not in caplog.text


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            CONFIG_REST,
            id='api rest',
        ),
        pytest.param(
            CONFIG_SDK,
            id='api sdk',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_auth_ok(dd_run_check, caplog, instance):
    caplog.set_level(logging.INFO)
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Error while authorizing user' not in caplog.text
    assert 'User successfully authorized' in caplog.text
