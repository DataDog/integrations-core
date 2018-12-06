# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
import copy
import requests

from six import iteritems
from datetime import datetime, timedelta

from datadog_checks.checks import AgentCheck
from datadog_checks.config import is_affirmative
from datadog_checks.utils.common import pattern_filter
from datadog_checks.utils.tracing import traced

from .scopes import ScopeFetcher
from .api import ComputeApi, NeutronApi, KeystoneApi
from .settings import DEFAULT_API_REQUEST_TIMEOUT
from .utils import get_instance_name
from .retry import BackOffRetry
from .exceptions import (InstancePowerOffFailure, IncompleteConfig, IncompleteIdentity, MissingNovaEndpoint,
                         MissingNeutronEndpoint, KeystoneUnreachable, AuthenticationNeeded)


try:
    # Agent >= 6.0: the check pushes tags invoking `set_external_tags`
    from datadog_agent import set_external_tags
except ImportError:
    # Agent < 6.0: the Agent pulls tags invoking `OpenStackControllerCheck.get_external_host_tags`
    set_external_tags = None


SOURCE_TYPE = 'openstack'
DEFAULT_PAGINATED_SERVER_LIMIT = 1000

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

SERVER_FIELDS_REQ = [
    'server_id',
    'state',
    'server_name',
    'hypervisor_hostname',
    'tenant_id',
]


