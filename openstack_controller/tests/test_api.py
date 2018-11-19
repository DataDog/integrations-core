# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock

from datadog_checks.openstack_controller.api import ComputeApi


def get_os_hypervisor_uptime_response(self, query_params, timeout=None):
    return {
        "hypervisor": {
            "hypervisor_hostname": "fake-mini",
            "id": 1,
            "state": "up",
            "status": "enabled",
            "uptime": " 08:32:11 up 93 days, 18:25, 12 users,  load average: 0.20, 0.12, 0.14"
        }
    }


def get_os_hypervisor_uptime_v2_53_response(self, query_params, timeout=None):
    return {
        "hypervisor": {
            "hypervisor_hostname": "fake-mini",
            "id": "b1e43b5f-eec1-44e0-9f10-7b4945c0226d",
            "state": "up",
            "status": "enabled",
            "uptime": " 08:32:11 up 93 days, 18:25, 12 users,  load average: 0.20, 0.12, 0.14"
        }
    }


def test_get_os_hypervisor_uptime():
    with mock.patch('datadog_checks.openstack_controller.api.AbstractApi._make_request',
                    side_effect=get_os_hypervisor_uptime_response):
        compute_api = ComputeApi(None, False, None, "foo", "foo")
        assert compute_api.get_os_hypervisor_uptime(1) == \
            " 08:32:11 up 93 days, 18:25, 12 users,  load average: 0.20, 0.12, 0.14"

    with mock.patch('datadog_checks.openstack_controller.api.AbstractApi._make_request',
                    side_effect=get_os_hypervisor_uptime_v2_53_response):
        compute_api = ComputeApi(None, False, None, "foo", "foo")
        assert compute_api.get_os_hypervisor_uptime(1) == \
            " 08:32:11 up 93 days, 18:25, 12 users,  load average: 0.20, 0.12, 0.14"
