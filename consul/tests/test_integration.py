# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from requests import HTTPError

from datadog_checks.consul import ConsulCheck

from . import common

METRICS = [
    'consul.catalog.nodes_up',
    'consul.catalog.nodes_passing',
    'consul.catalog.nodes_warning',
    'consul.catalog.nodes_critical',
    'consul.catalog.services_up',
    'consul.catalog.services_passing',
    'consul.catalog.services_warning',
    'consul.catalog.services_critical',
    'consul.catalog.total_nodes',
    # Enable again when it's figured out why only followers submit these
    # 'consul.net.node.latency.p95',
    # 'consul.net.node.latency.min',
    # 'consul.net.node.latency.p25',
    # 'consul.net.node.latency.median',
    # 'consul.net.node.latency.max',
    # 'consul.net.node.latency.p99',
    # 'consul.net.node.latency.p90',
    # 'consul.net.node.latency.p75'
]


@pytest.mark.integration
def test_check(aggregator, instance, dd_environment):
    """
    Testing Consul Integration
    """
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    consul_check.check(instance)

    for m in METRICS:
        aggregator.assert_metric(m, at_least=0)

    aggregator.assert_metric('consul.peers', value=3)

    aggregator.assert_service_check('consul.check')
    aggregator.assert_service_check('consul.up', tags=['consul_datacenter:dc1', 'consul_url:{}'.format(common.URL)])


@pytest.mark.integration
def test_single_node_install(aggregator, instance_single_node_install, dd_environment):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    consul_check.check(instance_single_node_install)

    for m in METRICS:
        aggregator.assert_metric(m, at_least=1)

    aggregator.assert_metric('consul.peers', value=3)

    aggregator.assert_service_check('consul.check')
    aggregator.assert_service_check('consul.up', tags=['consul_datacenter:dc1', 'consul_url:{}'.format(common.URL)])


@pytest.mark.integration
def test_acl_forbidden(instance_bad_token, dd_environment):
    """
    Testing Consul Integration with wrong ACL token
    """
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})

    got_error_403 = False
    try:
        consul_check.check(instance_bad_token)
    except HTTPError as e:
        if e.response.status_code == 403:
            got_error_403 = True

    assert got_error_403
