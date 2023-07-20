# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.openstack_controller import OpenStackControllerCheck

pytestmark = [pytest.mark.integration]


@pytest.mark.usefixtures('dd_environment')
def test_connect_exception(aggregator, dd_run_check, caplog):
    instance = {
        'keystone_server_url': 'http://10.0.0.0/identity',
        'username': 'admin',
        'password': 'password',
    }
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Exception while reporting identity response time' in caplog.text


@pytest.mark.usefixtures('dd_environment')
def test_connect_http_error(aggregator, dd_run_check, caplog):
    instance = {
        'keystone_server_url': 'http://127.0.0.1:8080/identity',
        'username': 'xxxx',
        'password': 'xxxx',
    }
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('openstack.keystone.api.up', status=check.CRITICAL)
    assert 'HTTPError while reporting identity response time' in caplog.text
