# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

import common
from datadog_checks.consul import ConsulCheck
from requests import HTTPError

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
    'consul.net.node.latency.p95',
    'consul.net.node.latency.min',
    'consul.net.node.latency.p25',
    'consul.net.node.latency.median',
    'consul.net.node.latency.max',
    'consul.net.node.latency.max',
    'consul.net.node.latency.p99',
    'consul.net.node.latency.p90',
    'consul.net.node.latency.p75'
]

CONFIG_INTEGRATION = {
    'url': common.URL,
    'catalog_checks': True,
    'network_latency_checks': True,
    'new_leader_checks': True,
    'catalog_checks': True,
    'self_leader_check': True,
    'acl_token': 'token'
}

CONFIG_INTEGRATION_WRONG_TOKEN = {
    'url': common.URL,
    'catalog_checks': True,
    'network_latency_checks': True,
    'new_leader_checks': True,
    'catalog_checks': True,
    'self_leader_check': True,
    'acl_token': 'wrong_token'
}


@pytest.mark.integration
def test_integration(aggregator, consul_cluster):
    """
    Testing Consul Integration
    """

    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    consul_check.check(CONFIG_INTEGRATION)

    for m in METRICS:
        aggregator.assert_metric(m, at_least=0)

    aggregator.assert_metric('consul.peers', value=3)

    aggregator.assert_service_check('consul.check')
    aggregator.assert_service_check('consul.up', tags=[
        'consul_datacenter:dc1',
        'consul_url:{}'.format(common.URL)
    ])


@pytest.mark.integration
def test_acl_forbidden(aggregator, consul_cluster):
    """
    Testing Consul Integration with wrong ACL token
    """

    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})

    got_error_403 = False
    try:
        consul_check.check(CONFIG_INTEGRATION_WRONG_TOKEN)
    except HTTPError as e:
        if e.response.status_code == 403:
            got_error_403 = True

    assert got_error_403
