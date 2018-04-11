# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import common
import consul_mocks

from datadog_checks.consul import ConsulCheck


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


def test_get_nodes_with_service_warning(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    my_mocks = consul_mocks._get_consul_mocks()
    my_mocks['get_nodes_with_service'] = consul_mocks.mock_get_nodes_with_service_warning
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG)

    aggregator.assert_metric('consul.catalog.nodes_up', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1', 'consul_service-1_service_tag:az-us-east-1a'])
    aggregator.assert_metric('consul.catalog.nodes_passing', value=0, tags=['consul_datacenter:dc1', 'consul_service_id:service-1', 'consul_service-1_service_tag:az-us-east-1a'])
    aggregator.assert_metric('consul.catalog.nodes_warning', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1', 'consul_service-1_service_tag:az-us-east-1a'])
    aggregator.assert_metric('consul.catalog.nodes_critical', value=0, tags=['consul_datacenter:dc1', 'consul_service_id:service-1', 'consul_service-1_service_tag:az-us-east-1a'])
    aggregator.assert_metric('consul.catalog.services_up', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
    aggregator.assert_metric('consul.catalog.services_passing', value=0, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
    aggregator.assert_metric('consul.catalog.services_warning', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
    aggregator.assert_metric('consul.catalog.services_critical', value=0, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])


def test_get_nodes_with_service_critical(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    my_mocks = consul_mocks._get_consul_mocks()
    my_mocks['get_nodes_with_service'] = consul_mocks.mock_get_nodes_with_service_critical
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG)

    aggregator.assert_metric('consul.catalog.nodes_up', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1', 'consul_service-1_service_tag:az-us-east-1a'])
    aggregator.assert_metric('consul.catalog.nodes_passing', value=0, tags=['consul_datacenter:dc1', 'consul_service_id:service-1', 'consul_service-1_service_tag:az-us-east-1a'])
    aggregator.assert_metric('consul.catalog.nodes_warning', value=0, tags=['consul_datacenter:dc1', 'consul_service_id:service-1', 'consul_service-1_service_tag:az-us-east-1a'])
    aggregator.assert_metric('consul.catalog.nodes_critical', value=1, tags=['consul_datacenter:dc1', 'consul_service_id:service-1', 'consul_service-1_service_tag:az-us-east-1a'])
    aggregator.assert_metric('consul.catalog.services_up', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
    aggregator.assert_metric('consul.catalog.services_passing', value=0, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
    aggregator.assert_metric('consul.catalog.services_warning', value=0, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])
    aggregator.assert_metric('consul.catalog.services_critical', value=6, tags=['consul_datacenter:dc1', 'consul_node_id:node-1'])


# def test_service_checks(aggregator):
#     consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
#     my_mocks = consul_mocks._get_consul_mocks()
#     my_mocks['consul_request'] = consul_mocks.mock_get_health_check
#     consul_mocks.mock_check(consul_check, my_mocks)
#     consul_check.check(consul_mocks.MOCK_CONFIG)
#
#     self.run_check(MOCK_CONFIG, mocks=my_mocks)
#     self.assertServiceCheckCritical('consul.check', tags=["consul_datacenter:dc1", "check:server-loadbalancer", "consul_service_id:server-loadbalancer","service:server-loadbalancer"], count=1)
#     self.assertServiceCheckOK('consul.check', tags=["consul_datacenter:dc1", "check:server-api", "consul_service_id:server-loadbalancer","service:server-loadbalancer"], count=1)
#     self.assertServiceCheckOK('consul.check', tags=["consul_datacenter:dc1", "check:server-api", "service:server-loadbalancer"], count=1)
#     self.assertServiceCheckOK('consul.check', tags=["consul_datacenter:dc1", "check:server-api", "consul_service_id:server-loadbalancer"], count=1)
#     self.assertServiceCheck('consul.check', status=AgentCheck.UNKNOWN, tags=["consul_datacenter:dc1", "check:server-status-empty", "consul_service_id:server-empty", "service:server-empty"], count=1)
#     self.assertServiceCheck('consul.check', count=5)


def test_get_peers_in_cluster(aggregator):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, {})
    my_mocks = consul_mocks._get_consul_mocks()
    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG)


    # When node is leader
    aggregator.assert_metric('consul.peers', value=3, tags=['consul_datacenter:dc1', 'mode:leader'])

    my_mocks['_get_cluster_leader'] = consul_mocks.mock_get_cluster_leader_B

    consul_mocks.mock_check(consul_check, my_mocks)
    consul_check.check(consul_mocks.MOCK_CONFIG)
    aggregator.assert_metric('consul.peers', value=3, tags=['consul_datacenter:dc1', 'mode:follower'])


# def test_cull_services_list(aggregator):
#     self.check = load_check(self.CHECK_NAME, MOCK_CONFIG_LEADER_CHECK, self.DEFAULT_AGENT_CONFIG)
#
#     # Pad num_services to kick in truncation logic
#     num_services = self.check.MAX_SERVICES + 20
#
#     # Max services parameter (from consul.yaml) set to be bigger than MAX_SERVICES and smaller than the total of services
#     max_services = num_services - 10
#
#     # Big whitelist
#     services = self.mock_get_n_services_in_cluster(num_services)
#     whitelist = ['service_{0}'.format(k) for k in range(num_services)]
#     self.assertEqual(len(self.check._cull_services_list(services, whitelist)), self.check.MAX_SERVICES)
#
#     # Big whitelist with max_services
#     services = self.mock_get_n_services_in_cluster(num_services)
#     whitelist = ['service_{0}'.format(k) for k in range(num_services)]
#     self.assertEqual(len(self.check._cull_services_list(services, whitelist, max_services)), max_services)
#
#     # Whitelist < MAX_SERVICES should spit out the whitelist
#     services = self.mock_get_n_services_in_cluster(num_services)
#     whitelist = ['service_{0}'.format(k) for k in range(self.check.MAX_SERVICES-1)]
#     self.assertEqual(set(self.check._cull_services_list(services, whitelist)), set(whitelist))
#
#     # Whitelist < max_services param should spit out the whitelist
#     services = self.mock_get_n_services_in_cluster(num_services)
#     whitelist = ['service_{0}'.format(k) for k in range(max_services-1)]
#     self.assertEqual(set(self.check._cull_services_list(services, whitelist, max_services)), set(whitelist))
#
#     # No whitelist, still triggers truncation
#     whitelist = []
#     self.assertEqual(len(self.check._cull_services_list(services, whitelist)), self.check.MAX_SERVICES)
#
#     # No whitelist with max_services set, also triggers truncation
#     whitelist = []
#     self.assertEqual(len(self.check._cull_services_list(services, whitelist, max_services)), max_services)
#
#     # Num. services < MAX_SERVICES should be no-op in absence of whitelist
#     num_services = self.check.MAX_SERVICES - 1
#     services = self.mock_get_n_services_in_cluster(num_services)
#     self.assertEqual(len(self.check._cull_services_list(services, whitelist)), num_services)
#
#     # Num. services < max_services (from consul.yaml) should be no-op in absence of whitelist
#     num_services = max_services - 1
#     services = self.mock_get_n_services_in_cluster(num_services)
#     self.assertEqual(len(self.check._cull_services_list(services, whitelist, max_services)), num_services)
#
#     # Num. services < MAX_SERVICES should spit out only the whitelist when one is defined
#     num_services = self.check.MAX_SERVICES - 1
#     whitelist = ['service_1', 'service_2', 'service_3']
#     services = self.mock_get_n_services_in_cluster(num_services)
#     self.assertEqual(set(self.check._cull_services_list(services, whitelist)), set(whitelist))
#
#     # Num. services < max_services should spit out only the whitelist when one is defined
#     num_services = max_services - 1
#     whitelist = ['service_1', 'service_2', 'service_3']
#     services = self.mock_get_n_services_in_cluster(num_services)
#     self.assertEqual(set(self.check._cull_services_list(services, whitelist, max_services)), set(whitelist))
#
#
# def test_new_leader_event(aggregator):
#     self.check = load_check(self.CHECK_NAME, MOCK_CONFIG_LEADER_CHECK, self.DEFAULT_AGENT_CONFIG)
#     instance_hash = hash_mutable(MOCK_CONFIG_LEADER_CHECK['instances'][0])
#     self.check._instance_states[instance_hash].last_known_leader = 'My Old Leader'
#
#     mocks = self._get_consul_mocks()
#     mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_B
#
#     self.run_check(MOCK_CONFIG_LEADER_CHECK, mocks=mocks)
#     self.assertEqual(len(self.events), 1)
#
#     event = self.events[0]
#     self.assertEqual(event['event_type'], 'consul.new_leader')
#     self.assertIn('prev_consul_leader:My Old Leader', event['tags'])
#     self.assertIn('curr_consul_leader:My New Leader', event['tags'])
#
#
# def test_self_leader_event(aggregator):
#     self.check = load_check(self.CHECK_NAME, MOCK_CONFIG_SELF_LEADER_CHECK, self.DEFAULT_AGENT_CONFIG)
#     instance_hash = hash_mutable(MOCK_CONFIG_SELF_LEADER_CHECK['instances'][0])
#     self.check._instance_states[instance_hash].last_known_leader = 'My Old Leader'
#
#     mocks = self._get_consul_mocks()
#
#     our_url = self.mock_get_cluster_leader_A(None)
#     other_url = self.mock_get_cluster_leader_B(None)
#
#     # We become the leader
#     mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_A
#     self.run_check(MOCK_CONFIG_SELF_LEADER_CHECK, mocks=mocks)
#     self.assertEqual(len(self.events), 1)
#     self.assertEqual(our_url, self.check._instance_states[instance_hash].last_known_leader)
#     event = self.events[0]
#     self.assertEqual(event['event_type'], 'consul.new_leader')
#     self.assertIn('prev_consul_leader:My Old Leader', event['tags'])
#     self.assertIn('curr_consul_leader:%s' % our_url, event['tags'])
#
#     # We are already the leader, no new events
#     self.run_check(MOCK_CONFIG_SELF_LEADER_CHECK, mocks=mocks)
#     self.assertEqual(len(self.events), 0)
#
#     # We lose the leader, no new events
#     mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_B
#     self.run_check(MOCK_CONFIG_SELF_LEADER_CHECK, mocks=mocks)
#     self.assertEqual(len(self.events), 0)
#     self.assertEqual(other_url, self.check._instance_states[instance_hash].last_known_leader)
#
#     # We regain the leadership
#     mocks['_get_cluster_leader'] = self.mock_get_cluster_leader_A
#     self.run_check(MOCK_CONFIG_SELF_LEADER_CHECK, mocks=mocks)
#     self.assertEqual(len(self.events), 1)
#     self.assertEqual(our_url, self.check._instance_states[instance_hash].last_known_leader)
#     event = self.events[0]
#     self.assertEqual(event['event_type'], 'consul.new_leader')
#     self.assertIn('prev_consul_leader:%s' % other_url, event['tags'])
#     self.assertIn('curr_consul_leader:%s' % our_url, event['tags'])
#
#
# def test_network_latency_checks(aggregator):
#     self.check = load_check(self.CHECK_NAME, MOCK_CONFIG_NETWORK_LATENCY_CHECKS,
#                             self.DEFAULT_AGENT_CONFIG)
#
#     mocks = self._get_consul_mocks()
#
#     # We start out as the leader, and stay that way
#     instance_hash = hash_mutable(MOCK_CONFIG_NETWORK_LATENCY_CHECKS['instances'][0])
#     self.check._instance_states[instance_hash].last_known_leader = self.mock_get_cluster_leader_A(None)
#
#     self.run_check(MOCK_CONFIG_NETWORK_LATENCY_CHECKS, mocks=mocks)
#
#     latency = [m for m in self.metrics if m[0].startswith('consul.net.')]
#     latency.sort()
#     # Make sure we have the expected number of metrics
#     self.assertEquals(19, len(latency))
#
#     # Only 3 dc-latency metrics since we only do source = self
#     dc = [m for m in latency if '.dc.latency.' in m[0]]
#     self.assertEquals(3, len(dc))
#     self.assertEquals(1.6746410750238774, dc[0][2])
#
#     # 16 latency metrics, 2 nodes * 8 metrics each
#     node = [m for m in latency if '.node.latency.' in m[0]]
#     self.assertEquals(16, len(node))
#     self.assertEquals(0.26577747932995816, node[0][2])
