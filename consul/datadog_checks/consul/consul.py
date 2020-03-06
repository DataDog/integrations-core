# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from collections import defaultdict
from datetime import datetime, timedelta
from itertools import islice
from time import time as timestamp

import requests
from six import iteritems, iterkeys, itervalues
from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.consul.common import (
    CONSUL_CAN_CONNECT,
    CONSUL_CATALOG_CHECK,
    CONSUL_CHECK,
    HEALTH_CHECK,
    MAX_CONFIG_TTL,
    MAX_SERVICES,
    SOURCE_TYPE_NAME,
    STATUS_SC,
    STATUS_SEVERITY,
    ceili,
    distance,
)


class ConsulCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(ConsulCheck, self).__init__(name, init_config, instances)

        self.url = self.instance.get('url')
        self.base_tags = self.instance.get('tags', [])

        self.single_node_install = is_affirmative(self.instance.get('single_node_install', False))
        self.perform_new_leader_checks = is_affirmative(
            self.instance.get('new_leader_checks', self.init_config.get('new_leader_checks', False))
        )
        self.perform_self_leader_check = is_affirmative(
            self.instance.get('self_leader_check', self.init_config.get('self_leader_check', False))
        )
        self.perform_catalog_checks = is_affirmative(
            self.instance.get('catalog_checks', self.init_config.get('catalog_checks'))
        )
        self.perform_network_latency_checks = is_affirmative(
            self.instance.get('network_latency_checks', self.init_config.get('network_latency_checks'))
        )
        self.disable_legacy_service_tag = is_affirmative(self.instance.get('disable_legacy_service_tag', False))
        self.service_whitelist = self.instance.get('service_whitelist', self.init_config.get('service_whitelist', []))
        self.max_services = self.instance.get('max_services', self.init_config.get('max_services', MAX_SERVICES))

        self._local_config = None
        self._last_config_fetch_time = None
        self._last_known_leader = None

        self.HTTP_CONFIG_REMAPPER = {
            'client_cert_file': {'name': 'tls_cert'},
            'private_key_file': {'name': 'tls_private_key'},
            'ca_bundle_file': {'name': 'tls_ca_cert'},
        }

        if 'acl_token' in self.instance:
            self.http.options['headers']['X-Consul-Token'] = self.instance['acl_token']

    def consul_request(self, endpoint):
        url = urljoin(self.url, endpoint)
        service_check_tags = ["url:{}".format(url)] + self.base_tags
        try:
            resp = self.http.get(url)

            resp.raise_for_status()

        except requests.exceptions.Timeout as e:
            msg = 'Consul request to {} timed out'.format(url)
            self.log.exception(msg)
            self.service_check(
                CONSUL_CAN_CONNECT, self.CRITICAL, tags=service_check_tags, message="{}: {}".format(msg, e)
            )
            raise
        except Exception as e:
            msg = "Consul request to {} failed".format(url)
            self.log.exception(msg)
            self.service_check(
                CONSUL_CAN_CONNECT, self.CRITICAL, tags=service_check_tags, message="{}: {}".format(msg, e)
            )
            raise
        else:
            self.service_check(CONSUL_CAN_CONNECT, self.OK, tags=service_check_tags)

        return resp.json()

    # Consul Config Accessors
    def _get_local_config(self):
        time_window = 0
        if self._last_config_fetch_time:
            time_window = datetime.utcnow() - self._last_config_fetch_time
        if not self._local_config or time_window > timedelta(seconds=MAX_CONFIG_TTL):
            self._local_config = self.consul_request('/v1/agent/self')
            self._last_config_fetch_time = datetime.utcnow()

        return self._local_config

    def _get_cluster_leader(self):
        return self.consul_request('/v1/status/leader')

    def _get_agent_url(self):
        self.log.debug("Starting _get_agent_url")
        local_config = self._get_local_config()

        # Member key for consul 0.7.x and up; Config key for older versions
        agent_addr = local_config.get('Member', {}).get('Addr') or local_config.get('Config', {}).get('AdvertiseAddr')
        agent_port = local_config.get('Member', {}).get('Tags', {}).get('port') or local_config.get('Config', {}).get(
            'Ports', {}
        ).get('Server')

        agent_url = "{}:{}".format(agent_addr, agent_port)
        self.log.debug("Agent url is %s", agent_url)
        return agent_url

    def _get_agent_datacenter(self):
        local_config = self._get_local_config()
        agent_dc = local_config.get('Config', {}).get('Datacenter')
        return agent_dc

    # Consul Leader Checks
    def _is_instance_leader(self):
        try:
            agent_url = self._get_agent_url()
            leader = self._last_known_leader or self._get_cluster_leader()
            self.log.debug("Consul agent lives at %s . Consul Leader lives at %s", agent_url, leader)
            return agent_url == leader

        except Exception:
            return False

    def _check_for_leader_change(self):

        if self.perform_new_leader_checks and self.perform_self_leader_check:
            self.log.warning(
                'Both perform_self_leader_check and perform_new_leader_checks are set, '
                'ignoring perform_new_leader_checks'
            )
        elif not self.perform_new_leader_checks and not self.perform_self_leader_check:
            # Nothing to do here
            return

        leader = self._get_cluster_leader()

        if not leader:
            # A few things could be happening here.
            #   1. Consul Agent is Down
            #   2. The cluster is in the midst of a leader election
            #   3. The Datadog agent is not able to reach the Consul instance (network partition et al.)
            self.log.warning('Consul Leader information is not available!')
            return

        if not self._last_known_leader:
            # We have no state preserved, store some and return
            self._last_known_leader = leader
            return

        agent = self._get_agent_url()
        agent_dc = self._get_agent_datacenter()

        if leader != self._last_known_leader:
            # There was a leadership change
            if self.perform_new_leader_checks or (self.perform_self_leader_check and agent == leader):
                # We either emit all leadership changes or emit when we become the leader and that just happened
                self.log.info('Leader change from %s to %s. Sending new leader event', self._last_known_leader, leader)

                self.event(
                    {
                        "timestamp": timestamp(),
                        "event_type": "consul.new_leader",
                        "source_type_name": SOURCE_TYPE_NAME,
                        "msg_title": "New Consul Leader Elected in consul_datacenter:{}".format(agent_dc),
                        "aggregation_key": "consul.new_leader",
                        "msg_text": "The Node at {} is the new leader of the consul datacenter {}".format(
                            leader, agent_dc
                        ),
                        "tags": [
                            "prev_consul_leader:{}".format(self._last_known_leader),
                            "curr_consul_leader:{}".format(leader),
                            "consul_datacenter:{}".format(agent_dc),
                        ],
                    }
                )

        self._last_known_leader = leader

    # Consul Catalog Accessors
    def get_peers_in_cluster(self):
        return self.consul_request('/v1/status/peers') or []

    def get_services_in_cluster(self):
        return self.consul_request('/v1/catalog/services')

    def get_nodes_with_service(self, service):
        consul_request_url = '/v1/health/service/{}'.format(service)

        return self.consul_request(consul_request_url)

    def _cull_services_list(self, services):

        if self.service_whitelist:
            if len(self.service_whitelist) > self.max_services:
                self.warning('More than %d services in whitelist. Service list will be truncated.', self.max_services)

            whitelisted_services = [s for s in services if s in self.service_whitelist]
            services = {s: services[s] for s in whitelisted_services[: self.max_services]}
        else:
            if len(services) <= self.max_services:
                log_line = 'Consul service whitelist not defined. Agent will poll for all {} services found'.format(
                    len(services)
                )
                self.log.debug(log_line)
            else:
                log_line = 'Consul service whitelist not defined. Agent will poll for at most {} services'.format(
                    self.max_services
                )
                self.warning(log_line)
                services = {s: services[s] for s in list(islice(iterkeys(services), 0, self.max_services))}

        return services

    @staticmethod
    def _get_service_tags(service, tags):
        service_tags = ['consul_service_id:{}'.format(service)]

        for tag in tags:
            service_tags.append('consul_{}_service_tag:{}'.format(service, tag))
            service_tags.append('consul_service_tag:{}'.format(tag))

        return service_tags

    def check(self, _):

        self._check_for_leader_change()
        self._collect_metadata()

        peers = self.get_peers_in_cluster()
        main_tags = []
        agent_dc = self._get_agent_datacenter()

        if agent_dc is not None:
            main_tags.append('consul_datacenter:{}'.format(agent_dc))

        main_tags += self.base_tags

        if not self._is_instance_leader():
            self.gauge("consul.peers", len(peers), tags=main_tags + ["mode:follower"])
            if not self.single_node_install:
                self.log.debug(
                    "This consul agent is not the cluster leader. "
                    "Skipping service and catalog checks for this instance"
                )
                return
        else:
            self.gauge("consul.peers", len(peers), tags=main_tags + ["mode:leader"])

        service_check_tags = main_tags + ['consul_url:{}'.format(self.url)]

        try:
            # Make service checks from health checks for all services in catalog
            health_state = self.consul_request('/v1/health/state/any')

            sc = {}
            # compute the highest status level (OK < WARNING < CRITICAL) a a check among all the nodes is running on.
            for check in health_state:
                sc_id = '{}/{}/{}'.format(check['CheckID'], check.get('ServiceID', ''), check.get('ServiceName', ''))
                status = STATUS_SC.get(check['Status'])
                if status is None:
                    status = AgentCheck.UNKNOWN

                if sc_id not in sc:
                    tags = ["check:{}".format(check["CheckID"])]
                    if check["ServiceName"]:
                        tags.append('consul_service:{}'.format(check['ServiceName']))
                        if not self.disable_legacy_service_tag:
                            self._log_deprecation('service_tag', 'consul_service')
                            tags.append('service:{}'.format(check['ServiceName']))
                    if check["ServiceID"]:
                        tags.append("consul_service_id:{}".format(check["ServiceID"]))
                    sc[sc_id] = {'status': status, 'tags': tags}

                elif STATUS_SEVERITY[status] > STATUS_SEVERITY[sc[sc_id]['status']]:
                    sc[sc_id]['status'] = status

            for s in itervalues(sc):
                self.service_check(HEALTH_CHECK, s['status'], tags=main_tags + s['tags'])

        except Exception as e:
            self.log.error(e)
            self.service_check(CONSUL_CHECK, AgentCheck.CRITICAL, tags=service_check_tags)
        else:
            self.service_check(CONSUL_CHECK, AgentCheck.OK, tags=service_check_tags)

        if self.perform_catalog_checks:
            # Collect node by service, and service by node counts for a whitelist of services

            services = self.get_services_in_cluster()

            self.count_all_nodes(main_tags)

            services = self._cull_services_list(services)

            # {node_id: {"up: 0, "passing": 0, "warning": 0, "critical": 0}
            nodes_to_service_status = defaultdict(lambda: defaultdict(int))

            for service in services:
                # For every service in the cluster,
                # Gauge the following:
                # `consul.catalog.nodes_up` : # of Nodes registered with that service
                # `consul.catalog.nodes_passing` : # of Nodes with service status `passing` from those registered
                # `consul.catalog.nodes_warning` : # of Nodes with service status `warning` from those registered
                # `consul.catalog.nodes_critical` : # of Nodes with service status `critical` from those registered

                service_tags = self._get_service_tags(service, services[service])

                nodes_with_service = self.get_nodes_with_service(service)

                # {'up': 0, 'passing': 0, 'warning': 0, 'critical': 0}
                node_status = defaultdict(int)

                for node in nodes_with_service:
                    # The node_id is n['Node']['Node']
                    node_id = node.get('Node', {}).get("Node")

                    # An additional service is registered on this node. Bump up the counter
                    nodes_to_service_status[node_id]["up"] += 1

                    # If there is no Check for the node then Consul and dd-agent consider it up
                    if 'Checks' not in node:
                        node_status['passing'] += 1
                        node_status['up'] += 1
                    else:
                        found_critical = False
                        found_warning = False
                        found_serf_health = False

                        for check in node['Checks']:
                            if check['CheckID'] == 'serfHealth':
                                found_serf_health = True

                                # For backwards compatibility, the "up" node_status is computed
                                # based on the total # of nodes 'running' as part of the service.

                                # If the serfHealth is `critical` it means the Consul agent isn't even responding,
                                # and we don't register the node as `up`
                                if check['Status'] != 'critical':
                                    node_status["up"] += 1
                                    continue

                            if check['Status'] == 'critical':
                                found_critical = True
                                break
                            elif check['Status'] == 'warning':
                                found_warning = True
                                # Keep looping in case there is a critical status

                        # Increment the counters based on what was found in Checks
                        # `critical` checks override `warning`s, and if neither are found,
                        # register the node as `passing`
                        if found_critical:
                            node_status['critical'] += 1
                            nodes_to_service_status[node_id]["critical"] += 1
                        elif found_warning:
                            node_status['warning'] += 1
                            nodes_to_service_status[node_id]["warning"] += 1
                        else:
                            if not found_serf_health:
                                # We have not found a serfHealth check for this node, which is unexpected
                                # If we get here assume this node's status is "up", since we register it as 'passing'
                                node_status['up'] += 1

                            node_status['passing'] += 1
                            nodes_to_service_status[node_id]["passing"] += 1

                for status_key in STATUS_SC:
                    status_value = node_status[status_key]
                    self.gauge(
                        '{}.nodes_{}'.format(CONSUL_CATALOG_CHECK, status_key),
                        status_value,
                        tags=main_tags + service_tags,
                    )

            for node, service_status in iteritems(nodes_to_service_status):
                # For every node discovered for whitelisted services, gauge the following:
                # `consul.catalog.services_up` : Total services registered on node
                # `consul.catalog.services_passing` : Total passing services on node
                # `consul.catalog.services_warning` : Total warning services on node
                # `consul.catalog.services_critical` : Total critical services on node

                node_tags = ['consul_node_id:{}'.format(node)]
                self.gauge('{}.services_up'.format(CONSUL_CATALOG_CHECK), len(services), tags=main_tags + node_tags)

                for status_key in STATUS_SC:
                    status_value = service_status[status_key]
                    self.gauge(
                        '{}.services_{}'.format(CONSUL_CATALOG_CHECK, status_key),
                        status_value,
                        tags=main_tags + node_tags,
                    )

        if self.perform_network_latency_checks:
            self.check_network_latency(agent_dc, main_tags)

    def _get_coord_datacenters(self):
        return self.consul_request('/v1/coordinate/datacenters')

    def _get_coord_nodes(self):
        return self.consul_request('v1/coordinate/nodes')

    def check_network_latency(self, agent_dc, main_tags):

        datacenters = self._get_coord_datacenters()
        for datacenter in datacenters:
            name = datacenter['Datacenter']
            if name == agent_dc:
                # This is us, time to collect inter-datacenter data
                for other in datacenters:
                    other_name = other['Datacenter']
                    if name == other_name:
                        # Ignore ourselves
                        continue
                    latencies = []
                    for node_a in datacenter['Coordinates']:
                        for node_b in other['Coordinates']:
                            latencies.append(distance(node_a, node_b))
                    latencies.sort()
                    tags = main_tags + ['source_datacenter:{}'.format(name), 'dest_datacenter:{}'.format(other_name)]
                    n = len(latencies)
                    half_n = n // 2
                    if n % 2:
                        median = latencies[half_n]
                    else:
                        median = (latencies[half_n - 1] + latencies[half_n]) / 2
                    self.gauge('consul.net.dc.latency.min', latencies[0], hostname='', tags=tags)
                    self.gauge('consul.net.dc.latency.median', median, hostname='', tags=tags)
                    self.gauge('consul.net.dc.latency.max', latencies[-1], hostname='', tags=tags)

                # We've found ourselves, we can move on
                break

        # Intra-datacenter
        nodes = self._get_coord_nodes()
        if len(nodes) == 1:
            self.log.debug("Only 1 node in cluster, skipping network latency metrics.")
        else:
            for node in nodes:
                node_name = node['Node']
                latencies = []
                for other in nodes:
                    other_name = other['Node']
                    if node_name == other_name:
                        continue
                    latencies.append(distance(node, other))
                latencies.sort()
                n = len(latencies)
                half_n = n // 2
                if n % 2:
                    median = latencies[half_n]
                else:
                    median = (latencies[half_n - 1] + latencies[half_n]) / 2
                self.gauge('consul.net.node.latency.min', latencies[0], hostname=node_name, tags=main_tags)
                self.gauge(
                    'consul.net.node.latency.p25', latencies[ceili(n * 0.25) - 1], hostname=node_name, tags=main_tags
                )
                self.gauge('consul.net.node.latency.median', median, hostname=node_name, tags=main_tags)
                self.gauge(
                    'consul.net.node.latency.p75', latencies[ceili(n * 0.75) - 1], hostname=node_name, tags=main_tags
                )
                self.gauge(
                    'consul.net.node.latency.p90', latencies[ceili(n * 0.90) - 1], hostname=node_name, tags=main_tags
                )
                self.gauge(
                    'consul.net.node.latency.p95', latencies[ceili(n * 0.95) - 1], hostname=node_name, tags=main_tags
                )
                self.gauge(
                    'consul.net.node.latency.p99', latencies[ceili(n * 0.99) - 1], hostname=node_name, tags=main_tags
                )
                self.gauge('consul.net.node.latency.max', latencies[-1], hostname=node_name, tags=main_tags)

    def _get_all_nodes(self):
        return self.consul_request('v1/catalog/nodes')

    def count_all_nodes(self, main_tags):
        nodes = self._get_all_nodes()
        self.gauge('consul.catalog.total_nodes', len(nodes), tags=main_tags)

    def _collect_metadata(self):
        local_config = self._get_local_config()
        agent_version = local_config.get('Config', {}).get('Version')
        self.log.debug("Agent version is `%s`", agent_version)
        if agent_version:
            self.set_metadata('version', agent_version)
