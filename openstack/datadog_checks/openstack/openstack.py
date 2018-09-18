# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datetime import datetime, timedelta
import re
import time
import random
import copy

import requests

from datadog_checks.checks import AgentCheck
from datadog_checks.config import is_affirmative

from .exceptions import (InstancePowerOffFailure, IncompleteConfig, IncompleteAuthScope,
                         IncompleteIdentity, MissingNovaEndpoint, MissingNeutronEndpoint, KeystoneUnreachable)
from .scopes import OpenStackProjectScope, OpenStackUnscoped


try:
    # Agent >= 6.0: the check pushes tags invoking `set_external_tags`
    from datadog_agent import set_external_tags
except ImportError:
    # Agent < 6.0: the Agent pulls tags invoking `OpenStackCheck.get_external_host_tags`
    set_external_tags = None


SOURCE_TYPE = 'openstack'

V21_NOVA_API_VERSION = 'v2.1'

DEFAULT_KEYSTONE_API_VERSION = 'v3'
DEFAULT_NOVA_API_VERSION = V21_NOVA_API_VERSION
FALLBACK_NOVA_API_VERSION = 'v2'
DEFAULT_NEUTRON_API_VERSION = 'v2.0'

DEFAULT_API_REQUEST_TIMEOUT = 10  # seconds

NOVA_HYPERVISOR_METRICS = [
    'current_workload',
    'disk_available_least',
    'free_disk_gb',
    'free_ram_mb',
    'local_gb',
    'local_gb_used',
    'memory_mb',
    'memory_mb_used',
    'running_vms',
    'vcpus',
    'vcpus_used',
]

NOVA_SERVER_METRICS = [
    "hdd_errors",
    "hdd_read",
    "hdd_read_req",
    "hdd_write",
    "hdd_write_req",
    "memory",
    "memory-actual",
    "memory-rss",
    "cpu0_time",
    "vda_errors",
    "vda_read",
    "vda_read_req",
    "vda_write",
    "vda_write_req",
]

NOVA_SERVER_INTERFACE_SEGMENTS = ['_rx', '_tx']

PROJECT_METRICS = dict(
    [
        ("maxImageMeta", "max_image_meta"),
        ("maxPersonality", "max_personality"),
        ("maxPersonalitySize", "max_personality_size"),
        ("maxSecurityGroupRules", "max_security_group_rules"),
        ("maxSecurityGroups", "max_security_groups"),
        ("maxServerMeta", "max_server_meta"),
        ("maxTotalCores", "max_total_cores"),
        ("maxTotalFloatingIps", "max_total_floating_ips"),
        ("maxTotalInstances", "max_total_instances"),
        ("maxTotalKeypairs", "max_total_keypairs"),
        ("maxTotalRAMSize", "max_total_ram_size"),
        ("totalImageMetaUsed", "total_image_meta_used"),
        ("totalPersonalityUsed", "total_personality_used"),
        ("totalPersonalitySizeUsed", "total_personality_size_used"),
        ("totalSecurityGroupRulesUsed", "total_security_group_rules_used"),
        ("totalSecurityGroupsUsed", "total_security_groups_used"),
        ("totalServerMetaUsed", "total_server_meta_used"),
        ("totalCoresUsed", "total_cores_used"),
        ("totalFloatingIpsUsed", "total_floating_ips_used"),
        ("totalInstancesUsed", "total_instances_used"),
        ("totalKeypairsUsed", "total_keypairs_used"),
        ("totalRAMUsed", "total_ram_used"),
    ]
)

DIAGNOSTICABLE_STATES = ['ACTIVE']

REMOVED_STATES = ['DELETED', 'SHUTOFF']

BASE_BACKOFF_SECS = 15
MAX_BACKOFF_SECS = 300


