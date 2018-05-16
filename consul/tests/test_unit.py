# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging

import common
import consul_mocks

from datadog_checks.consul import ConsulCheck
from datadog_checks.utils.containers import hash_mutable

log = logging.getLogger(__file__)


def test_get_nodes_with_service(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    consul_mocks.mock_check(consul_check, consul_mocks._get_consul_mocks())
    consul_check.check(consul_mocks.MOCK_CONFIG)

    expected_tags = ['consul_datacenter:dc1',
                     'consul_service_id:service-1',
                     'consul_service-1_service_tag:az-us-east-1a']

    aggregator.assert_metric('consul.catalog.nodes_up', value=1, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.nodes_passing', value=1, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.nodes_warning', value=0, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.nodes_critical', value=0, tags=expected_tags)

    expected_tags = ['consul_datacenter:dc1', 'consul_node_id:node-1']

    aggregator.assert_metric('consul.catalog.services_up', value=6, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.services_passing', value=6, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.services_warning', value=0, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.services_critical', value=0, tags=expected_tags)


def test_get_peers_in_cluster(aggregator):
    my_mocks = consul_mocks._get_consul_mocks()
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG)

    # When node is leader
    aggregator.assert_metric('consul.peers', value=3, tags=['consul_datacenter:dc1', 'mode:leader'])

    my_mocks['_get_cluster_leader'] = consul_mocks.mock_get_cluster_leader_B
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG)

    aggregator.assert_metric('consul.peers', value=3, tags=['consul_datacenter:dc1', 'mode:follower'])


def test_count_all_nodes(aggregator):
    my_mocks = consul_mocks._get_consul_mocks()
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG)

    aggregator.assert_metric('consul.catalog.total_nodes', value=2, tags=['consul_datacenter:dc1'])


