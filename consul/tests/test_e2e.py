# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.consul import ConsulCheck

from . import common

pytestmark = pytest.mark.e2e


def test_e2e(dd_agent_check, instance_single_node_install):
    aggregator = dd_agent_check(instance_single_node_install, rate=True)

    aggregator.assert_metric('consul.peers', count=2)
    aggregator.assert_metric('consul.catalog.nodes_critical', count=2)
    aggregator.assert_metric('consul.catalog.services_passing', count=6)
    aggregator.assert_metric('consul.catalog.nodes_warning', count=2)
    aggregator.assert_metric('consul.catalog.services_warning', count=6)
    aggregator.assert_metric('consul.catalog.services_critical', count=6)
    aggregator.assert_metric('consul.catalog.services_up', count=6)
    aggregator.assert_metric('consul.catalog.nodes_passing', count=2)
    aggregator.assert_metric('consul.catalog.nodes_up', count=2)
    aggregator.assert_metric('consul.catalog.total_nodes', count=2)
    aggregator.assert_metric('consul.catalog.services_count', count=6)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'consul.up', ConsulCheck.OK, tags=['consul_datacenter:dc1', 'consul_url:http://{}:8500'.format(common.HOST)]
    )
    aggregator.assert_service_check('consul.check', ConsulCheck.OK, tags=['check:serfHealth', 'consul_datacenter:dc1'])
    aggregator.assert_service_check(
        'consul.can_connect', ConsulCheck.OK, tags=['url:http://{}:8500/v1/status/leader'.format(common.HOST)]
    )
    aggregator.assert_service_check(
        'consul.can_connect', ConsulCheck.OK, tags=['url:http://{}:8500/v1/status/peers'.format(common.HOST)]
    )
    aggregator.assert_service_check(
        'consul.can_connect', ConsulCheck.OK, tags=['url:http://{}:8500/v1/agent/self'.format(common.HOST)]
    )
    aggregator.assert_service_check(
        'consul.can_connect', ConsulCheck.OK, tags=['url:http://{}:8500/v1/health/state/any'.format(common.HOST)]
    )
    aggregator.assert_service_check(
        'consul.can_connect', ConsulCheck.OK, tags=['url:http://{}:8500/v1/catalog/services'.format(common.HOST)]
    )
    aggregator.assert_service_check(
        'consul.can_connect', ConsulCheck.OK, tags=['url:http://{}:8500/v1/catalog/nodes'.format(common.HOST)]
    )
    aggregator.assert_service_check(
        'consul.can_connect', ConsulCheck.OK, tags=['url:http://{}:8500/v1/coordinate/datacenters'.format(common.HOST)]
    )
    aggregator.assert_service_check(
        'consul.can_connect', ConsulCheck.OK, tags=['url:http://{}:8500/v1/coordinate/nodes'.format(common.HOST)]
    )
