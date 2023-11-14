# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.base import AgentCheck

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures('dd_environment'),
    pytest.mark.skipif(os.environ.get('OPENSTACK_E2E_LEGACY') == 'true', reason='Not Legacy test'),
    pytest.mark.skipif(os.environ.get('USE_OPENSTACK_GCP') == 'true', reason='Not GCP test'),
]


def test_connect_exception(openstack_controller_check, dd_run_check, caplog):
    instance = {
        'keystone_server_url': 'http://10.0.0.0/identity',
        'username': 'admin',
        'password': 'password',
        'use_legacy_check_version': False,
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    assert 'Error while authorizing user' in caplog.text


def test_connect_ok(aggregator, openstack_controller_check, dd_run_check):
    instance = {
        'keystone_server_url': 'http://127.0.0.1:8080/identity',
        'username': 'admin',
        'password': 'password',
        'use_legacy_check_version': False,
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    aggregator.assert_service_check('openstack.keystone.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.nova.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.ironic.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.octavia.api.up', status=AgentCheck.OK)
