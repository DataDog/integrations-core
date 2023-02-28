# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
import re

import pytest

from datadog_checks.openstack_controller import OpenStackControllerCheck

from .common import CHECK_NAME, CONFIG_FILE_INSTANCE, TEST_OPENSTACK_NO_AUTH_CONFIG_PATH


@pytest.mark.parametrize(
    'options, exception_msg',
    [
        pytest.param({'user': {'domain': {'id': 'test_id'}}}, 'Missing name', id='empty'),
        pytest.param({'user': {'domain': {'id': 'test_id'}}}, 'Missing name', id='empty name'),
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'openstack_config_file_path': 'test',
            },
            'Missing name',
            id='no name, keystone_server_url, cfg path',
        ),
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'openstack_cloud_name': 'test',
                'openstack_config_file_path': 'test',
                'name': 'test',
            },
            'Cloud test was not found.',
            id='bad openstack_cloud_name',
        ),
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'openstack_config_file_path': 'test',
                'name': 'test',
            },
            'Auth plugin requires parameters which were not given: auth_url',
            id='bad openstack_cloud_name',
        ),
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'name': 'test',
                'openstack_cloud_name': 'test_cloud',
                'openstack_config_file_path': TEST_OPENSTACK_NO_AUTH_CONFIG_PATH,
            },
            re.escape('__init__() got an unexpected keyword argument \'auth_type\''),
            id='bad config file',
        ),
    ],
)
def test_config_invalid(options, exception_msg):
    instance = copy.deepcopy(CONFIG_FILE_INSTANCE)
    del instance['openstack_config_file_path']
    del instance['name']
    del instance['openstack_cloud_name']
    del instance['user']

    instance.update(options)

    check = OpenStackControllerCheck(CHECK_NAME, {}, [instance])

    with pytest.raises(Exception, match=exception_msg):
        check.check(instance)


@pytest.mark.parametrize(
    'options, warning_msg',
    [
        pytest.param(
            {'name': 'test'},
            'Either keystone_server_url or openstack_config_file_path need to be provided',
            id='no keystone_server_url, no cfg path',
        ),
        pytest.param(
            {'name': 'test', 'keystone_server_url': 'http://localhost'},
            'The agent could not contact the specified identity server',
            id='no user',
        ),
        pytest.param(
            {'name': 'test', 'keystone_server_url': 'http://localhost', 'user': {}},
            'Please specify the user via the `user` variable in your init_config.',
            id='bad user',
        ),
        pytest.param(
            {
                'name': 'test',
                'keystone_server_url': 'http://localhost',
                'user': {'password': 'test_pass', 'domain': {'id': 'test_id'}},
            },
            'Please specify the user via the `user` variable in your init_config.',
            id='no user name',
        ),
        pytest.param(
            {
                'name': 'test',
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'test_name', 'domain': {'id': 'test_id'}},
            },
            'Please specify the user via the `user` variable in your init_config.',
            id='no user pw',
        ),
    ],
)
def test_config_warning(options, warning_msg, caplog):
    instance = copy.deepcopy(CONFIG_FILE_INSTANCE)
    del instance['openstack_config_file_path']
    del instance['name']
    del instance['openstack_cloud_name']

    instance.update(options)
    caplog.set_level(logging.WARN)

    check = OpenStackControllerCheck(CHECK_NAME, {}, [instance])

    # try:
    check.check(instance)
    assert warning_msg in caplog.text