class OpenStackControllerCheck(AgentCheck):
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
        super(OpenStackControllerCheck, self).__init__(name, init_config, agentConfig, instances)
        self.keystone_server_url = init_config.get("keystone_server_url")
        if not self.keystone_server_url:
            raise IncompleteConfig()
        self.proxy_config = self.get_instance_proxy(init_config, self.keystone_server_url)

        self.ssl_verify = is_affirmative(init_config.get("ssl_verify", True))

        self.paginated_server_limit = init_config.get('paginated_server_limit') or DEFAULT_PAGINATED_SERVER_LIMIT
        self.request_timeout = init_config.get('request_timeout') or DEFAULT_API_REQUEST_TIMEOUT

        exclude_network_id_patterns = set(init_config.get('exclude_network_ids', []))
        self.exclude_network_id_rules = [re.compile(ex) for ex in exclude_network_id_patterns]
        exclude_server_id_patterns = set(init_config.get('exclude_server_ids', []))
        self.exclude_server_id_rules = [re.compile(ex) for ex in exclude_server_id_patterns]
        include_project_name_patterns = set(init_config.get('whitelist_project_names', []))
        self.include_project_name_rules = [re.compile(ex) for ex in include_project_name_patterns]
        exclude_project_name_patterns = set(init_config.get('blacklist_project_names', []))
        self.exclude_project_name_rules = [re.compile(ex) for ex in exclude_project_name_patterns]

        self._keystone_api = None
        self._compute_api = None
        self._neutron_api = None

        self._backoff = BackOffRetry()

        # Mapping of check instances to associated OpenStackScope
        self.instance_scopes_cache = {}

        # Current instance and project authentication scopes
        self.instance_scope = None

        # Hypervisor names cache
        self.hypervisor_name_cache = {}

        # Cache some things between runs for values that change rarely
        self._aggregate_list = None

        # Mapping of Nova-managed servers to tags
        self.external_host_tags = {}

        # ISO8601 date time: used to filter the call to get the list of nova servers
        self.changes_since_time = {}

        # Ex: server_details_by_id = {
        #   UUID: {UUID: <value>, etc}
        #   1: {id: 1, name: hostA},
        #   2: {id: 2, name: hostB}
        # }
        self.server_details_by_id = {}

    def delete_instance_scope(self):
        for instance_name, scope in list(iteritems(self.instance_scopes_cache)):
            if scope is self.instance_scope:
                self.log.debug("Deleting instance scope for instance: %s", instance_name)
                del self.instance_scopes_cache[instance_name]

    def get_instance_scope(self, instance):
        instance_name = get_instance_name(instance)
        self.log.debug("Getting scope for instance %s", instance_name)
        return self.instance_scopes_cache[instance_name]

    def set_scopes_cache(self, instance, scope):
        instance_name = get_instance_name(instance)
        self.log.debug("Setting scope for instance %s", instance_name)
        self.instance_scopes_cache[instance_name] = scope

    def get_project_scopes(self, instance):
        instance_scope = self.get_instance_scope(instance)
        project_scopes = copy.deepcopy(instance_scope.project_scopes)
        return project_scopes

    def get_network_stats(self, tags):
        """
        Collect stats for all reachable networks
        """
        # FIXME: (aaditya) Check all networks defaults to true
        # until we can reliably assign agents to networks to monitor
        if is_affirmative(self.init_config.get('check_all_networks', True)):
            all_network_ids = set(self.get_network_ids())

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

    def get_stats_for_single_network(self, network_id, tags):
        net_details = self.get_network_details(network_id)
        service_check_tags = ['network:{}'.format(network_id)] + tags

        network_name = net_details.get('network', {}).get('name')
        if network_name:
            service_check_tags.append('network_name:{}'.format(network_name))

        tenant_id = net_details.get('network', {}).get('tenant_id')
        if tenant_id:
            service_check_tags.append('tenant_id:{}'.format(tenant_id))

        if net_details.get('network', {}).get('admin_state_up'):
            self.service_check(self.NETWORK_SC, AgentCheck.OK, tags=service_check_tags)
        else:
            self.service_check(self.NETWORK_SC, AgentCheck.CRITICAL, tags=service_check_tags)

    # Compute
    def _parse_uptime_string(self, uptime):
        """ Parse u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n' """
        uptime = uptime.strip()
        load_averages = uptime[uptime.find('load average:'):].split(':')[1].strip().split(',')
        load_averages = [float(load_avg) for load_avg in load_averages]
        uptime_sec = uptime.split(',')[0]
        return {'loads': load_averages, 'uptime_sec': uptime_sec}

    def get_all_aggregate_hypervisors(self):
        hypervisor_aggregate_map = {}
        try:
            aggregate_list = self.get_os_aggregates()
            for v in aggregate_list:
                for host in v['hosts']:
                    hypervisor_aggregate_map[host] = {
                        'aggregate': v['name'],
                        'availability_zone': v['availability_zone'],
                    }

        except Exception as e:
            self.warning('Unable to get the list of aggregates: {}'.format(e))
            raise e

        return hypervisor_aggregate_map

    def get_uptime_for_single_hypervisor(self, hyp_id):
        uptime = self.get_os_hypervisor_uptime(hyp_id)
        return self._parse_uptime_string(uptime)

    def get_stats_for_all_hypervisors(self, instance, custom_tags=None,
                                      use_shortname=False,
                                      collect_hypervisor_load=False):
        """
        Submits stats for all hypervisors registered to this control plane
        Raises specific exceptions based on response code
        """
        resp = self.get_os_hypervisors_detail()
        hypervisors = resp.get('hypervisors', [])
        for hyp in hypervisors:
            self.get_stats_for_single_hypervisor(hyp, instance, custom_tags=custom_tags,
                                                 use_shortname=use_shortname,
                                                 collect_hypervisor_load=collect_hypervisor_load)

        if not hypervisors:
            self.log.warn("Unable to collect any hypervisors from Nova response: {}".format(resp))

    def get_stats_for_single_hypervisor(self, hyp, instance, custom_tags=None,
                                        use_shortname=False,
                                        collect_hypervisor_load=False):
        hyp_hostname = hyp.get('hypervisor_hostname')
        self.hypervisor_name_cache[get_instance_name(instance)] = hyp_hostname
        custom_tags = custom_tags or []
        tags = [
            'hypervisor:{}'.format(hyp_hostname),
            'hypervisor_id:{}'.format(hyp['id']),
            'virt_type:{}'.format(hyp['hypervisor_type']),
            'status:{}'.format(hyp['status']),
        ]
        host_tags = self._get_host_aggregate_tag(hyp_hostname, use_shortname=use_shortname)
        tags.extend(host_tags)
        tags.extend(custom_tags)
        service_check_tags = list(custom_tags)

        # This makes a request per hypervisor and only sends hypervisor_load 1/5/15
        # Disable this by default for higher performance in a large environment
        # If the Agent is installed on the hypervisors, system.load.1/5/15 is available
        if collect_hypervisor_load:
            try:
                uptime = self.get_uptime_for_single_hypervisor(hyp['id'])
            except Exception as e:
                self.warning('Unable to get uptime for hypervisor {}: {}'.format(hyp['id'], e))
                uptime = {}

            load_averages = uptime.get("loads")
            if load_averages and len(load_averages) == 3:
                for i, avg in enumerate([1, 5, 15]):
                    self.gauge('openstack.nova.hypervisor_load.{}'.format(avg), load_averages[i], tags=tags)
            else:
                self.log.debug("Load Averages didn't return expected values: {}".format(load_averages))

        hyp_state = hyp.get('state', None)

        if not hyp_state:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.UNKNOWN, hostname=hyp_hostname, tags=service_check_tags)
        elif hyp_state != self.HYPERVISOR_STATE_UP:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.CRITICAL, hostname=hyp_hostname, tags=service_check_tags)
        else:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.OK, hostname=hyp_hostname, tags=service_check_tags)

        for label, val in iteritems(hyp):
            if label in NOVA_HYPERVISOR_METRICS:
                metric_label = "openstack.nova.{}".format(label)
                self.gauge(metric_label, val, tags=tags)

    # Get all of the server IDs and their metadata and cache them
    # After the first run, we will only get servers that have changed state since the last collection run
    def get_all_servers(self, project_auth_token, instance_name):
        query_params = {}

        # If we don't have a timestamp for this instance, default to None
        if instance_name in self.changes_since_time:
            query_params['changes-since'] = self.changes_since_time.get(instance_name)

        # Note this query param specifically requires admin user rights
        query_params["all_tenants"] = True
        servers = []

        # Get a list of active servers using pagination
        query_params['status'] = 'ACTIVE'
        query_params['limit'] = self.paginated_server_limit
        resp = self.get_servers_detail(query_params, timeout=self.request_timeout)
        servers.extend(resp)
        # Avoid the extra request since we know we're done when the response has anywhere between
        # 0 and paginated_server_limit servers
        while len(resp) == self.paginated_server_limit:
            query_params['marker'] = resp[-1]['id']
            resp = self.get_servers_detail(query_params, timeout=self.request_timeout)
            servers.extend(resp)

        query_params['limit'] = None
        query_params['marker'] = None

        # Don't collect Deleted or Shut off VMs on the first run:
        if instance_name in self.changes_since_time:

            # Get a list of deleted serversTimestamp used to filter the call to get the list
            # Need to have admin perms for this to take affect
            query_params['deleted'] = 'true'
            del query_params['status']
            resp = self.get_servers_detail(query_params)
            servers.extend(resp)

            query_params['deleted'] = 'false'
            # Get a list of shut off servers
            query_params['status'] = 'SHUTOFF'
            resp = self.get_servers_detail(query_params)
            servers.extend(resp)

        self.changes_since_time[instance_name] = datetime.utcnow().isoformat()

        for server in servers:
            new_server = dict()
            new_server['server_id'] = server.get('id')
            new_server['state'] = server.get('status')
            new_server['server_name'] = server.get('name')
            new_server['hypervisor_hostname'] = server.get('OS-EXT-SRV-ATTR:hypervisor_hostname')
            new_server['tenant_id'] = server.get('tenant_id')
            new_server['availability_zone'] = server.get('OS-EXT-AZ:availability_zone')

            # Confirm that the new server has all the required fields
            if not all(new_server[key] is not None for key in SERVER_FIELDS_REQ):
                self.log.debug(
                    "Server {} has None for one of the required keys."
                    "Not collecting server metrics for this server."
                    .format(new_server)
                )
                continue

            # Update our cached list of servers
            if (new_server['server_id'] not in self.server_details_by_id and
                    new_server['state'] in DIAGNOSTICABLE_STATES):
                self.log.debug("Adding server to cache: %s", new_server)
                # The project may not exist if the server isn't in an active state
                # Query for the project name here to avoid 404s
                # If the project name conversion fails, we won't add this server
                new_server['project_name'] = self.get_project_name_from_id(project_auth_token, new_server['tenant_id'])
                if new_server['project_name']:
                    self.server_details_by_id[new_server['server_id']] = new_server
            elif new_server['server_id'] in self.server_details_by_id and new_server['state'] in REMOVED_STATES:
                self.log.debug("Removing server from cache: %s", new_server)
                try:
                    del self.server_details_by_id[new_server['server_id']]
                except KeyError:
                    self.log.debug("Server: %s has already been removed from the cache", new_server['server_id'])

    def filter_excluded_servers(self):
        proj_list = set([])
        if self.exclude_server_id_rules:
            # Filter out excluded servers
            for exclude_id_rule in self.exclude_server_id_rules:
                for server_id in list(self.server_details_by_id):
                    if re.match(exclude_id_rule, server_id):
                        del self.server_details_by_id[server_id]

        for _, server in iteritems(self.server_details_by_id):
            proj_list.add(server.get('project_name'))

        projects_filtered = pattern_filter(
            proj_list,
            whitelist=self.include_project_name_rules,
            blacklist=self.exclude_project_name_rules
        )

        self.server_details_by_id = {
                sid: server for (sid, server)
                in iteritems(self.server_details_by_id)
                if server.get('project_name') in projects_filtered
        }

    def get_stats_for_single_server(self, server_details, tags=None, use_shortname=False):
        def _is_valid_metric(label):
            return label in NOVA_SERVER_METRICS or any(seg in label for seg in NOVA_SERVER_INTERFACE_SEGMENTS)

        def _is_interface_metric(label):
            return any(seg in label for seg in NOVA_SERVER_INTERFACE_SEGMENTS)

        hypervisor_hostname = server_details.get('hypervisor_hostname')
        host_tags = self._get_host_aggregate_tag(hypervisor_hostname, use_shortname=use_shortname)
        host_tags.append('availability_zone:{}'.format(server_details.get('availability_zone', 'NA')))
        self.external_host_tags[server_details.get('server_name')] = host_tags

        server_id = server_details.get('server_id')
        server_name = server_details.get('server_name')
        hypervisor_hostname = server_details.get('hypervisor_hostname')
        project_name = server_details.get('project_name')

        server_stats = {}
        try:
            server_stats = self.get_server_diagnostics(server_id)
        except InstancePowerOffFailure:  # 409 response code came back fro nova
            self.log.debug("Server %s is powered off and cannot be monitored", server_id)
            del self.server_details_by_id[server_id]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.log.debug("Server %s is not in an ACTIVE state and cannot be monitored, %s", server_id, e)
                del self.server_details_by_id[server_id]
            else:
                self.log.debug("Received HTTP Error when reaching the nova endpoint")
                return
        except Exception as e:
            self.warning("Unknown error when monitoring %s : %s" % (server_id, e))
            return

        if server_stats:
            tags = tags or []
            if project_name:
                tags.append("project_name:{}".format(project_name))
            if hypervisor_hostname:
                tags.append("hypervisor:{}".format(hypervisor_hostname))
            if server_name:
                tags.append("server_name:{}".format(server_name))

            # microversion pre 2.48
            for m in server_stats:
                if _is_interface_metric(m):
                    # Example of interface metric
                    # tap123456_rx_errors
                    metric_pre = re.split("(_rx|_tx)", m)
                    interface = "interface:{}".format(metric_pre[0])
                    self.gauge(
                        "openstack.nova.server.{}{}".format(metric_pre[1].replace("_", ""), metric_pre[2]),
                        server_stats[m],
                        tags=tags+host_tags+[interface],
                        hostname=server_id,
                    )
                elif _is_valid_metric(m):
                    self.gauge(
                        "openstack.nova.server.{}".format(m.replace("-", "_")),
                        server_stats[m],
                        tags=tags+host_tags,
                        hostname=server_id,
                    )

    def get_stats_for_single_project(self, project, tags=None):
        def _is_valid_metric(label):
            return label in PROJECT_METRICS

        if tags is None:
            tags = []

        server_tags = copy.deepcopy(tags)
        project_name = project.get('name')
        project_id = project.get('id')

        self.log.debug("Collecting metrics for project. name: {} id: {}".format(project_name, project['id']))
        server_stats = self.get_project_limits(project['id'])
        server_tags.append('tenant_id:{}'.format(project_id))

        if project_name:
            server_tags.append('project_name:{}'.format(project_name))

        try:
            for st in server_stats:
                if _is_valid_metric(st):
                    metric_key = PROJECT_METRICS[st]
                    self.gauge(
                        "openstack.nova.limits.{}".format(metric_key),
                        server_stats[st],
                        tags=server_tags,
                    )
        except KeyError:
            self.log.warn("Unexpected response, not submitting limits metrics for project id".format(project['id']))

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

    def _send_api_service_checks(self, project_scope, tags):
        # Nova
        headers = {"X-Auth-Token": project_scope.auth_token}
        try:
            self.log.debug("Nova endpoint: {}".format(project_scope.nova_endpoint))
            requests.get(
                project_scope.nova_endpoint,
                headers=headers,
                verify=self.ssl_verify,
                timeout=DEFAULT_API_REQUEST_TIMEOUT,
                proxies=self.proxy_config,
            )
            self.service_check(
                self.COMPUTE_API_SC,
                AgentCheck.OK,
                tags=["keystone_server: {}".format(self.keystone_server_url)] + tags,
            )
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self.service_check(
                self.COMPUTE_API_SC,
                AgentCheck.CRITICAL,
                tags=["keystone_server: {}".format(self.keystone_server_url)] + tags,
            )

        # Neutron
        try:
            self.log.debug("Neutron endpoint: {}".format(project_scope.neutron_endpoint))
            requests.get(
                project_scope.neutron_endpoint,
                headers=headers,
                verify=self.ssl_verify,
                timeout=DEFAULT_API_REQUEST_TIMEOUT,
                proxies=self.proxy_config,
            )
            self.service_check(
                self.NETWORK_API_SC,
                AgentCheck.OK,
                tags=["keystone_server: {}".format(self.keystone_server_url)] + tags,
            )
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self.service_check(
                self.NETWORK_API_SC,
                AgentCheck.CRITICAL,
                tags=["keystone_server: {}".format(self.keystone_server_url)] + tags,
            )

    def init_instance_scope_cache(self, instance):
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
            instance_scope = self.get_instance_scope(instance)
        except KeyError:
            # We are missing the entire instance scope either because it is the first time we initialize it or because
            # authentication previously failed and got removed from the cache
            # Let's populate it now
            try:
                self.log.debug("Fetch scope for instance {}".format(instance))
                instance_scope = ScopeFetcher.from_config(self.log, self.init_config, instance,
                                                          proxy_config=self.proxy_config)
                # Set keystone api with proper token
                self._keystone_api = KeystoneApi(self.log, self.ssl_verify, self.proxy_config,
                                                 self.keystone_server_url, instance_scope.auth_token)
                self.service_check(
                    self.IDENTITY_API_SC,
                    AgentCheck.OK,
                    tags=["keystone_server: {}".format(self.keystone_server_url)] + custom_tags,
                )
            except KeystoneUnreachable as e:
                self.log.warning("The agent could not contact the specified identity server at {} . "
                                 "Are you sure it is up at that address?".format(self.keystone_server_url))
                self.log.debug("Problem grabbing auth token: %s", e)
                self.service_check(
                    self.IDENTITY_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server: {}".format(self.keystone_server_url)] + custom_tags,
                )

                # If Keystone is down/unreachable, we default the
                # Nova and Neutron APIs to UNKNOWN since we cannot access the service catalog
                self.service_check(
                    self.NETWORK_API_SC,
                    AgentCheck.UNKNOWN,
                    tags=["keystone_server: {}".format(self.keystone_server_url)] + custom_tags,
                )
                self.service_check(
                    self.COMPUTE_API_SC,
                    AgentCheck.UNKNOWN,
                    tags=["keystone_server: {}".format(self.keystone_server_url)] + custom_tags,
                )

            except MissingNovaEndpoint as e:
                self.warning("The agent could not find a compatible Nova endpoint in your service catalog!")
                self.log.debug("Failed to get nova endpoint for response catalog: %s", e)
                self.service_check(
                    self.COMPUTE_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server: {}".format(self.keystone_server_url)] + custom_tags,
                )

            except MissingNeutronEndpoint:
                self.warning("The agent could not find a compatible Neutron endpoint in your service catalog!")
                self.service_check(
                    self.NETWORK_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server: {}".format(self.keystone_server_url)] + custom_tags,
                )

        if not instance_scope:
            # Fast fail in the absence of an instance_scope
            raise IncompleteConfig()

        self.set_scopes_cache(instance, instance_scope)
        return instance_scope

    @traced
    def check(self, instance):
        # have we been backed off
        if not self._backoff.should_run(instance):
            self.log.info('Skipping run due to exponential backoff in effect')
            return
        custom_tags = instance.get("tags", [])
        collect_limits_from_all_projects = is_affirmative(instance.get('collect_limits_from_all_projects', True))
        collect_hypervisor_load = is_affirmative(instance.get('collect_hypervisor_load', False))
        use_shortname = is_affirmative(instance.get('use_shortname', False))

        projects = {}
        try:
            instance_name = get_instance_name(instance)

            # Authenticate and add the instance scope to instance_scopes cache
            self.init_instance_scope_cache(instance)

            # Init instance_scope
            self.instance_scope = self.get_instance_scope(instance)
            project_scopes = self.get_project_scopes(instance)
            for _, project_scope in iteritems(project_scopes):
                self._send_api_service_checks(project_scope, custom_tags)

                self.log.debug("Running check with credentials: \n")
                self.log.debug("Nova Url: %s", project_scope.nova_endpoint)
                self.log.debug("Neutron Url: %s", project_scope.neutron_endpoint)
                self._neutron_api = NeutronApi(self.log,
                                               self.ssl_verify,
                                               self.proxy_config,
                                               project_scope.neutron_endpoint,
                                               project_scope.auth_token)
                self._compute_api = ComputeApi(self.log,
                                               self.ssl_verify,
                                               self.proxy_config,
                                               project_scope.nova_endpoint,
                                               project_scope.auth_token)

                project = self.get_and_update_project_details(project_scope)
                if project and project.get('name'):
                    projects[project.get('name')] = project

                if collect_limits_from_all_projects:
                    scope_projects = self.get_projects(project_scope.auth_token)
                    if scope_projects:
                        for proj in scope_projects:
                            projects[proj['name']] = proj

                filtered_projects = pattern_filter([p for p in projects],
                                                   whitelist=self.include_project_name_rules,
                                                   blacklist=self.exclude_project_name_rules)

                projects = {name: v for (name, v) in iteritems(projects) if name in filtered_projects}

                for name, project in iteritems(projects):
                    self.get_stats_for_single_project(project, custom_tags)

                self.get_stats_for_all_hypervisors(instance, custom_tags=custom_tags,
                                                   use_shortname=use_shortname,
                                                   collect_hypervisor_load=collect_hypervisor_load)

                # This updates the server cache directly
                self.get_all_servers(project_scope.auth_token, instance_name)
                self.filter_excluded_servers()

                # Deep copy the cache so we can remove things from the Original during the iteration
                # Allows us to remove bad servers from the cache if need be
                server_cache_copy = copy.deepcopy(self.server_details_by_id)

                self.log.debug("Fetch stats from %s server(s)" % len(server_cache_copy))
                for server in server_cache_copy:
                    server_tags = copy.deepcopy(custom_tags)
                    server_tags.append("nova_managed_server")

                    self.get_stats_for_single_server(server_cache_copy[server], tags=server_tags,
                                                     use_shortname=use_shortname)

            # For now, monitor all networks
            self.get_network_stats(custom_tags)

            if set_external_tags is not None:
                set_external_tags(self.get_external_host_tags())

        except IncompleteConfig as e:
            if isinstance(e, IncompleteIdentity):
                self.warning(
                    "Please specify the user via the `user` variable in your init_config.\n"
                    + "This is the user you would use to authenticate with Keystone v3 via password auth.\n"
                    + "The user should look like:"
                    + "{'password': 'my_password', 'name': 'my_name', 'domain': {'id': 'my_domain_id'}}"
                )
            else:
                self.warning("Configuration Incomplete! Check your openstack.yaml file")
        except AuthenticationNeeded:
            # Delete the scope, we'll populate a new one on the next run for this instance
            self.delete_instance_scope()
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code < 500:
                self.warning("Error reaching nova API: %s" % e)
            else:
                # exponential backoff
                self.do_backoff(instance)
                return

        self._backoff.reset_backoff(instance)

    def do_backoff(self, instance):
        backoff_interval, retries = self._backoff.do_backoff(instance)

        instance_name = get_instance_name(instance)
        tags = instance.get('tags', [])
        hypervisor_name = self.hypervisor_name_cache.get(instance_name)
        if hypervisor_name:
            tags.extend("hypervisor:{}".format(hypervisor_name))

        self.gauge("openstack.backoff.interval", backoff_interval, tags=tags)
        self.gauge("openstack.backoff.retries", retries, tags=tags)
        self.warning("There were some problems reaching the nova API - applying exponential backoff")

    def get_and_update_project_details(self, project_scope):
        """
        Returns the project that this instance of the check is scoped to
        """
        try:
            project_details, tenant_id, project_name = self.get_project_details(
                project_scope.tenant_id,
                project_scope.name,
                project_scope.domain_id)

            # Set the tenant_id so we won't have to fetch it next time
            if project_scope.tenant_id:
                project_scope.tenant_id = tenant_id
            if project_scope.name:
                project_scope.name = project_name
            return project_details

        except Exception as e:
            self.warning('Unable to get the project details: {}'.format(e))
            raise e

    def _get_host_aggregate_tag(self, hyp_hostname, use_shortname=False):
        tags = []
        hyp_hostname = hyp_hostname.split('.')[0] if use_shortname else hyp_hostname
        if hyp_hostname in self._get_and_set_aggregate_list():
            tags.append('aggregate:{}'.format(self._aggregate_list[hyp_hostname].get('aggregate', "unknown")))
            # Need to check if there is a value for availability_zone
            # because it is possible to have an aggregate without an AZ
            try:
                if self._aggregate_list[hyp_hostname].get('availability_zone'):
                    tags.append('availability_zone:{}'
                                .format(self._aggregate_list[hyp_hostname]['availability_zone']))
            except KeyError:
                self.log.debug('Unable to get the availability_zone for hypervisor: {}'.format(hyp_hostname))
        else:
            self.log.info('Unable to find hostname %s in aggregate list. Assuming this host is unaggregated',
                          hyp_hostname)

        return tags

    # For attaching tags to hosts that are not the host running the agent
    def get_external_host_tags(self):
        """ Returns a list of tags for every guest server that is detected by the OpenStack
        integration.
        List of pairs (hostname, list_of_tags)
        """
        self.log.debug("Collecting external_host_tags now")
        external_host_tags = []
        for k, v in iteritems(self.external_host_tags):
            external_host_tags.append((k, {SOURCE_TYPE: v}))

        self.log.debug("Sending external_host_tags: %s", external_host_tags)
        return external_host_tags

    # Nova Proxy methods
    def get_os_hypervisor_uptime(self, hyp_id):
        return self._compute_api.get_os_hypervisor_uptime(hyp_id)

    def get_os_aggregates(self):
        return self._compute_api.get_os_aggregates()

    def get_os_hypervisors_detail(self):
        return self._compute_api.get_os_hypervisors_detail()

    def get_servers_detail(self, query_params, timeout=None):
        return self._compute_api.get_servers_detail(query_params, timeout=timeout)

    def get_server_diagnostics(self, server_id):
        return self._compute_api.get_server_diagnostics(server_id)

    def get_project_limits(self, tenant_id):
        return self._compute_api.get_project_limits(tenant_id)

    # Keystone Proxy Methods
    def get_projects(self, project_token):
        return self._keystone_api.get_projects(project_token)

    def get_project_name_from_id(self, project_token, project_id):
        return self._keystone_api.get_project_name_from_id(project_token, project_id)

    def get_project_details(self, tenant_id, project_name, domain_id):
        return self._keystone_api.get_project_details(tenant_id, project_name, domain_id)

    # Neutron Proxy Methods
    def get_network_ids(self):
        return self._neutron_api.get_network_ids()

    def get_network_details(self, network_id):
        return self._neutron_api.get_network_details(network_id)
