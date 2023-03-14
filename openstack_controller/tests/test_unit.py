# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck
from datadog_checks.base import AgentCheck

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, expected_exception',
    [
        pytest.param(
            {},
            pytest.raises(
                Exception, match='Either `keystone_server_url` or `openstack_config_file_path` need to be configured'
            ),
            id='keystone_server_url_not_configured',
        ),
        pytest.param(
            {'keystone_server_url': 'http://127.0.0.1/identity'},
            pytest.raises(Exception, match='`user_name` and `user_password` need to be configured'),
            id='user_name_not_configured',
        ),
        pytest.param(
            {'keystone_server_url': 'http://127.0.0.1/identity', 'user_name': 'admin'},
            pytest.raises(Exception, match='`user_name` and `user_password` need to be configured'),
            id='user_password_not_configured',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://127.0.0.1:8080/identity',
                'user_name': 'admin',
                'user_password': 'password',
            },
            does_not_raise(),
            id='ok',
        ),
    ],
)
@mock.patch(
    'requests.get',
    side_effect=[
        MockResponse(status_code=200, json_data={}),
        MockResponse(status_code=200, json_data={'projects': []}),
    ],
)
@mock.patch(
    'requests.post', side_effect=[MockResponse(status_code=200, json_data={}, headers={'X-Subject-Token': 'abcd'})]
)
def test_config_validation(
    mocked_post,
    mocked_get,
    aggregator,
    dd_run_check,
    instance,
    expected_exception,
):
    check = OpenStackControllerCheck('test', {}, [instance])
    with expected_exception:
        dd_run_check(check)


@mock.patch('requests.get', side_effect=[MockResponse(status_code=500)])
def test_keystone_server_down(
    mocked_get,
    aggregator,
    dd_run_check,
):
    instance = {'keystone_server_url': 'http://127.0.0.1/identity', 'user_name': 'admin', 'user_password': 'password'}
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('openstack.keystone.api.up', status=check.CRITICAL)


@mock.patch('requests.get', side_effect=[MockResponse(status_code=200, json_data={})])
@mock.patch('requests.post', side_effect=[MockResponse(status_code=401)])
def test_keystone_server_up_and_credentials_fail(
    mocked_post,
    mocked_get,
    aggregator,
    dd_run_check,
):
    instance = {
        'keystone_server_url': 'http://127.0.0.1/identity',
        'user_name': 'admin',
        'user_password': 'password',
    }
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('openstack.keystone.api.up', status=check.CRITICAL)


# @mock.patch(
#     'requests.get',
#     side_effect=[
#         MockResponse(status_code=200, json_data={}),
#         MockResponse(status_code=200, json_data={'projects': []}),
#     ],
# )
# @mock.patch(
#     'requests.post', side_effect=[MockResponse(status_code=200, json_data={}, headers={'X-Subject-Token': 'abcd'})]
# )
@pytest.mark.vcr
def test_keystone_server_up_and_credentials_ok(
    # mocked_post,
    # mocked_get,
    # aggregator,
    # dd_run_check,
    dd_agent_check
):
    instance = {
        'keystone_server_url': 'http://10.164.0.83/identity',
        'user_name': 'admin',
        'user_password': 'password',
    }
    aggregator = dd_agent_check()
    # check = OpenStackControllerCheck('test', {}, [instance])
    # dd_run_check(check)
    aggregator.assert_service_check('openstack.keystone.api.up', status=AgentCheck.OK)
    assert False
