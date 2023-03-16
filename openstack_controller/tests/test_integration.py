# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from requests.exceptions import HTTPError

from datadog_checks.openstack_controller import OpenStackControllerCheck

pytestmark = [pytest.mark.integration]


@pytest.mark.usefixtures('dd_environment')
def test_connect_exception(aggregator, dd_run_check):
    instance = {
        'keystone_server_url': 'http://10.0.0.0/identity',
        'user_name': 'admin',
        'user_password': 'password',
    }
    with pytest.raises(Exception):
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
    aggregator.assert_service_check('openstack.keystone.api.up', status=check.CRITICAL)


@pytest.mark.usefixtures('dd_environment')
def test_connect_http_error(aggregator, dd_run_check):
    with pytest.raises(HTTPError):
        instance = {
            'keystone_server_url': 'http://127.0.0.1:8080/identity',
            'user_name': 'xxxx',
            'user_password': 'xxxx',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('openstack.keystone.api.up', status=check.CRITICAL)
