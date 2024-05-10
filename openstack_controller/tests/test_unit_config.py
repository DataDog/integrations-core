# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import re

import pytest

import tests.configs as configs
from datadog_checks.openstack_controller import OpenStackControllerCheck

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(os.environ.get('OPENSTACK_E2E_LEGACY') == 'true', reason='Not Legacy test'),
]


@pytest.mark.parametrize(
    'instance, exception_msg',
    [
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'openstack_cloud_name': 'test',
                'openstack_config_file_path': configs.TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
                'use_legacy_check_version': False,
            },
            'Cloud test was not found.',
            id='bad openstack_cloud_name',
        ),
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'openstack_config_file_path': 'test',
                'use_legacy_check_version': False,
            },
            'Auth plugin requires parameters which were not given: auth_url',
            id='openstack_config_file_path doesn\' exist',
        ),
        pytest.param(
            {
                'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
                'openstack_cloud_name': 'test_cloud',
                'openstack_config_file_path': configs.TEST_OPENSTACK_BAD_CONFIG_PATH,
                'use_legacy_check_version': False,
            },
            re.escape('__init__() got an unexpected keyword argument \'auth_type\''),
            id='invalid openstack_config_file',
        ),
        pytest.param(
            {
                'use_legacy_check_version': False,
            },
            'Either keystone_server_url or openstack_config_file_path need to be provided.',
            id='no keystone_server_url, no cfg path',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'use_legacy_check_version': False,
            },
            'Please specify `username` in your config.',
            id='no username',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'username': 'admin',
                'use_legacy_check_version': False,
            },
            'Please specify `password` in your config.',
            id='no password',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {},
                'use_legacy_check_version': False,
            },
            'The user should look like: '
            '{"name": "my_name", "password": "my_password", "domain": {"id": "my_domain_id"}}',
            id='no name in user (legacy config)',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name'},
                'use_legacy_check_version': False,
            },
            'The user should look like: '
            '{"name": "my_name", "password": "my_password", "domain": {"id": "my_domain_id"}}',
            id='no password in user (legacy config)',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name', 'password': 'my_password'},
                'use_legacy_check_version': False,
            },
            'The user should look like: '
            '{"name": "my_name", "password": "my_password", "domain": {"id": "my_domain_id"}}',
            id='no domain in user (legacy config)',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name', 'password': 'my_password', 'domain': {'id': 'my_domain_id'}},
                'nova_microversion': 'test',
                'use_legacy_check_version': False,
            },
            'Invalid `nova_microversion`: test; please specify a valid version',
            id='invalid nova_microversion',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name', 'password': 'my_password', 'domain': {'id': 'my_domain_id'}},
                'ironic_microversion': 'tests',
                'use_legacy_check_version': False,
            },
            'Invalid `ironic_microversion`: tests; please specify a valid version',
            id='invalid ironic_microversion',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name', 'password': 'my_password', 'domain': {'id': 'my_domain_id'}},
                'cinder_microversion': 'tests',
                'use_legacy_check_version': False,
            },
            'Invalid `cinder_microversion`: tests; please specify a valid version',
            id='invalid cinder_microversion',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name', 'password': 'my_password', 'domain': {'id': 'my_domain_id'}},
                'ironic_microversion': 'tests',
                'nova_microversion': 'tests',
                'use_legacy_check_version': False,
            },
            'Invalid `nova_microversion`: tests; please specify a valid version',
            id='invalid nova_microversion and ironic_microversion',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name', 'password': 'my_password', 'domain': {}},
                'use_legacy_check_version': False,
            },
            'The user should look like: '
            '{"name": "my_name", "password": "my_password", "domain": {"id": "my_domain_id"}}',
            id='no domain id in user (legacy config)',
        ),
    ],
)
def test_config_exceptions(check, dd_run_check, exception_msg):
    with pytest.raises(Exception, match=exception_msg):
        dd_run_check(check)


@pytest.mark.parametrize(
    'instance, warning_msg',
    [
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name', 'password': 'my_password', 'domain': {'id': 'my_domain_id'}},
                'ironic_microversion': 'latest',
                'use_legacy_check_version': False,
            },
            'Setting `ironic_microversion` to `latest` is not recommended',
            id='latest ironic_microversion',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name', 'password': 'my_password', 'domain': {'id': 'my_domain_id'}},
                'ironic_microversion': 'LATEST',
                'use_legacy_check_version': False,
            },
            'Setting `ironic_microversion` to `latest` is not recommended',
            id='capital latest ironic_microversion',
        ),
        pytest.param(
            {
                'keystone_server_url': 'http://localhost',
                'user': {'name': 'my_name', 'password': 'my_password', 'domain': {'id': 'my_domain_id'}},
                'nova_microversion': 'LATEST',
                'use_legacy_check_version': False,
            },
            'Setting `nova_microversion` to `latest` is not recommended',
            id='capital latest nova_microversion',
        ),
    ],
)
def test_config_warnings(check, dd_run_check, caplog, warning_msg):
    with caplog.at_level(logging.DEBUG):
        dd_run_check(check)
    assert warning_msg in caplog.text


def test_legacy_config_ok():
    instance = {
        'keystone_server_url': 'http://localhost',
        'user': {'name': 'my_name', 'password': 'my_password', 'domain': {'id': 'default'}},
        'use_legacy_check_version': False,
    }
    OpenStackControllerCheck('test', {}, [instance])


def test_config_ok():
    instance = {
        'keystone_server_url': 'http://localhost',
        'username': 'my_name',
        'password': 'my_password',
        'domain_id': 'default',
    }
    OpenStackControllerCheck('test', {}, [instance])
