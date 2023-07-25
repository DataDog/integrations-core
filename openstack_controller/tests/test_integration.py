# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.ci import running_on_ci
from datadog_checks.openstack_controller import OpenStackControllerCheck

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(running_on_ci(), reason='Test is failing on CI'),
    pytest.mark.usefixtures('dd_environment'),
]


def test_connect_exception(aggregator, dd_run_check, caplog):
    instance = {
        'keystone_server_url': 'http://10.0.0.0/identity',
        'username': 'admin',
        'password': 'password',
    }
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Exception while reporting identity response time' in caplog.text


def test_connect_ok(aggregator, dd_run_check, caplog):
    instance = {
        'keystone_server_url': 'http://127.0.0.1:8080/identity',
        'username': 'admin',
        'password': 'password',
    }
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('openstack.keystone.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.nova.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.ironic.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.octavia.api.up', status=AgentCheck.OK)
