# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import os
import re

import pytest

from datadog_checks.openstack_controller.legacy.openstack_controller_legacy import OpenStackControllerLegacyCheck

from .common import CHECK_NAME, TEST_OPENSTACK_NO_AUTH_CONFIG_PATH

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        os.environ.get('OPENSTACK_E2E_LEGACY') is None or os.environ.get('OPENSTACK_E2E_LEGACY') == 'false',
        reason='Legacy test',
    ),
]


@pytest.mark.parametrize(
    'instance, exception_msg',
    [
        pytest.param({'user': {'domain': {'id': 'test_id'}}}, 'Missing name', id='empty name'),
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'openstack_config_file_path': 'test',
            },
            'Missing name',
            id='no name, keystone_server_url, cfg path',
        ),
    ],
)
def test_config_invalid(instance, exception_msg, dd_run_check):

    check = OpenStackControllerLegacyCheck(CHECK_NAME, {}, [instance])

    with pytest.raises(Exception, match=exception_msg):
        dd_run_check(check)


@pytest.mark.parametrize(
    'instance, exception_msg',
    [
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
            id='openstack_config_file_path doesn\' exist',
        ),
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'name': 'test',
                'openstack_cloud_name': 'test_cloud',
                'openstack_config_file_path': TEST_OPENSTACK_NO_AUTH_CONFIG_PATH,
            },
            re.escape('__init__() got an unexpected keyword argument \'auth_type\''),
            id='invalid openstack_config_file',
        ),
    ],
)
def test_config_invalid_openstack_auth(instance, exception_msg, dd_run_check):

    check = OpenStackControllerLegacyCheck(CHECK_NAME, {}, [instance])

    with pytest.raises(Exception, match=exception_msg):
        dd_run_check(check)


@pytest.mark.parametrize(
    'instance, warning_msg',
    [
        pytest.param(
            {'name': 'test'},
            'Either keystone_server_url or openstack_config_file_path need to be provided',
            id='no keystone_server_url, no cfg path',
        ),
        pytest.param(
            {'name': 'test', 'keystone_server_url': 'http://localhost'},
            'Please specify the user via the `user` variable in your init_config.',
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
def test_config_warning(instance, warning_msg, caplog, dd_run_check):
    caplog.set_level(logging.WARN)

    check = OpenStackControllerLegacyCheck(CHECK_NAME, {}, [instance])

    dd_run_check(check)
    assert warning_msg in caplog.text
