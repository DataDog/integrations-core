# # (C) Datadog, Inc. 2023-present
# # All rights reserved
# # Licensed under a 3-clause BSD style license (see LICENSE)
# import logging
import re

import pytest

from datadog_checks.openstack_controller import OpenStackControllerCheck

from .common import TEST_OPENSTACK_CONFIG_PATH, TEST_OPENSTACK_NO_AUTH_CONFIG_PATH

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, exception_msg',
    [
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'openstack_cloud_name': 'test',
                'openstack_config_file_path': TEST_OPENSTACK_CONFIG_PATH,
            },
            'Cloud test was not found.',
            id='bad openstack_cloud_name',
        ),
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'openstack_config_file_path': 'test',
            },
            'Auth plugin requires parameters which were not given: auth_url',
            id='openstack_config_file_path doesn\' exist',
        ),
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'openstack_cloud_name': 'test_cloud',
                'openstack_config_file_path': TEST_OPENSTACK_NO_AUTH_CONFIG_PATH,
            },
            re.escape('__init__() got an unexpected keyword argument \'auth_type\''),
            id='invalid openstack_config_file',
        ),
        pytest.param(
            {},
            'Either keystone_server_url or openstack_config_file_path need to be provided.',
            id='no keystone_server_url, no cfg path',
        ),
        pytest.param(
            {'keystone_server_url': 'http://localhost'},
            'Please specify `user_name` in your config.',
            id='no user_name',
        ),
        pytest.param(
            {'keystone_server_url': 'http://localhost', 'user_name': 'admin'},
            'Please specify `user_password` in your config.',
            id='no user_password',
        ),
        pytest.param(
            {'keystone_server_url': 'http://localhost', 'user': {}},
            'The user should look like: '
            '{"name": "my_name", "password": "my_password", "domain": {"id": "my_domain_id"}}',
            id='no name in user (legacy config)',
        ),
        pytest.param(
            {'keystone_server_url': 'http://localhost', 'user': {'name': 'my_name'}},
            'The user should look like: '
            '{"name": "my_name", "password": "my_password", "domain": {"id": "my_domain_id"}}',
            id='no password in user (legacy config)',
        ),
        pytest.param(
            {'keystone_server_url': 'http://localhost', 'user': {'name': 'my_name', 'password': 'my_password'}},
            'The user should look like: '
            '{"name": "my_name", "password": "my_password", "domain": {"id": "my_domain_id"}}',
            id='no domain in user (legacy config)',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name', 'password': 'my_password', 'domain': {}},
            },
            'The user should look like: '
            '{"name": "my_name", "password": "my_password", "domain": {"id": "my_domain_id"}}',
            id='no domain id in user (legacy config)',
        ),
    ],
)
def test_config_exceptions(instance, exception_msg):
    with pytest.raises(Exception, match=exception_msg):
        OpenStackControllerCheck('test', {}, [instance])


def test_legacy_config_ok():
    instance = {
        'keystone_server_url': 'http://localhost',
        'user': {'name': 'my_name', 'password': 'my_password', 'domain': {'id': 'default'}},
    }
    OpenStackControllerCheck('test', {}, [instance])


def test_config_ok():
    instance = {
        'keystone_server_url': 'http://localhost',
        'user_name': 'my_name',
        'user_password': 'my_password',
        'domain_id': 'default',
    }
    OpenStackControllerCheck('test', {}, [instance])
