# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import os
import tempfile

import pytest

from datadog_checks.base import AgentCheck

# from . import common


@pytest.mark.e2e
def test_connect_ok(dd_agent_check):
    aggregator = dd_agent_check()
    # assert default metrics
    # for metric in common.DEFAULT_METRICS:
    #     aggregator.assert_metric(metric)
    # aggregator.assert_all_metrics_covered()
    # assert service checks
    aggregator.assert_service_check('openstack.keystone.api.up', status=AgentCheck.OK)
    # aggregator.assert_service_check('openstack.nova.api.up', status=AgentCheck.OK)
    # aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.OK)
    # aggregator.assert_service_check('openstack.ironic.api.up', status=AgentCheck.OK)
    # aggregator.assert_service_check('openstack.octavia.api.up', status=AgentCheck.OK)


@pytest.mark.e2e
def test_connect_with_invalid_user(dd_agent_check):
    config_file = os.path.join(tempfile.gettempdir(), 'openstack_controller_instance.json')
    with open(config_file, 'rb') as f:
        instance = json.load(f)
    instance['user_name'] = 'xxxx'
    aggregator = dd_agent_check(instance)
    aggregator.assert_service_check('openstack.keystone.api.up', status=AgentCheck.CRITICAL)
    aggregator.assert_service_check('openstack.nova.api.up', status=AgentCheck.UNKNOWN)
    aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.UNKNOWN)
    aggregator.assert_service_check('openstack.ironic.api.up', status=AgentCheck.UNKNOWN)
    aggregator.assert_service_check('openstack.octavia.api.up', status=AgentCheck.UNKNOWN)
