# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import re
from collections import defaultdict
from datetime import datetime

import requests
from openstack.config.loader import OpenStackConfig
from six import iteritems, itervalues

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.common import pattern_filter
from datadog_checks.base.utils.tracing import traced

from .api import ApiFactory
from .exceptions import (
    AuthenticationNeeded,
    IncompleteConfig,
    IncompleteIdentity,
    InstancePowerOffFailure,
    KeystoneUnreachable,
    MissingNeutronEndpoint,
    MissingNovaEndpoint,
)
from .retry import BackOffRetry

SOURCE_TYPE = 'openstack'

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

SERVER_FIELDS_REQ = ['server_id', 'state', 'server_name', 'hypervisor_hostname', 'tenant_id']


class OpenStackControllerCheck(AgentCheck):
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

    HTTP_CONFIG_REMAPPER = {'ssl_verify': {'name': 'tls_verify'}, 'request_timeout': {'name': 'timeout'}}

    def __init__(self, name, init_config, instances):
        super(OpenStackControllerCheck, self).__init__(name, init_config, instances)
        # We cache all api instances.
        # This allows to cache connection if the underlying implementation support it
        # Ex: _api = <api object>
        self._api = None

        # BackOffRetry supports multiple instances
        self._backoff = BackOffRetry()

        # Ex: servers_cache = {
        #   'servers': {<server_id>: <server_metadata>},
        #   'changes_since': <ISO8601 date time>
        # }
        self.servers_cache = {}

        # Current instance name
        self.instance_name = None
        # Mapping of Nova-managed servers to tags for current instance name
        self.external_host_tags = {}

    def delete_api_cache(self):
        self._api = None

    def collect_networks_metrics(self, tags, network_ids, exclude_network_id_rules):
        """
        Collect stats for all reachable networks
        """
        networks = self.get_networks()
        filtered_networks = []
        if not network_ids:
            # Filter out excluded networks
            filtered_networks = [
                network
                for network in networks
                if not any([re.match(exclude_id, network.get('id')) for exclude_id in exclude_network_id_rules])
            ]
        else:
            for network in networks:
                if network.get('id') in network_ids:
                    filtered_networks.append(network)

        for network in filtered_networks:
            network_id = network.get('id')
            service_check_tags = ['network:{}'.format(network_id)] + tags

            network_name = network.get('name')
            if network_name:
                service_check_tags.append('network_name:{}'.format(network_name))

            tenant_id = network.get('tenant_id')
            if tenant_id:
                service_check_tags.append('tenant_id:{}'.format(tenant_id))

            if network.get('admin_state_up'):
                self.service_check(self.NETWORK_SC, AgentCheck.OK, tags=service_check_tags)
            else:
                self.service_check(self.NETWORK_SC, AgentCheck.CRITICAL, tags=service_check_tags)

    # Compute
    def _parse_uptime_string(self, uptime):
        """ Parse u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n' """
        uptime = uptime.strip()
        load_averages = uptime[uptime.find('load average:') :].split(':')[1].strip().split(',')
        load_averages = [float(load_avg) for load_avg in load_averages]
        return load_averages

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
            self.warning('Unable to get the list of aggregates: %s', e)
            raise e

        return hypervisor_aggregate_map

    def get_loads_for_single_hypervisor(self, hyp_id):
        uptime = self.get_os_hypervisor_uptime(hyp_id)
        return self._parse_uptime_string(uptime)

    def collect_hypervisors_metrics(
        self,
        servers,
        custom_tags=None,
        use_shortname=False,
        collect_hypervisor_metrics=True,
        collect_hypervisor_load=False,
    ):
        """
        Submits stats for all hypervisors registered to this control plane
        Raises specific exceptions based on response code
        """
        # Create a dictionary with hypervisor hostname as key and the list of project names as value
        hyp_project_names = defaultdict(set)
        for server in itervalues(servers):
            hypervisor_hostname = server.get('hypervisor_hostname')
            if not hypervisor_hostname:
                self.log.debug(
                    "hypervisor_hostname is None for server %s. Check that your user is an administrative users.",
                    server['server_id'],
                )
            else:
                hyp_project_names[hypervisor_hostname].add(server['project_name'])

        hypervisors = self.get_os_hypervisors_detail()
        for hyp in hypervisors:
            self.get_stats_for_single_hypervisor(
                hyp,
                hyp_project_names,
                custom_tags=custom_tags,
                use_shortname=use_shortname,
                collect_hypervisor_metrics=collect_hypervisor_metrics,
                collect_hypervisor_load=collect_hypervisor_load,
            )
        if not hypervisors:
            self.warning("Unable to collect any hypervisors from Nova response.")

    def get_stats_for_single_hypervisor(
        self,
        hyp,
        hyp_project_names,
        custom_tags=None,
        use_shortname=False,
        collect_hypervisor_metrics=True,
        collect_hypervisor_load=True,
    ):
        hyp_hostname = hyp.get('hypervisor_hostname')
        custom_tags = custom_tags or []
        tags = [
            'hypervisor:{}'.format(hyp_hostname),
            'hypervisor_id:{}'.format(hyp['id']),
            'virt_type:{}'.format(hyp['hypervisor_type']),
            'status:{}'.format(hyp['status']),
        ]

        # add hypervisor project names as tags
        project_names = hyp_project_names.get(hyp_hostname, set())
        for project_name in project_names:
            tags.append('project_name:{}'.format(project_name))

        host_tags = self._get_host_aggregate_tag(hyp_hostname, use_shortname=use_shortname)
        tags.extend(host_tags)
        tags.extend(custom_tags)
        service_check_tags = list(custom_tags)

        hyp_state = hyp.get('state', None)

        if not hyp_state:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.UNKNOWN, tags=service_check_tags)
        elif hyp_state != self.HYPERVISOR_STATE_UP:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.CRITICAL, tags=service_check_tags)
        else:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.OK, tags=service_check_tags)

        if not collect_hypervisor_metrics:
            return

        for label, val in iteritems(hyp):
            if label in NOVA_HYPERVISOR_METRICS:
                metric_label = "openstack.nova.{}".format(label)
                self.gauge(metric_label, val, tags=tags)

        # This makes a request per hypervisor and only sends hypervisor_load 1/5/15
        # Disable this by default for higher performance in a large environment
        # If the Agent is installed on the hypervisors, system.load.1/5/15 is available as a system metric
        if collect_hypervisor_load:
            try:
                load_averages = self.get_loads_for_single_hypervisor(hyp['id'])
            except Exception as e:
                self.warning('Unable to get loads averages for hypervisor %s: %s', hyp['id'], e)
                load_averages = []
            if load_averages and len(load_averages) == 3:
                for i, avg in enumerate([1, 5, 15]):
                    self.gauge('openstack.nova.hypervisor_load.{}'.format(avg), load_averages[i], tags=tags)
            else:
                self.warning("Load Averages didn't return expected values: %s", load_averages)

    def get_active_servers(self, tenant_to_name):
        query_params = {"all_tenants": True, 'status': 'ACTIVE'}
        servers = self.get_servers_detail(query_params)

        return {
            server.get('id'): self.create_server_object(server, tenant_to_name)
            for server in servers
            if tenant_to_name.get(server.get('tenant_id'))
        }

    def update_servers_cache(self, cached_servers, tenant_to_name, changes_since):
        servers = copy.deepcopy(cached_servers)

        query_params = {"all_tenants": True, 'changes-since': changes_since}
        updated_servers = self.get_servers_detail(query_params)

        # For each updated servers, we update the servers cache accordingly
        for updated_server in updated_servers:
            updated_server_status = updated_server.get('status')
            updated_server_id = updated_server.get('id')

            if updated_server_status == 'ACTIVE':
                # Add or update the cache
                if tenant_to_name.get(updated_server.get('tenant_id')):
                    servers[updated_server_id] = self.create_server_object(updated_server, tenant_to_name)
            else:
                # Remove from the cache if it exists
                if updated_server_id in servers:
                    del servers[updated_server_id]
        return servers

    def create_server_object(self, server, tenant_to_name):
        result = {
            'server_id': server.get('id'),
            'state': server.get('status'),
            'server_name': server.get('name'),
            'hypervisor_hostname': server.get('OS-EXT-SRV-ATTR:hypervisor_hostname'),
            'tenant_id': server.get('tenant_id'),
            'availability_zone': server.get('OS-EXT-AZ:availability_zone'),
            'project_name': tenant_to_name.get(server.get('tenant_id')),
        }
        # starting version 2.47, flavors infos are contained within the `servers/detail` endpoint
        # See https://developer.openstack.org/api-ref/compute/
        # ?expanded=list-servers-detailed-detail#list-servers-detailed-detail
        # TODO: Instead of relying on the structure of the response, we could use specified versions
        # provided in the config. Both have pros and cons.
        flavor = server.get('flavor', {})
        if 'id' in flavor:
            # Available until version 2.46
            result['flavor_id'] = flavor.get('id')
        if 'disk' in flavor:
            # New in version 2.47
            result['flavor'] = self.create_flavor_object(flavor)
        if not all(key in result for key in SERVER_FIELDS_REQ):
            self.warning("Server %s is missing a required field. Unable to collect all metrics for this server", result)
        return result

    # Get all of the server IDs and their metadata and cache them
    # After the first run, we will only get servers that have changed state since the last collection run
    def populate_servers_cache(self, projects, exclude_server_id_rules):
        # projects is being fetched from
        # https://developer.openstack.org/api-ref/identity/v3/?expanded=list-projects-detail#list-projects
        # It has an id (project id) and a name (project name)
        # The id is referenced as the tenant_id in other endpoints like
        # https://developer.openstack.org/api-ref/compute/?expanded=list-servers-detail#list-servers
        # as mentioned in a note:
        # "tenant_id can also be requested which is alias of project_id but that is not
        # recommended to use as that will be removed in future."
        tenant_to_name = {}
        for name, p in iteritems(projects):
            tenant_to_name[p.get('id')] = name

        cached_servers = self.servers_cache.get('servers')
        # NOTE: updated_time need to be set at the beginning of this method in order to no miss servers changes.
        changes_since = datetime.utcnow().isoformat()
        if cached_servers is None:
            updated_servers = self.get_active_servers(tenant_to_name)
        else:
            previous_changes_since = self.servers_cache.get('changes_since')
            updated_servers = self.update_servers_cache(cached_servers, tenant_to_name, previous_changes_since)

        # Filter out excluded servers
        servers = {}
        for updated_server_id, updated_server in iteritems(updated_servers):
            if not any([re.match(rule, updated_server_id) for rule in exclude_server_id_rules]):
                servers[updated_server_id] = updated_server

        # Initialize or update cache for this instance
        self.servers_cache = {'servers': servers, 'changes_since': changes_since}
        return servers

    def collect_server_diagnostic_metrics(self, server_details, tags=None, use_shortname=False):
        def _is_valid_metric(label):
            return label in NOVA_SERVER_METRICS or any(seg in label for seg in NOVA_SERVER_INTERFACE_SEGMENTS)

        def _is_interface_metric(label):
            return any(seg in label for seg in NOVA_SERVER_INTERFACE_SEGMENTS)

        tags = tags or []
        tags = copy.deepcopy(tags)
        tags.append("nova_managed_server")
        hypervisor_hostname = server_details.get('hypervisor_hostname')
        host_tags = self._get_host_aggregate_tag(hypervisor_hostname, use_shortname=use_shortname)
        host_tags.append('availability_zone:{}'.format(server_details.get('availability_zone', 'NA')))
        self.external_host_tags[server_details.get('server_name')] = host_tags

        server_id = server_details.get('server_id')
        server_name = server_details.get('server_name')
        hypervisor_hostname = server_details.get('hypervisor_hostname')
        project_name = server_details.get('project_name')

        try:
            server_stats = self.get_server_diagnostics(server_id)
        except InstancePowerOffFailure:  # 409 response code came back fro nova
            self.log.debug("Server %s is powered off and cannot be monitored", server_id)
            return
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.log.debug("Server %s is not in an ACTIVE state and cannot be monitored, %s", server_id, e)
            else:
                self.warning(
                    "Received HTTP Error when reaching the Diagnostics endpoint for server:%s, %s", e, server_name
                )
            return
        except Exception as e:
            self.warning("Unknown error when monitoring %s : %s", server_id, e)
            return

        if server_stats:
            if project_name:
                tags.append("project_name:{}".format(project_name))
            if hypervisor_hostname:
                tags.append("hypervisor:{}".format(hypervisor_hostname))
            if server_id:
                tags.append("server_id:{}".format(server_id))
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
                        tags=tags + host_tags + [interface],
                    )
                elif _is_valid_metric(m):
                    self.gauge(
                        "openstack.nova.server.{}".format(m.replace("-", "_")), server_stats[m], tags=tags + host_tags,
                    )

    def collect_project_limit(self, project, tags=None):
        # NOTE: starting from Version 3.10 (Queens)
        # We can use /v3/limits (Unified Limits API) if not experimental any more.
        def _is_valid_metric(label):
            return label in PROJECT_METRICS

        tags = tags or []

        server_tags = copy.deepcopy(tags)
        project_name = project.get('name')
        project_id = project.get('id')

        self.log.debug("Collecting metrics for project. name: %s id: %s", project_name, project['id'])
        server_stats = self.get_project_limits(project['id'])
        server_tags.append('tenant_id:{}'.format(project_id))

        if project_name:
            server_tags.append('project_name:{}'.format(project_name))

        try:
            for st in server_stats:
                if _is_valid_metric(st):
                    metric_key = PROJECT_METRICS[st]
                    self.gauge("openstack.nova.limits.{}".format(metric_key), server_stats[st], tags=server_tags)
        except KeyError:
            self.warning("Unexpected response, not submitting limits metrics for project id %s", project['id'])

    def get_flavors(self):
        query_params = {}
        flavors = self.get_flavors_detail(query_params)

        return {flavor.get('id'): self.create_flavor_object(flavor) for flavor in flavors}

    @staticmethod
    def create_flavor_object(flavor):
        return {
            'id': flavor.get('id'),
            'disk': flavor.get('disk'),
            'vcpus': flavor.get('vcpus'),
            'ram': flavor.get('ram'),
            'ephemeral': flavor.get('OS-FLV-EXT-DATA:ephemeral'),
            'swap': 0 if flavor.get('swap') == '' else flavor.get('swap'),
        }

    def collect_server_flavor_metrics(self, server_details, flavors, tags=None, use_shortname=False):
        tags = tags or []
        tags = copy.deepcopy(tags)
        tags.append("nova_managed_server")
        hypervisor_hostname = server_details.get('hypervisor_hostname')
        host_tags = self._get_host_aggregate_tag(hypervisor_hostname, use_shortname=use_shortname)
        host_tags.append('availability_zone:{}'.format(server_details.get('availability_zone', 'NA')))
        self.external_host_tags[server_details.get('server_name')] = host_tags

        server_id = server_details.get('server_id')
        server_name = server_details.get('server_name')
        hypervisor_hostname = server_details.get('hypervisor_hostname')
        project_name = server_details.get('project_name')

        flavor_id = server_details.get('flavor_id')
        if flavor_id and flavors:
            # Available until version 2.46
            flavor = flavors.get(flavor_id)
        else:
            # New in version 2.47
            flavor = server_details.get('flavor')
        if not flavor:
            return

        if project_name:
            tags.append("project_name:{}".format(project_name))
        if hypervisor_hostname:
            tags.append("hypervisor:{}".format(hypervisor_hostname))
        if server_id:
            tags.append("server_id:{}".format(server_id))
        if server_name:
            tags.append("server_name:{}".format(server_name))

        self.gauge("openstack.nova.server.flavor.disk", flavor.get('disk'), tags=tags + host_tags)
        self.gauge("openstack.nova.server.flavor.vcpus", flavor.get('vcpus'), tags=tags + host_tags)
        self.gauge("openstack.nova.server.flavor.ram", flavor.get('ram'), tags=tags + host_tags)
        self.gauge("openstack.nova.server.flavor.ephemeral", flavor.get('ephemeral'), tags=tags + host_tags)
        self.gauge("openstack.nova.server.flavor.swap", flavor.get('swap'), tags=tags + host_tags)

    def _get_host_aggregate_tag(self, hyp_hostname, use_shortname=False):
        tags = []
        if not hyp_hostname:
            return tags

        hyp_hostname = hyp_hostname.split('.')[0] if use_shortname else hyp_hostname
        aggregate_list = self.get_all_aggregate_hypervisors()
        if hyp_hostname in aggregate_list:
            tags.append('aggregate:{}'.format(aggregate_list[hyp_hostname].get('aggregate', "unknown")))
            # Need to check if there is a value for availability_zone
            # because it is possible to have an aggregate without an AZ
            try:
                if aggregate_list[hyp_hostname].get('availability_zone'):
                    tags.append('availability_zone:{}'.format(aggregate_list[hyp_hostname]['availability_zone']))
            except KeyError:
                self.log.debug('Unable to get the availability_zone for hypervisor: %s', hyp_hostname)
        else:
            self.log.info(
                'Unable to find hostname %s in aggregate list. Assuming this host is unaggregated', hyp_hostname
            )

        return tags

    def _send_api_service_checks(self, keystone_server_url, tags):
        # Nova
        service_check_tags = ["keystone_server: {}".format(keystone_server_url)] + tags
        try:
            self.get_nova_endpoint()
            self.service_check(self.COMPUTE_API_SC, AgentCheck.OK, tags=service_check_tags)
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            AuthenticationNeeded,
            InstancePowerOffFailure,
        ):
            self.service_check(self.COMPUTE_API_SC, AgentCheck.CRITICAL, tags=service_check_tags)

        # Neutron
        try:
            self.get_neutron_endpoint()
            self.service_check(self.NETWORK_API_SC, AgentCheck.OK, tags=service_check_tags)
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            AuthenticationNeeded,
            InstancePowerOffFailure,
        ):
            self.service_check(self.NETWORK_API_SC, AgentCheck.CRITICAL, tags=service_check_tags)

    def init_api(self, instance_config, keystone_server_url, custom_tags):
        """
        Guarantees a valid auth scope for this instance, and returns it

        Communicates with the identity server and initializes a new scope when one is absent, or has been forcibly
        removed due to token expiry
        """
        custom_tags = custom_tags or []

        if self._api is None:
            # We are missing the entire instance scope either because it is the first time we initialize it or because
            # authentication previously failed and got removed from the cache
            # Let's populate it now
            try:
                self.log.debug("Fetch scope for instance %s", self.instance_name)
                # Set keystone api with proper token
                self._api = ApiFactory.create(self.log, instance_config, self.http)
                self.service_check(
                    self.IDENTITY_API_SC,
                    AgentCheck.OK,
                    tags=["keystone_server: {}".format(keystone_server_url)] + custom_tags,
                )
            except KeystoneUnreachable as e:
                self.warning(
                    "The agent could not contact the specified identity server at `%s`. "
                    "Are you sure it is up at that address?",
                    keystone_server_url,
                )
                self.log.debug("Problem grabbing auth token: %s", e)
                self.service_check(
                    self.IDENTITY_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server: {}".format(keystone_server_url)] + custom_tags,
                )

                # If Keystone is down/unreachable, we default the
                # Nova and Neutron APIs to UNKNOWN since we cannot access the service catalog
                self.service_check(
                    self.NETWORK_API_SC,
                    AgentCheck.UNKNOWN,
                    tags=["keystone_server: {}".format(keystone_server_url)] + custom_tags,
                )
                self.service_check(
                    self.COMPUTE_API_SC,
                    AgentCheck.UNKNOWN,
                    tags=["keystone_server: {}".format(keystone_server_url)] + custom_tags,
                )

            except MissingNovaEndpoint as e:
                self.warning("The agent could not find a compatible Nova endpoint in your service catalog!")
                self.log.debug("Failed to get nova endpoint for response catalog: %s", e)
                self.service_check(
                    self.COMPUTE_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server: {}".format(keystone_server_url)] + custom_tags,
                )

            except MissingNeutronEndpoint:
                self.warning("The agent could not find a compatible Neutron endpoint in your service catalog!")
                self.service_check(
                    self.NETWORK_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server: {}".format(keystone_server_url)] + custom_tags,
                )

        if self._api is None:
            # Fast fail in the absence of an api
            raise IncompleteConfig("Could not initialise Openstack API")

    @traced
    def check(self, instance):
        # Initialize global variable that are per instances
        self.external_host_tags = {}
        self.instance_name = instance.get('name')
        if not self.instance_name:
            # We need a instance_name to identify this instance
            raise IncompleteConfig("Missing name")

        # have we been backed off
        if not self._backoff.should_run():
            self.log.info('Skipping run due to exponential backoff in effect')
            return

        network_ids = instance.get('network_ids', [])
        exclude_network_id_patterns = set(instance.get('exclude_network_ids', []))
        exclude_network_id_rules = [re.compile(ex) for ex in exclude_network_id_patterns]
        exclude_server_id_patterns = set(instance.get('exclude_server_ids', []))
        exclude_server_id_rules = [re.compile(ex) for ex in exclude_server_id_patterns]
        include_project_name_patterns = set(instance.get('whitelist_project_names', []))
        include_project_name_rules = [re.compile(ex) for ex in include_project_name_patterns]
        exclude_project_name_patterns = set(instance.get('blacklist_project_names', []))
        exclude_project_name_rules = [re.compile(ex) for ex in exclude_project_name_patterns]

        custom_tags = instance.get("tags", [])
        collect_project_metrics = is_affirmative(instance.get('collect_project_metrics', True))
        collect_hypervisor_metrics = is_affirmative(instance.get('collect_hypervisor_metrics', True))
        collect_hypervisor_load = is_affirmative(instance.get('collect_hypervisor_load', True))
        collect_network_metrics = is_affirmative(instance.get('collect_network_metrics', True))
        collect_server_diagnostic_metrics = is_affirmative(instance.get('collect_server_diagnostic_metrics', True))
        collect_server_flavor_metrics = is_affirmative(instance.get('collect_server_flavor_metrics', True))
        use_shortname = is_affirmative(instance.get('use_shortname', False))

        try:
            # Authenticate and add the instance api to apis cache
            keystone_server_url = self._get_keystone_server_url(instance)
            self.init_api(instance, keystone_server_url, custom_tags)
            if self._api is None:
                self.log.info("Not api found, make sure you admin user has access to your OpenStack projects: \n")
                return

            self.log.debug("Running check with credentials: \n")
            self._send_api_service_checks(keystone_server_url, custom_tags)
            # Artificial metric introduced to distinguish between old and new openstack integrations
            self.gauge("openstack.controller", 1)

            # List projects and filter them
            # TODO: NOTE: During authentication we use /v3/auth/projects and here we use /v3/projects.
            # TODO: These api don't seems to return the same thing however the latter contains the former.
            # TODO: Is this expected or could we just have one call with proper config?
            projects = self.get_projects(include_project_name_rules, exclude_project_name_rules)

            if collect_project_metrics:
                for project in itervalues(projects):
                    self.collect_project_limit(project, custom_tags)

            servers = self.populate_servers_cache(projects, exclude_server_id_rules)

            self.collect_hypervisors_metrics(
                servers,
                custom_tags=custom_tags,
                use_shortname=use_shortname,
                collect_hypervisor_metrics=collect_hypervisor_metrics,
                collect_hypervisor_load=collect_hypervisor_load,
            )

            if collect_server_diagnostic_metrics or collect_server_flavor_metrics:
                if collect_server_diagnostic_metrics:
                    self.log.debug("Fetch stats from %s server(s)", len(servers))
                    for server in itervalues(servers):
                        self.collect_server_diagnostic_metrics(server, tags=custom_tags, use_shortname=use_shortname)
                if collect_server_flavor_metrics:
                    if len(servers) >= 1 and 'flavor_id' in next(itervalues(servers)):
                        self.log.debug("Fetch server flavors")
                        # If flavors are not part of servers detail (new in version 2.47) then we need to fetch them
                        flavors = self.get_flavors()
                    else:
                        flavors = None
                    for server in itervalues(servers):
                        self.collect_server_flavor_metrics(
                            server, flavors, tags=custom_tags, use_shortname=use_shortname
                        )

            if collect_network_metrics:
                self.collect_networks_metrics(custom_tags, network_ids, exclude_network_id_rules)

            self.set_external_tags(self.get_external_host_tags())

        except IncompleteConfig as e:
            if isinstance(e, IncompleteIdentity):
                self.warning(
                    "Please specify the user via the `user` variable in your init_config.\n"
                    "This is the user you would use to authenticate with Keystone v3 via password auth.\n"
                    "The user should look like: "
                    "{'password': 'my_password', 'name': 'my_name', 'domain': {'id': 'my_domain_id'}}"
                )
            else:
                self.warning("Configuration Incomplete: %s! Check your openstack.yaml file", e)
        except AuthenticationNeeded:
            # Delete the scope, we'll populate a new one on the next run for this instance
            self.delete_api_cache()
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code < 500:
                self.warning("Error reaching nova API: %s", e)
            else:
                # exponential backoff
                self.do_backoff(custom_tags)
                return

        self._backoff.reset_backoff()

    def do_backoff(self, tags):
        backoff_interval, retries = self._backoff.do_backoff()

        self.gauge("openstack.backoff.interval", backoff_interval, tags=tags)
        self.gauge("openstack.backoff.retries", retries, tags=tags)
        self.warning("There were some problems reaching the nova API - applying exponential backoff")

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
    def get_nova_endpoint(self):
        return self._api.get_nova_endpoint()

    def get_os_hypervisor_uptime(self, hyp_id):
        return self._api.get_os_hypervisor_uptime(hyp_id)

    def get_os_aggregates(self):
        return self._api.get_os_aggregates()

    def get_os_hypervisors_detail(self):
        return self._api.get_os_hypervisors_detail()

    def get_servers_detail(self, query_params):
        return self._api.get_servers_detail(query_params)

    def get_server_diagnostics(self, server_id):
        return self._api.get_server_diagnostics(server_id)

    def get_project_limits(self, tenant_id):
        return self._api.get_project_limits(tenant_id)

    def get_flavors_detail(self, query_params):
        return self._api.get_flavors_detail(query_params)

    # Keystone Proxy Methods
    def get_projects(self, include_project_name_rules, exclude_project_name_rules):
        projects = self._api.get_projects()
        project_by_name = {}
        for project in projects:
            name = project.get('name')
            project_by_name[name] = project
        filtered_project_names = pattern_filter(
            [p for p in project_by_name], whitelist=include_project_name_rules, blacklist=exclude_project_name_rules
        )
        result = {name: v for (name, v) in iteritems(project_by_name) if name in filtered_project_names}
        return result

    # Neutron Proxy Methods
    def get_neutron_endpoint(self):
        return self._api.get_neutron_endpoint()

    def get_networks(self):
        return self._api.get_networks()

    def _get_keystone_server_url(self, instance_config):
        keystone_server_url = instance_config.get("keystone_server_url")
        if keystone_server_url:
            return keystone_server_url

        openstack_config_file_path = instance_config.get("openstack_config_file_path")
        if not openstack_config_file_path and not keystone_server_url:
            raise IncompleteConfig("Either keystone_server_url or openstack_config_file_path need to be provided")

        openstack_cloud_name = instance_config.get("openstack_cloud_name")
        openstack_config = OpenStackConfig(config_files=[openstack_config_file_path])
        cloud = openstack_config.get_one(cloud=openstack_cloud_name)
        cloud_auth = cloud.get_auth()
        if not cloud_auth or not cloud_auth.auth_url:
            raise IncompleteConfig(
                'No auth_url found for cloud {} in {}', openstack_cloud_name, openstack_config_file_path
            )
        return cloud_auth.auth_url