def test_get_nodes_with_service_warning(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    my_mocks = consul_mocks._get_consul_mocks()
    my_mocks['get_nodes_with_service'] = consul_mocks.mock_get_nodes_with_service_warning
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG)

    expected_tags = [
        'consul_datacenter:dc1',
        'consul_service_id:service-1',
        'consul_service-1_service_tag:az-us-east-1a'
    ]
    aggregator.assert_metric('consul.catalog.nodes_up', value=1, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.nodes_passing', value=0, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.nodes_warning', value=1, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.nodes_critical', value=0, tags=expected_tags)

    expected_tags = [
        'consul_datacenter:dc1',
        'consul_node_id:node-1'
    ]
    aggregator.assert_metric('consul.catalog.services_up', value=6, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.services_passing', value=0, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.services_warning', value=6, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.services_critical', value=0, tags=expected_tags)


def test_get_nodes_with_service_critical(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    my_mocks = consul_mocks._get_consul_mocks()
    my_mocks['get_nodes_with_service'] = consul_mocks.mock_get_nodes_with_service_critical
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG)

    expected_tags = [
        'consul_datacenter:dc1',
        'consul_service_id:service-1',
        'consul_service-1_service_tag:az-us-east-1a'
    ]
    aggregator.assert_metric('consul.catalog.nodes_up', value=1, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.nodes_passing', value=0, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.nodes_warning', value=0, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.nodes_critical', value=1, tags=expected_tags)

    expected_tags = [
        'consul_datacenter:dc1',
        'consul_node_id:node-1'
    ]
    aggregator.assert_metric('consul.catalog.services_up', value=6, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.services_passing', value=0, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.services_warning', value=0, tags=expected_tags)
    aggregator.assert_metric('consul.catalog.services_critical', value=6, tags=expected_tags)


def test_service_checks(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    my_mocks = consul_mocks._get_consul_mocks()
    my_mocks['consul_request'] = consul_mocks.mock_get_health_check
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG)

    expected_tags = [
        "consul_datacenter:dc1",
        "check:server-loadbalancer",
        "consul_service_id:server-loadbalancer",
        "service:server-loadbalancer"
    ]
    aggregator.assert_service_check('consul.check', status=ConsulCheck.CRITICAL, tags=expected_tags, count=1)

    expected_tags = [
        "consul_datacenter:dc1",
        "check:server-api",
        "consul_service_id:server-loadbalancer",
        "service:server-loadbalancer"
    ]
    aggregator.assert_service_check('consul.check', status=ConsulCheck.OK, tags=expected_tags, count=1)

    expected_tags = [
        "consul_datacenter:dc1",
        "check:server-api",
        "service:server-loadbalancer"
    ]
    aggregator.assert_service_check('consul.check', status=ConsulCheck.OK, tags=expected_tags, count=1)

    expected_tags = [
        "consul_datacenter:dc1",
        "check:server-api",
        "consul_service_id:server-loadbalancer"
    ]
    aggregator.assert_service_check('consul.check', status=ConsulCheck.OK, tags=expected_tags, count=1)

    expected_tags = [
        "consul_datacenter:dc1",
        "check:server-status-empty",
        "consul_service_id:server-empty",
        "service:server-empty"
    ]
    aggregator.assert_service_check('consul.check', status=ConsulCheck.UNKNOWN, tags=expected_tags, count=1)

    aggregator.assert_service_check('consul.check', count=5)


def test_cull_services_list(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    my_mocks = consul_mocks._get_consul_mocks()
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG_LEADER_CHECK)

    # Pad num_services to kick in truncation logic
    num_services = consul_check.MAX_SERVICES + 20

    # Max services parameter (from consul.yaml) set to be bigger than MAX_SERVICES and smaller than total of services
    max_services = num_services - 10

    # Big whitelist
    services = consul_mocks.mock_get_n_services_in_cluster(num_services)
    whitelist = ['service_{0}'.format(k) for k in range(num_services)]
    assert len(consul_check._cull_services_list(services, whitelist)) == consul_check.MAX_SERVICES

    # Big whitelist with max_services
    assert len(consul_check._cull_services_list(services, whitelist, max_services)) == max_services

    # Whitelist < MAX_SERVICES should spit out the whitelist
    whitelist = ['service_{0}'.format(k) for k in range(consul_check.MAX_SERVICES - 1)]
    assert set(consul_check._cull_services_list(services, whitelist)) == set(whitelist)

    # Whitelist < max_services param should spit out the whitelist
    whitelist = ['service_{0}'.format(k) for k in range(max_services - 1)]
    assert set(consul_check._cull_services_list(services, whitelist, max_services)) == set(whitelist)

    # No whitelist, still triggers truncation
    whitelist = []
    assert len(consul_check._cull_services_list(services, whitelist)) == consul_check.MAX_SERVICES

    # No whitelist with max_services set, also triggers truncation
    whitelist = []
    assert len(consul_check._cull_services_list(services, whitelist, max_services)) == max_services

    # Num. services < MAX_SERVICES should be no-op in absence of whitelist
    num_services = consul_check.MAX_SERVICES - 1
    services = consul_mocks.mock_get_n_services_in_cluster(num_services)
    assert len(consul_check._cull_services_list(services, whitelist)) == num_services

    # Num. services < MAX_SERVICES should spit out only the whitelist when one is defined
    whitelist = ['service_1', 'service_2', 'service_3']
    assert set(consul_check._cull_services_list(services, whitelist)) == set(whitelist)

    # Num. services < max_services (from consul.yaml) should be no-op in absence of whitelist
    num_services = max_services - 1
    whitelist = []
    services = consul_mocks.mock_get_n_services_in_cluster(num_services)
    assert len(consul_check._cull_services_list(services, whitelist, max_services)) == num_services

    # Num. services < max_services should spit out only the whitelist when one is defined
    whitelist = ['service_1', 'service_2', 'service_3']
    assert set(consul_check._cull_services_list(services, whitelist, max_services)) == set(whitelist)


def test_new_leader_event(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    my_mocks = consul_mocks._get_consul_mocks()
    my_mocks['_get_cluster_leader'] = consul_mocks.mock_get_cluster_leader_B
    consul_mocks.mock_check(consul_check, my_mocks)

    instance_hash = hash_mutable(consul_mocks.MOCK_CONFIG_LEADER_CHECK)
    consul_check._instance_states[instance_hash].last_known_leader = 'My Old Leader'

    consul_check.check(consul_mocks.MOCK_CONFIG_LEADER_CHECK)
    assert len(aggregator.events) == 1

    event = aggregator.events[0]
    assert event['event_type'] == 'consul.new_leader'
    assert 'prev_consul_leader:My Old Leader' in event['tags']
    assert 'curr_consul_leader:My New Leader' in event['tags']


def test_self_leader_event(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    my_mocks = consul_mocks._get_consul_mocks()

    instance_hash = hash_mutable(consul_mocks.MOCK_CONFIG_SELF_LEADER_CHECK)
    consul_check._instance_states[instance_hash].last_known_leader = 'My Old Leader'

    our_url = consul_mocks.mock_get_cluster_leader_A(None)
    other_url = consul_mocks.mock_get_cluster_leader_B(None)

    # We become the leader
    my_mocks['_get_cluster_leader'] = consul_mocks.mock_get_cluster_leader_A
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG_SELF_LEADER_CHECK)
    assert len(aggregator.events) == 1
    assert our_url == consul_check._instance_states[instance_hash].last_known_leader
    event = aggregator.events[0]
    assert event['event_type'] == 'consul.new_leader'
    assert 'prev_consul_leader:My Old Leader' in event['tags']
    assert 'curr_consul_leader:{}'.format(our_url) in event['tags']

    # We are already the leader, no new events
    aggregator.reset()
    consul_check.check(consul_mocks.MOCK_CONFIG_SELF_LEADER_CHECK)
    assert len(aggregator.events) == 0

    # We lose the leader, no new events
    my_mocks['_get_cluster_leader'] = consul_mocks.mock_get_cluster_leader_B
    consul_mocks.mock_check(consul_check, my_mocks)
    aggregator.reset()
    consul_check.check(consul_mocks.MOCK_CONFIG_SELF_LEADER_CHECK)
    assert len(aggregator.events) == 0
    assert other_url == consul_check._instance_states[instance_hash].last_known_leader

    # We regain the leadership
    my_mocks['_get_cluster_leader'] = consul_mocks.mock_get_cluster_leader_A
    consul_mocks.mock_check(consul_check, my_mocks)
    aggregator.reset()
    consul_check.check(consul_mocks.MOCK_CONFIG_SELF_LEADER_CHECK)
    assert len(aggregator.events) == 1
    assert our_url == consul_check._instance_states[instance_hash].last_known_leader
    event = aggregator.events[0]
    assert event['event_type'] == 'consul.new_leader'
    assert 'prev_consul_leader:{}'.format(other_url) in event['tags']
    assert 'curr_consul_leader:{}'.format(our_url) in event['tags']


def test_network_latency_checks(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    my_mocks = consul_mocks._get_consul_mocks()
    consul_mocks.mock_check(consul_check, my_mocks)

    # We start out as the leader, and stay that way
    instance_hash = hash_mutable(consul_mocks.MOCK_CONFIG_NETWORK_LATENCY_CHECKS)
    consul_check._instance_states[instance_hash].last_known_leader = consul_mocks.mock_get_cluster_leader_A(None)

    consul_check.check(consul_mocks.MOCK_CONFIG_NETWORK_LATENCY_CHECKS)

    latency = []
    for m_name, metrics in aggregator._metrics.items():
        if m_name.startswith('consul.net.'):
            latency.extend(metrics)
    latency.sort()
    # Make sure we have the expected number of metrics
    assert 19 == len(latency)

    # Only 3 dc-latency metrics since we only do source = self
    dc = [m for m in latency if '.dc.latency.' in m[0]]
    assert 3 == len(dc)
    assert 1.6746410750238774 == dc[0][2]

    # 16 latency metrics, 2 nodes * 8 metrics each
    node = [m for m in latency if '.node.latency.' in m[0]]
    assert 16 == len(node)
    assert 0.26577747932995816 == node[0][2]