class OpenStackCheck(AgentCheck):
    CACHE_TTL = {"aggregates": 300, "physical_hosts": 300, "hypervisors": 300}  # seconds

    FETCH_TIME_ACCESSORS = {
        "aggregates": "_last_aggregate_fetch_time",
        "physical_hosts": "_last_host_fetch_time",
        "hypervisors": "_last_hypervisor_fetch_time",
    }

    HYPERVISOR_STATE_UP = 'up'
    HYPERVISOR_STATE_DOWN = 'down'
    NETWORK_STATE_UP = 'UP'

    NETWORK_API_SC = 'openstack.neutron.api.up'
    COMPUTE_API_SC = 'openstack.nova.api.up'
    IDENTITY_API_SC = 'openstack.keystone.api.up'

    # Service checks for individual hypervisors and networks
    HYPERVISOR_SC = 'openstack.nova.hypervisor.up'
    NETWORK_SC = 'openstack.neutron.network.up'

    HYPERVISOR_CACHE_EXPIRY = 120  # seconds

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        self._ssl_verify = is_affirmative(init_config.get("ssl_verify", True))
        self.keystone_server_url = init_config.get("keystone_server_url")
        self._hypervisor_name_cache = {}

        if not self.keystone_server_url:
            raise IncompleteConfig()

        # Current authentication scopes
        self._parent_scope = None
        self._current_scope = None

        # Cache some things between runs for values that change rarely
        self._aggregate_list = None

        # Mapping of check instances to associated OpenStack project scopes
        self.instance_map = {}

        # Mapping of Nova-managed servers to tags
        self.external_host_tags = {}

        self.exclude_network_id_rules = set([re.compile(ex) for ex in init_config.get('exclude_network_ids', [])])

        self.exclude_server_id_rules = set([re.compile(ex) for ex in init_config.get('exclude_server_ids', [])])

        skip_proxy = not is_affirmative(init_config.get('use_agent_proxy', True))
        self.proxy_config = None if skip_proxy else self.proxies

        self.backoff = {}
        random.seed()

        # ISO8601 date time: used to filter the call to get the list of nova servers
        self.changes_since_time = {}

        # Ex: server_details_by_id = {
        #   UUID: {UUID: <value>, etc}
        #   1: {id: 1, name: hostA},
        #   2: {id: 2, name: hostB}
        # }
        self.server_details_by_id = {}

    def _make_request_with_auth_fallback(self, url, headers=None, params=None):
        """
        Generic request handler for OpenStack API requests
        Raises specialized Exceptions for commonly encountered error codes
        """
        self.log.debug("Request URL and Params: %s, %s", url, params)
        try:
            resp = requests.get(
                url,
                headers=headers,
                verify=self._ssl_verify,
                params=params,
                timeout=DEFAULT_API_REQUEST_TIMEOUT,
                proxies=self.proxy_config,
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.log.debug("Error contacting openstack endpoint: %s", e)
            if resp.status_code == 401:
                self.log.info('Need to reauthenticate before next check')

                # Delete the scope, we'll populate a new one on the next run for this instance
                self.delete_current_scope()
            elif resp.status_code == 409:
                raise InstancePowerOffFailure()
            elif resp.status_code == 404:
                raise e
            else:
                raise

        return resp.json()

    def _instance_key(self, instance):
        i_key = instance.get('name')
        if not i_key:
            # We need a name to identify this instance
            raise IncompleteConfig()
        return i_key

    def delete_current_scope(self):
        scope_to_delete = self._parent_scope if self._parent_scope else self._current_scope
        for i_key, scope in self.instance_map.items():
            if scope is scope_to_delete:
                self.log.debug("Deleting current scope: %s", i_key)
                del self.instance_map[i_key]

    def should_run(self, instance):
        i_key = self._instance_key(instance)
        if i_key not in self.backoff:
            self.backoff[i_key] = {'retries': 0, 'scheduled': time.time()}

        if self.backoff[i_key]['scheduled'] <= time.time():
            return True

        return False

    def do_backoff(self, instance):
        i_key = self._instance_key(instance)
        tracker = self.backoff[i_key]

        self.backoff[i_key]['retries'] += 1
        jitter = min(MAX_BACKOFF_SECS, BASE_BACKOFF_SECS * 2 ** self.backoff[i_key]['retries'])

        # let's add some jitter  (half jitter)
        backoff_interval = jitter / 2
        backoff_interval += random.randint(0, backoff_interval)

        tags = instance.get('tags', [])
        hypervisor_name = self._hypervisor_name_cache.get(i_key)
        if hypervisor_name:
            tags.extend("hypervisor:{}".format(hypervisor_name))

        self.gauge("openstack.backoff.interval", backoff_interval, tags=tags)
        self.gauge("openstack.backoff.retries", self.backoff[i_key]['retries'], tags=tags)

        tracker['scheduled'] = time.time() + backoff_interval

    def reset_backoff(self, instance):
        i_key = self._instance_key(instance)
        self.backoff[i_key]['retries'] = 0
        self.backoff[i_key]['scheduled'] = time.time()

    def get_scope_for_instance(self, instance):
        i_key = self._instance_key(instance)
        self.log.debug("Getting scope for instance %s", i_key)
        return self.instance_map[i_key]

    def set_scope_for_instance(self, instance, scope):
        i_key = self._instance_key(instance)
        self.log.debug("Setting scope for instance %s", i_key)
        self.instance_map[i_key] = scope

    def delete_scope_for_instance(self, instance):
        i_key = self._instance_key(instance)
        self.log.debug("Deleting scope for instance %s", i_key)
        del self.instance_map[i_key]

    def get_auth_token(self, instance=None):
        if not instance:
            # Assume instance scope is populated on self
            return self._current_scope.auth_token

        return self.get_scope_for_instance(instance).auth_token

    # Network
    def get_neutron_endpoint(self, instance=None):
        if not instance:
            # Assume instance scope is populated on self
            return self._current_scope.service_catalog.neutron_endpoint

        return self.get_scope_for_instance(instance).service_catalog.neutron_endpoint

    def get_network_stats(self, tags):
        """
        Collect stats for all reachable networks
        """

        # FIXME: (aaditya) Check all networks defaults to true
        # until we can reliably assign agents to networks to monitor
        if is_affirmative(self.init_config.get('check_all_networks', True)):
            all_network_ids = set(self.get_all_network_ids())

            # Filter out excluded networks
            network_ids = [
                network_id
                for network_id in all_network_ids
                if not any([re.match(exclude_id, network_id) for exclude_id in self.exclude_network_id_rules])
            ]
        else:
            network_ids = self.init_config.get('network_ids', [])

        if not network_ids:
            self.warning(
                "Your check is not configured to monitor any networks.\n"
                + "Please list `network_ids` under your init_config"
            )

        for nid in network_ids:
            self.get_stats_for_single_network(nid, tags)

    def get_all_network_ids(self):
        url = '{0}/{1}/networks'.format(self.get_neutron_endpoint(), DEFAULT_NEUTRON_API_VERSION)
        headers = {'X-Auth-Token': self.get_auth_token()}

        network_ids = []
        try:
            net_details = self._make_request_with_auth_fallback(url, headers)
            for network in net_details['networks']:
                network_ids.append(network['id'])
        except Exception as e:
            self.warning('Unable to get the list of all network ids: {0}'.format(str(e)))
            raise e

        return network_ids

    def get_stats_for_single_network(self, network_id, tags):
        url = '{0}/{1}/networks/{2}'.format(self.get_neutron_endpoint(), DEFAULT_NEUTRON_API_VERSION, network_id)
        headers = {'X-Auth-Token': self.get_auth_token()}
        net_details = self._make_request_with_auth_fallback(url, headers)

        service_check_tags = ['network:{0}'.format(network_id)] + tags

        network_name = net_details.get('network', {}).get('name')
        if network_name is not None:
            service_check_tags.append('network_name:{0}'.format(network_name))

        tenant_id = net_details.get('network', {}).get('tenant_id')
        if tenant_id is not None:
            service_check_tags.append('tenant_id:{0}'.format(tenant_id))

        if net_details.get('network', {}).get('admin_state_up'):
            self.service_check(self.NETWORK_SC, AgentCheck.OK, tags=service_check_tags)
        else:
            self.service_check(self.NETWORK_SC, AgentCheck.CRITICAL, tags=service_check_tags)

    # Compute
    def get_nova_endpoint(self, instance=None):
        if not instance:
            # Assume instance scope is populated on self
            return self._current_scope.service_catalog.nova_endpoint

        return self.get_scope_for_instance(instance).service_catalog.nova_endpoint

    def _parse_uptime_string(self, uptime):
        """ Parse u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n' """
        uptime = uptime.strip()
        load_averages = uptime[uptime.find('load average:'):].split(':')[1].split(',')
        uptime_sec = uptime.split(',')[0]

        return {'loads': map(float, load_averages), 'uptime_sec': uptime_sec}

    def get_all_hypervisor_ids(self, filter_by_host=None):
        nova_version = self.init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)
        if nova_version >= V21_NOVA_API_VERSION:
            url = '{0}/os-hypervisors'.format(self.get_nova_endpoint())
            headers = {'X-Auth-Token': self.get_auth_token()}

            hypervisor_ids = []
            try:
                hv_list = self._make_request_with_auth_fallback(url, headers)
                for hv in hv_list['hypervisors']:
                    if filter_by_host and hv['hypervisor_hostname'] == filter_by_host:
                        # Assume one-one relationship between hypervisor and host, return the 1st found
                        return [hv['id']]

                    hypervisor_ids.append(hv['id'])
            except Exception as e:
                self.warning('Unable to get the list of all hypervisors: {0}'.format(str(e)))
                raise e

            return hypervisor_ids
        else:
            if not self.init_config.get("hypervisor_ids"):
                self.warning(
                    "Nova API v2 requires admin privileges to index hypervisors. "
                    + "Please specify the hypervisor you wish to monitor under the `hypervisor_ids` section"
                )
                return []
            return self.init_config.get("hypervisor_ids")

    def get_all_aggregate_hypervisors(self):
        url = '{0}/os-aggregates'.format(self.get_nova_endpoint())
        headers = {'X-Auth-Token': self.get_auth_token()}

        hypervisor_aggregate_map = {}
        try:
            aggregate_list = self._make_request_with_auth_fallback(url, headers)
            for v in aggregate_list['aggregates']:
                for host in v['hosts']:
                    hypervisor_aggregate_map[host] = {
                        'aggregate': v['name'],
                        'availability_zone': v['availability_zone'],
                    }

        except Exception as e:
            self.warning('Unable to get the list of aggregates: {0}'.format(str(e)))
            raise e

        return hypervisor_aggregate_map

    def get_uptime_for_single_hypervisor(self, hyp_id):
        url = '{0}/os-hypervisors/{1}/uptime'.format(self.get_nova_endpoint(), hyp_id)
        headers = {'X-Auth-Token': self.get_auth_token()}

        resp = self._make_request_with_auth_fallback(url, headers)
        uptime = resp['hypervisor']['uptime']
        return self._parse_uptime_string(uptime)

    def get_stats_for_single_hypervisor(self, hyp_id, instance, host_tags=None, custom_tags=None):
        url = '{0}/os-hypervisors/{1}'.format(self.get_nova_endpoint(), hyp_id)
        headers = {'X-Auth-Token': self.get_auth_token()}
        resp = self._make_request_with_auth_fallback(url, headers)
        hyp = resp['hypervisor']
        host_tags = host_tags or []
        self._hypervisor_name_cache[self._instance_key(instance)] = hyp['hypervisor_hostname']
        custom_tags = custom_tags or []
        tags = [
            'hypervisor:{0}'.format(hyp['hypervisor_hostname']),
            'hypervisor_id:{0}'.format(hyp['id']),
            'virt_type:{0}'.format(hyp['hypervisor_type']),
        ]
        tags.extend(host_tags)
        tags.extend(custom_tags)
        service_check_tags = list(custom_tags)

        try:
            uptime = self.get_uptime_for_single_hypervisor(hyp['id'])
        except Exception as e:
            self.warning('Unable to get uptime for hypervisor {0}: {1}'.format(hyp['id'], str(e)))
            uptime = {}

        hyp_state = hyp.get('state', None)
        if hyp_state is None:
            try:
                # Fall back for pre Nova v2.1 to the uptime response
                if uptime.get('uptime_sec', 0) > 0:
                    hyp_state = self.HYPERVISOR_STATE_UP
                else:
                    hyp_state = self.HYPERVISOR_STATE_DOWN
            except Exception:
                # This creates the AgentCheck.UNKNOWN state
                pass

        if hyp_state is None:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.UNKNOWN, tags=service_check_tags)
        elif hyp_state != self.HYPERVISOR_STATE_UP:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.CRITICAL, tags=service_check_tags)
        else:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.OK, tags=service_check_tags)

        for label, val in hyp.iteritems():
            if label in NOVA_HYPERVISOR_METRICS:
                metric_label = "openstack.nova.{0}".format(label)
                self.gauge(metric_label, val, tags=tags)

        load_averages = uptime.get("loads")
        if load_averages is not None:
            assert len(load_averages) == 3
            for i, avg in enumerate([1, 5, 15]):
                self.gauge('openstack.nova.hypervisor_load.{0}'.format(avg), load_averages[i], tags=tags)

    # Get all of the server IDs and their metadata and cache them
    # After the first run, we will only get servers that have changed state since the last collection run
    def get_all_servers(self, i_key, collect_all_tenants, filter_by_host=None):
        query_params = {}
        if filter_by_host:
            query_params["host"] = filter_by_host

        # If we don't have a timestamp for this instance, default to None
        if i_key in self.changes_since_time:
            query_params['changes-since'] = self.changes_since_time.get(i_key)

        url = '{0}/servers/detail'.format(self.get_nova_endpoint())
        headers = {'X-Auth-Token': self.get_auth_token()}

        if collect_all_tenants:
            query_params["all_tenants"] = True
        servers = []

        try:
            # Get a list of active servers
            query_params['status'] = 'ACTIVE'
            resp = self._make_request_with_auth_fallback(url, headers, params=query_params)
            servers.extend(resp['servers'])

            # Don't collect Deleted or Shut off VMs on the first run:
            if i_key in self.changes_since_time:

                # Get a list of deleted serversTimestamp used to filter the call to get the list
                # Need to have admin perms for this to take affect
                query_params['deleted'] = 'true'
                del query_params['status']
                resp = self._make_request_with_auth_fallback(url, headers, params=query_params)

                servers.extend(resp['servers'])
                query_params['deleted'] = 'false'

                # Get a list of shut off servers
                query_params['status'] = 'SHUTOFF'
                resp = self._make_request_with_auth_fallback(url, headers, params=query_params)
                servers.extend(resp['servers'])

            self.changes_since_time[i_key] = datetime.utcnow().isoformat()

        except Exception as e:
            self.warning('Unable to get the list of all servers: {0}'.format(str(e)))
            raise e

        for server in servers:
            new_server = {}

            new_server['server_id'] = server.get('id')
            new_server['state'] = server.get('status')
            new_server['server_name'] = server.get('name')
            new_server['hypervisor_hostname'] = server.get('OS-EXT-SRV-ATTR:hypervisor_hostname')
            new_server['tenant_id'] = server.get('tenant_id')

            # Update our cached list of servers
            if (
                new_server['server_id'] not in self.server_details_by_id
                and new_server['state'] in DIAGNOSTICABLE_STATES
            ):
                self.log.debug("Adding server to cache: %s", new_server)
                # The project may not exist if the server isn't in an active state
                # Query for the project name here to avoid 404s
                new_server['project_name'] = self.get_project_name_from_id(new_server['tenant_id'])
                self.server_details_by_id[new_server['server_id']] = new_server
            elif new_server['server_id'] in self.server_details_by_id and new_server['state'] in REMOVED_STATES:
                self.log.debug("Removing server from cache: %s", new_server)
                try:
                    del self.server_details_by_id[new_server['server_id']]
                except KeyError as e:
                    self.log.debug("Server: %s has already been removed from the cache", new_server['server_id'])

        return self.server_details_by_id

    def get_project_name_from_id(self, tenant_id):
        url = "{0}/{1}/{2}/{3}".format(self.keystone_server_url, DEFAULT_KEYSTONE_API_VERSION, "projects", tenant_id)
        self.log.debug("Project URL is %s", url)
        headers = {'X-Auth-Token': self.get_auth_token()}
        try:
            r = self._make_request_with_auth_fallback(url, headers)
            return r['project']['name']

        except Exception as e:
            self.warning('Unable to get project name: {0}'.format(str(e)))
            raise e

    def get_stats_for_single_server(self, server_details, tags=None):
        def _is_valid_metric(label):
            return label in NOVA_SERVER_METRICS or any(seg in label for seg in NOVA_SERVER_INTERFACE_SEGMENTS)

        server_id = server_details.get('server_id')
        server_name = server_details.get('server_name')
        hypervisor_hostname = server_details.get('hypervisor_hostname')
        project_name = server_details.get('project_name')

        server_stats = {}
        headers = {'X-Auth-Token': self.get_auth_token()}
        url = '{0}/servers/{1}/diagnostics'.format(self.get_nova_endpoint(), server_id)
        try:
            server_stats = self._make_request_with_auth_fallback(url, headers)
        except InstancePowerOffFailure:  # 409 response code came back fro nova
            self.log.debug("Server %s is powered off and cannot be monitored", server_id)
            del self.server_details_by_id[server_id]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.log.debug("Server %s is not in an ACTIVE state and cannot be monitored, %s", server_id, e)
                del self.server_details_by_id[server_id]
            else:
                self.log.debug("Received HTTP Error when reaching the nova endpoint")
                raise e
        except Exception as e:
            self.warning("Unknown error when monitoring %s : %s" % (server_id, e))
            raise e

        if server_stats:
            tags = tags or []
            if project_name:
                tags.append("project_name:{}".format(project_name))
            if hypervisor_hostname:
                tags.append("hypervisor:{0}".format(hypervisor_hostname))
            if server_name:
                tags.append("server_name:{0}".format(server_name))
            for st in server_stats:
                if _is_valid_metric(st):
                    self.gauge(
                        "openstack.nova.server.{0}".format(st.replace("-", "_")),
                        server_stats[st],
                        tags=tags,
                        hostname=server_id,
                    )

    def get_stats_for_single_project(self, project, tags=None):
        def _is_valid_metric(label):
            return label in PROJECT_METRICS

        if tags is None:
            tags = []

        server_tags = copy.deepcopy(tags)

        project_name = project.get('name')

        self.log.debug("Collecting metrics for project. name: {0} id: {1}".format(project_name, project['id']))

        url = '{0}/limits'.format(self.get_nova_endpoint())
        headers = {'X-Auth-Token': self.get_auth_token()}
        server_stats = self._make_request_with_auth_fallback(url, headers, params={"tenant_id": project['id']})

        server_tags.append('tenant_id:{0}'.format(project['id']))

        if project_name:
            server_tags.append('project_name:{0}'.format(project['name']))

        for st in server_stats['limits']['absolute']:
            if _is_valid_metric(st):
                metric_key = PROJECT_METRICS[st]
                self.gauge(
                    "openstack.nova.limits.{0}".format(metric_key),
                    server_stats['limits']['absolute'][st],
                    tags=server_tags,
                )

    # Cache util
    def _is_expired(self, entry):
        assert entry in ["aggregates", "physical_hosts", "hypervisors"]
        ttl = self.CACHE_TTL.get(entry)
        last_fetch_time = getattr(self, self.FETCH_TIME_ACCESSORS.get(entry))
        return datetime.now() - last_fetch_time > timedelta(seconds=ttl)

    def _get_and_set_aggregate_list(self):
        if not self._aggregate_list or self._is_expired("aggregates"):
            self._aggregate_list = self.get_all_aggregate_hypervisors()
            self._last_aggregate_fetch_time = datetime.now()

        return self._aggregate_list

    def _send_api_service_checks(self, scope, tags):
        # Nova
        headers = {"X-Auth-Token": scope.auth_token}

        try:
            requests.get(
                scope.service_catalog.nova_endpoint,
                headers=headers,
                verify=self._ssl_verify,
                timeout=DEFAULT_API_REQUEST_TIMEOUT,
                proxies=self.proxy_config,
            )
            self.service_check(
                self.COMPUTE_API_SC,
                AgentCheck.OK,
                tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + tags,
            )
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self.service_check(
                self.COMPUTE_API_SC,
                AgentCheck.CRITICAL,
                tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + tags,
            )

        # Neutron
        try:
            requests.get(
                scope.service_catalog.neutron_endpoint,
                headers=headers,
                verify=self._ssl_verify,
                timeout=DEFAULT_API_REQUEST_TIMEOUT,
                proxies=self.proxy_config,
            )
            self.service_check(
                self.NETWORK_API_SC,
                AgentCheck.OK,
                tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + tags,
            )
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self.service_check(
                self.NETWORK_API_SC,
                AgentCheck.CRITICAL,
                tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + tags,
            )

    def ensure_auth_scope(self, instance):
        """
        Guarantees a valid auth scope for this instance, and returns it

        Communicates with the identity server and initializes a new scope when one is absent, or has been forcibly
        removed due to token expiry
        """
        instance_scope = None

        custom_tags = instance.get('tags', [])
        if custom_tags is None:
            custom_tags = []
        try:
            instance_scope = self.get_scope_for_instance(instance)
        except KeyError:

            # We're missing a project scope for this instance
            # Let's populate it now
            try:
                if 'auth_scope' in instance:
                    instance_scope = OpenStackProjectScope.from_config(self.init_config, instance, self.proxy_config)
                else:
                    instance_scope = OpenStackUnscoped.from_config(self.init_config, instance, self.proxy_config)

                self.service_check(
                    self.IDENTITY_API_SC,
                    AgentCheck.OK,
                    tags=["server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )
            except KeystoneUnreachable as e:
                self.warning(
                    "The agent could not contact the specified identity server at %s . \
                    Are you sure it is up at that address?"
                    % self.init_config.get("keystone_server_url")
                )
                self.log.debug("Problem grabbing auth token: %s", e)
                self.service_check(
                    self.IDENTITY_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )

                # If Keystone is down/unreachable, we default the
                # Nova and Neutron APIs to UNKNOWN since we cannot access the service catalog
                self.service_check(
                    self.NETWORK_API_SC,
                    AgentCheck.UNKNOWN,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )
                self.service_check(
                    self.COMPUTE_API_SC,
                    AgentCheck.UNKNOWN,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )

            except MissingNovaEndpoint as e:
                self.warning("The agent could not find a compatible Nova endpoint in your service catalog!")
                self.log.debug("Failed to get nova endpoint for response catalog: %s", e)
                self.service_check(
                    self.COMPUTE_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )

            except MissingNeutronEndpoint:
                self.warning("The agent could not find a compatible Neutron endpoint in your service catalog!")
                self.service_check(
                    self.NETWORK_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )
            else:
                self.set_scope_for_instance(instance, instance_scope)

        return instance_scope

    def get_scope_map(self, instance):
        instance_scope = self.ensure_auth_scope(instance)

        if not instance_scope:
            # Fast fail in the absence of an instance_scope
            raise IncompleteConfig()

        scope_map = {}
        if isinstance(instance_scope, OpenStackProjectScope):
            #  Key could be anything but same format for consistency
            scope_key = (instance_scope.project_name, instance_scope.tenant_id)
            scope_map[scope_key] = instance_scope
            self._parent_scope = None
        elif isinstance(instance_scope, OpenStackUnscoped):
            scope_map.update(instance_scope.project_scope_map)
            self._parent_scope = instance_scope

        return scope_map

    def check(self, instance):
        # have we been backed off
        if not self.should_run(instance):
            self.log.info('Skipping run due to exponential backoff in effect')
            return

        custom_tags = instance.get("tags", [])
        if custom_tags is None:
            custom_tags = []
        try:
            split_hostname_on_first_period = is_affirmative(instance.get('split_hostname_on_first_period', False))
            scope_map = self.get_scope_map(instance)

            #  The scopes we iterate over should all be OpenStackProjectScope
            #  instances
            projects = []
            for _, scope in scope_map.iteritems():
                # Store the scope on the object so we don't have to keep passing it around
                self._current_scope = scope

                self._send_api_service_checks(scope, custom_tags)

                collect_all_projects = is_affirmative(instance.get("collect_all_projects", False))
                collect_all_tenants = is_affirmative(instance.get('collect_all_tenants', False))

                self.log.debug("Running check with credentials: \n")
                self.log.debug("Nova Url: %s", self.get_nova_endpoint())
                self.log.debug("Neutron Url: %s", self.get_neutron_endpoint())

                # Restrict monitoring to this (host, hypervisor, project)
                # and it's guest servers

                hyp = self.get_local_hypervisor()

                project = self.get_scoped_project(scope)

                if collect_all_projects or project is None:
                    scope_projects = self.get_all_projects(scope)
                    if scope_projects:
                        projects.extend(scope_projects)
                else:
                    projects.append(project)

                # Restrict monitoring to non-excluded servers
                i_key = self._instance_key(instance)
                servers = self.get_servers_managed_by_hypervisor(
                    i_key, collect_all_tenants, split_hostname_on_first_period=split_hostname_on_first_period,
                )

                host_tags = self._get_tags_for_host(split_hostname_on_first_period=split_hostname_on_first_period)

                # Deep copy the cache so we can remove things from the Original during the iteration
                server_cache_copy = copy.deepcopy(self.server_details_by_id)

                for server in server_cache_copy:
                    server_tags = copy.deepcopy(custom_tags)
                    server_tags.append("nova_managed_server")

                    if scope.tenant_id:
                        server_tags.append("tenant_id:%s" % scope.tenant_id)

                    self.external_host_tags[server] = host_tags
                    self.get_stats_for_single_server(servers[server], tags=server_tags)

                if hyp:
                    self.get_stats_for_single_hypervisor(hyp, instance, host_tags=host_tags, custom_tags=custom_tags)
                else:
                    self.warning(
                        "Couldn't get hypervisor to monitor for host: %s"
                        % self.get_my_hostname(split_hostname_on_first_period=split_hostname_on_first_period)
                    )

            # get stats from all projects
            for project in projects:
                self.get_stats_for_single_project(project, custom_tags)

            # For now, monitor all networks
            self.get_network_stats(custom_tags)

            if set_external_tags is not None:
                set_external_tags(self.get_external_host_tags())

        except IncompleteConfig as e:
            if isinstance(e, IncompleteAuthScope):
                self.warning(
                    """Please specify the auth scope via the `auth_scope` variable in your init_config.\n
                             The auth_scope should look like: \n
                            {'project': {'name': 'my_project', 'domain': {'id': 'my_domain_id'}}}\n
                            OR\n
                            {'project': {'id': 'my_project_id'}}
                             """
                )
            elif isinstance(e, IncompleteIdentity):
                self.warning(
                    "Please specify the user via the `user` variable in your init_config.\n"
                    + "This is the user you would use to authenticate with Keystone v3 via password auth.\n"
                    + "The user should look like:"
                    + "{'password': 'my_password', 'name': 'my_name', 'domain': {'id': 'my_domain_id'}}"
                )
            else:
                self.warning("Configuration Incomplete! Check your openstack.yaml file")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code >= 500:
                # exponential backoff
                self.do_backoff(instance)
                self.warning("There were some problems reaching the nova API - applying exponential backoff")
            else:
                self.warning("Error reaching nova API")

            return
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # exponential backoff
            self.do_backoff(instance)
            self.warning("There were some problems reaching the nova API - applying exponential backoff")
            return

        self.reset_backoff(instance)

    # Local Info accessors
    def get_local_hypervisor(self):
        """
        Returns the hypervisor running on this host, and assumes a 1-1 between host and hypervisor
        """
        # Look up hypervisors available filtered by my hostname
        host = self.get_my_hostname()
        hyp = self.get_all_hypervisor_ids(filter_by_host=host)
        if hyp:
            return hyp[0]

    def get_all_projects(self, scope):
        """
        Returns all projects in the domain
        """
        url = "{0}/{1}/{2}".format(self.keystone_server_url, DEFAULT_KEYSTONE_API_VERSION, "projects")
        headers = {'X-Auth-Token': scope.auth_token}
        try:
            r = self._make_request_with_auth_fallback(url, headers)
            return r['projects']

        except Exception as e:
            self.warning('Unable to get projects: {0}'.format(str(e)))
            raise e

    def get_scoped_project(self, project_auth_scope):
        """
        Returns the project that this instance of the check is scoped to
        """

        filter_params = {}
        url = "{0}/{1}/{2}".format(self.keystone_server_url, DEFAULT_KEYSTONE_API_VERSION, "projects")
        if project_auth_scope.tenant_id:
            if project_auth_scope.project_name:
                return {"id": project_auth_scope.tenant_id, "name": project_auth_scope.project_name}

            url = "{}/{}".format(url, project_auth_scope.tenant_id)
        else:
            filter_params = {"name": project_auth_scope.project_name, "domain_id": project_auth_scope.domain_id}

        headers = {'X-Auth-Token': project_auth_scope.auth_token}

        try:
            project_details = self._make_request_with_auth_fallback(url, headers, params=filter_params)
            if filter_params:
                assert len(project_details["projects"]) == 1, "Non-unique project credentials"

                # Set the tenant_id so we won't have to fetch it next time
                project_auth_scope.tenant_id = project_details["projects"][0].get("id")
                return project_details["projects"][0]
            else:
                project_auth_scope.project_name = project_details["project"]["name"]
                return project_details["project"]

        except Exception as e:
            self.warning('Unable to get the project details: {0}'.format(str(e)))
            raise e

    def get_my_hostname(self, split_hostname_on_first_period=False):
        """
        Returns a best guess for the hostname registered with OpenStack for this host
        """

        hostname = self.init_config.get("os_host") or self.hostname
        if split_hostname_on_first_period:
            hostname = hostname.split('.')[0]

        return hostname

    def get_servers_managed_by_hypervisor(self, i_key, collect_all_tenants, split_hostname_on_first_period=False):
        servers = self.get_all_servers(
            i_key, collect_all_tenants,
            filter_by_host=self.get_my_hostname(split_hostname_on_first_period=split_hostname_on_first_period)
        )
        if self.exclude_server_id_rules:
            # Filter out excluded servers
            for exclude_id_rule in self.exclude_server_id_rules:
                for server_id in servers.keys():
                    if re.match(exclude_id_rule, server_id):
                        del self.server_details_by_id[server_id]

        return self.server_details_by_id

    def _get_tags_for_host(self, split_hostname_on_first_period=False):
        hostname = self.get_my_hostname(split_hostname_on_first_period=split_hostname_on_first_period)
        tags = []
        if hostname in self._get_and_set_aggregate_list():
            tags.append('aggregate:{0}'.format(self._aggregate_list[hostname]['aggregate']))
            # Need to check if there is a value for availability_zone
            # because it is possible to have an aggregate without an AZ
            if self._aggregate_list[hostname]['availability_zone']:
                tags.append('availability_zone:{0}'.format(self._aggregate_list[hostname]['availability_zone']))
        else:
            self.log.info('Unable to find hostname %s in aggregate list. Assuming this host is unaggregated', hostname)

        return tags

    # For attaching tags to hosts that are not the host running the agent

    def get_external_host_tags(self):
        """ Returns a list of tags for every guest server that is detected by the OpenStack
        integration.
        List of pairs (hostname, list_of_tags)
        """
        self.log.debug("Collecting external_host_tags now")
        external_host_tags = []
        for k, v in self.external_host_tags.iteritems():
            external_host_tags.append((k, {SOURCE_TYPE: v}))

        self.log.debug("Sending external_host_tags: %s", external_host_tags)
        return external_host_tags
