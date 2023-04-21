# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from requests.exceptions import HTTPError

from datadog_checks.base import AgentCheck
from datadog_checks.openstack_controller.api.factory import make_api
from datadog_checks.openstack_controller.config import OpenstackConfig
from datadog_checks.openstack_controller.metrics import (
    HYPERVISOR_SERVICE_CHECK,
    KEYSTONE_SERVICE_CHECK,
    NEUTRON_AGENTS_METRICS,
    NEUTRON_AGENTS_METRICS_PREFIX,
    NEUTRON_QUOTAS_METRICS,
    NOVA_FLAVOR_METRICS,
    NOVA_HYPERVISOR_METRICS,
    NOVA_HYPERVISOR_SERVICE_CHECK,
    NOVA_LIMITS_METRICS,
    NOVA_QUOTA_SETS_METRICS,
    NOVA_SERVER_METRICS,
    NOVA_SERVICE_CHECK,
)


def _create_hypervisor_metric_tags(hypervisor_id, hypervisor_data, os_aggregates):
    tags = [
        f'hypervisor_id:{hypervisor_id}',
        f'hypervisor:{hypervisor_data.get("name")}',
        f'virt_type:{hypervisor_data.get("type")}',
        f'status:{hypervisor_data.get("status")}',
    ]
    for _os_aggregate_id, os_aggregate_value in os_aggregates.items():
        if hypervisor_data.get("name") in os_aggregate_value.get('hosts', []):
            tags.append('aggregate:{}'.format(os_aggregate_value.get("name")))
            tags.append('availability_zone:{}'.format(os_aggregate_value.get("availability_zone")))
    return tags


def _create_baremetal_nodes_metric_tags(node_name, node_uuid, conductor_group, power_state):
    tags = [
        f'power_state:{power_state}',
    ]
    if node_name:
        tags.append(f'node_name:{node_name}')
    if node_uuid:
        tags.append(f'node_uuid:{node_uuid}')
    if conductor_group:
        tags.append(f'conductor_group:{conductor_group}')
    return tags


def _create_baremetal_conductors_metric_tags(hostname, conductor_group):
    tags = [
        f'conductor_hostname:{hostname}',
    ]
    if conductor_group != "":
        tags.append(f'conductor_group:{conductor_group}')
    return tags


def _create_nova_services_metric_tags(name, host, state, nova_id, status, zone):
    tags = [
        f'service_name:{name}',
        f'service_host:{host}',
        f'service_status:{status}',
    ]
    if nova_id:
        tags.append(f'service_id:{nova_id}')

    if state:
        tags.append(f'service_state:{state}')

    if zone:
        tags.append(f'availability_zone:{zone}')
    return tags


def _create_project_tags(project):
    return [f"project_id:{project.get('id')}", f"project_name:{project.get('name')}"]


def _create_nova_server_tags(server_id, server_name, server_status, hypervisor, instance_hostname, flavor_name):
    tags = [
        f'server_id:{server_id}',
        f'server_name:{server_name}',
        f'server_status:{server_status}',
        f'hypervisor:{hypervisor}',
        f'flavor_name:{flavor_name}',
    ]
    if instance_hostname is not None:
        tags.append(f'instance_hostname:{instance_hostname}')

    return tags


class OpenStackControllerCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(OpenStackControllerCheck, self).__init__(name, init_config, instances)
        self.config = OpenstackConfig(self.log, self.instance)

    def check(self, _instance):
        tags = [
            'keystone_server:{}'.format(self.config.keystone_server_url),
        ] + self.instance.get('tags', [])
        api = make_api(self.config, self.log, self.http)
        self.gauge("openstack.controller", 1)
        self._report_metrics(api, tags)

    def _report_metrics(self, api, tags):
        if self._report_identity_metrics(api, tags):
            auth_projects = api.get_auth_projects()
            self.log.debug("auth_projects: %s", auth_projects)
            for project in auth_projects:
                self._report_project_metrics(api, project, tags + ['domain_id:{}'.format(self.config.domain_id)])

    def _report_identity_metrics(self, api, tags):
        try:
            self._report_identity_response_time(api, tags)
            self._report_identity_domains(api, tags)
            self._report_identity_projects(api, tags)
            self._report_identity_users(api, tags)
            self._report_identity_groups(api, tags)
            self._report_identity_services(api, tags)
            self._report_identity_limits(api, tags)
            return True
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting identity metrics: %s", e)
            self.service_check(KEYSTONE_SERVICE_CHECK, AgentCheck.CRITICAL, tags=tags)
        except Exception as e:
            self.warning("Exception while reporting identity metrics: %s", e)
        return False

    def _report_identity_response_time(self, api, tags):
        response_time = api.get_identity_response_time()
        self.log.debug("identity response time: %s", response_time)
        self.gauge('openstack.keystone.response_time', response_time, tags=tags)
        self.service_check(KEYSTONE_SERVICE_CHECK, AgentCheck.OK, tags=tags)

    def _report_identity_domains(self, api, tags):
        identity_domains = api.get_identity_domains()
        self.log.debug("identity_domains: %s", identity_domains)
        self.gauge('openstack.keystone.domains.count', len(identity_domains), tags=tags)
        for domain in identity_domains:
            enabled = domain.get("enabled")
            if enabled is not None:
                self.gauge(
                    'openstack.keystone.domains.enabled',
                    1 if enabled else 0,
                    tags + ['domain_id:{}'.format(domain.get("id"))],
                )

    def _report_identity_projects(self, api, tags):
        identity_projects = api.get_identity_projects()
        self.log.debug("identity_projects: %s", identity_projects)
        self.gauge(
            'openstack.keystone.projects.count',
            len(identity_projects),
            tags=tags + ['domain_id:{}'.format(self.config.domain_id)],
        )
        for project in identity_projects:
            enabled = project.get("enabled")
            if enabled is not None:
                self.gauge(
                    'openstack.keystone.projects.enabled',
                    1 if enabled else 0,
                    tags
                    + ['domain_id:{}'.format(self.config.domain_id)]
                    + [f"project_id:{project.get('id')}", f"project_name:{project.get('name')}"],
                )

    def _report_identity_users(self, api, tags):
        identity_users = api.get_identity_users()
        self.log.debug("identity_users: %s", identity_users)
        self.gauge(
            'openstack.keystone.users.count',
            len(identity_users),
            tags=tags + ['domain_id:{}'.format(self.config.domain_id)],
        )
        for user in identity_users:
            enabled = user.get("enabled")
            if enabled is not None:
                self.gauge(
                    'openstack.keystone.users.enabled',
                    1 if enabled else 0,
                    tags
                    + ['domain_id:{}'.format(self.config.domain_id)]
                    + [f"user_id:{user.get('id')}", f"user_name:{user.get('name')}"],
                )

    def _report_identity_groups(self, api, tags):
        identity_groups = api.get_identity_groups()
        self.log.debug("identity_groups: %s", identity_groups)
        self.gauge(
            'openstack.keystone.groups.count',
            len(identity_groups),
            tags=tags + ['domain_id:{}'.format(self.config.domain_id)],
        )
        for group in identity_groups:
            identity_group_users = api.get_identity_group_users(group.get('id'))
            self.gauge(
                'openstack.keystone.groups.users',
                len(identity_group_users),
                tags
                + ['domain_id:{}'.format(self.config.domain_id)]
                + [f"group_id:{group.get('id')}", f"group_name:{group.get('name')}"],
            )

    def _report_identity_services(self, api, tags):
        identity_services = api.get_identity_services()
        self.log.debug("identity_services: %s", identity_services)
        self.gauge(
            'openstack.keystone.services.count',
            len(identity_services),
            tags=tags + ['domain_id:{}'.format(self.config.domain_id)],
        )
        for service in identity_services:
            enabled = service.get("enabled")
            if enabled is not None:
                self.gauge(
                    'openstack.keystone.services.enabled',
                    1 if enabled else 0,
                    tags
                    + ['domain_id:{}'.format(self.config.domain_id)]
                    + [
                        f"service_id:{service.get('id')}",
                        f"service_name:{service.get('name')}",
                        f"service_type:{service.get('type')}",
                    ],
                )

    def _report_identity_limits(self, api, tags):
        identity_limits = api.get_identity_limits()
        self.log.debug("identity_limits: %s", identity_limits)
        for limit_id, limit_data in identity_limits.items():
            domain_id = limit_data.get('domain_id')
            project_id = limit_data.get('project_id')
            optional_tags = [
                'domain_id:{}'.format(domain_id) if domain_id else None,
                'project_id:{}'.format(project_id) if project_id else None,
            ]
            self.gauge(
                'openstack.keystone.limits',
                limit_data['limit'],
                tags=tags
                + [
                    'limit_id:{}'.format(limit_id),
                    'resource_name:{}'.format(limit_data['resource_name']),
                    'service_id:{}'.format(limit_data.get('service_id', '')),
                    'region_id:{}'.format(limit_data.get('region_id', '')),
                ]
                + optional_tags,
            )

    def _report_project_metrics(self, api, project, tags):
        project_id = project.get('id')
        project_name = project.get('name')
        self.log.debug("reporting metrics from project: [id:%s][name:%s]", project_id, project_name)
        project_tags = _create_project_tags(project)
        self._report_compute_metrics(api, project_id, tags + project_tags)
        self._report_network_metrics(api, project_id, tags + project_tags)
        self._report_block_storage_metrics(api, project_id, tags + project_tags)
        self._report_baremetal_metrics(api, project_id, tags + project_tags)
        self._report_load_balancer_metrics(api, project_id, tags + project_tags)

    def _report_compute_metrics(self, api, project_id, project_tags):
        try:
            self._report_compute_response_time(api, project_id, project_tags)
            self._report_compute_limits(api, project_id, project_tags)
            self._report_compute_quotas(api, project_id, project_tags)
            self._report_compute_servers(api, project_id, project_tags)
            self._report_compute_flavors(api, project_id, project_tags)
            self._report_compute_hypervisors(api, project_id, project_tags)
            self._report_compute_services(api, project_id, project_tags)
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting compute metrics: %s", e)
            self.service_check(NOVA_SERVICE_CHECK, AgentCheck.CRITICAL, tags=project_tags)
        except Exception as e:
            self.warning("Exception while reporting compute metrics: %s", e)

    def _report_compute_response_time(self, api, project_id, project_tags):
        response_time = api.get_compute_response_time(project_id)
        self.log.debug("compute response time: %s", response_time)
        if response_time is not None:
            self.gauge('openstack.nova.response_time', response_time, tags=project_tags)
            self.service_check(NOVA_SERVICE_CHECK, AgentCheck.OK, tags=project_tags)
        else:
            self.service_check(NOVA_SERVICE_CHECK, AgentCheck.UNKNOWN, tags=project_tags)

    def _report_compute_limits(self, api, project_id, project_tags):
        compute_limits = api.get_compute_limits(project_id)
        self.log.debug("compute_limits: %s", compute_limits)
        if compute_limits:
            for metric, value in compute_limits.items():
                if metric in NOVA_LIMITS_METRICS:
                    self.gauge(metric, value, tags=project_tags)
                else:
                    self.log.warning("%s metric not reported as nova limits metric", metric)

    def _report_compute_quotas(self, api, project_id, project_tags):
        compute_quotas = api.get_compute_quota_set(project_id)
        self.log.debug("compute_quotas: %s", compute_quotas)
        if compute_quotas:
            for metric, value in compute_quotas['metrics'].items():
                # long_metric_name = f'{NOVA_QUOTA_SETS_METRICS_PREFIX}.{metric}'
                tags = project_tags + [f'quota_id:{compute_quotas["id"]}']
                if metric in NOVA_QUOTA_SETS_METRICS:
                    self.gauge(metric, value, tags=tags)
                else:
                    self.log.warning("%s metric not reported as nova quota metric", metric)

    def _report_compute_services(self, api, project_id, project_tags):
        compute_services = api.get_compute_services(project_id)
        self.log.debug("compute_services: %s", compute_services)
        if compute_services is not None:
            for compute_service in compute_services:
                service_tags = _create_nova_services_metric_tags(
                    compute_service.get('name'),
                    compute_service.get('host'),
                    compute_service.get('state'),
                    compute_service.get('id'),
                    compute_service.get('status'),
                    compute_service.get('zone'),
                )
                all_tags = project_tags + service_tags
                is_up = compute_service.get('is_up')
                self.gauge('openstack.nova.service.up', is_up, tags=all_tags)

    def _report_compute_servers(self, api, project_id, project_tags):
        compute_servers = api.get_compute_servers(project_id)
        self.log.debug("compute_servers: %s", compute_servers)
        if compute_servers is not None:
            self.gauge(
                'openstack.nova.server.count',
                len(compute_servers),
                tags=project_tags,
            )
            for server_id, server_data in compute_servers.items():
                if server_data["status"] == "active" or server_data["status"] == "error":
                    self.gauge(
                        f'openstack.nova.server.{server_data["status"]}',
                        1,
                        tags=project_tags
                        + _create_nova_server_tags(
                            server_id,
                            server_data["name"],
                            server_data["status"],
                            server_data["hypervisor_hostname"],
                            server_data["instance_hostname"],
                            server_data["flavor_name"],
                        ),
                    )
                for metric, value in server_data['metrics'].items():
                    if metric in NOVA_SERVER_METRICS:
                        self.gauge(
                            metric,
                            value,
                            tags=project_tags
                            + _create_nova_server_tags(
                                server_id,
                                server_data["name"],
                                server_data["status"],
                                server_data["hypervisor_hostname"],
                                server_data["instance_hostname"],
                                server_data["flavor_name"],
                            ),
                        )
                    else:
                        self.log.warning("%s metric not reported as nova server metric", metric)

    def _report_compute_flavors(self, api, project_id, project_tags):
        compute_flavors = api.get_compute_flavors(project_id)
        self.log.debug("compute_flavors: %s", compute_flavors)
        if compute_flavors:
            for flavor_id, flavor_data in compute_flavors.items():
                for metric, value in flavor_data['metrics'].items():
                    # long_metric_name = f'openstack.nova.flavor.{metric}'
                    if metric in NOVA_FLAVOR_METRICS:
                        self.gauge(
                            metric,
                            value,
                            tags=project_tags + [f'flavor_id:{flavor_id}', f'flavor_name:{flavor_data["name"]}'],
                        )

    def _report_compute_hypervisors(self, api, project_id, project_tags):
        compute_hypervisors = api.get_compute_hypervisors(project_id)
        self.log.debug("compute_hypervisors: %s", compute_hypervisors)
        compute_os_aggregates = api.get_compute_os_aggregates(project_id)
        self.log.debug("compute_os_aggregates: %s", compute_os_aggregates)
        if compute_hypervisors:
            for hypervisor_id, hypervisor_data in compute_hypervisors.items():
                hypervisor_tags = project_tags + _create_hypervisor_metric_tags(
                    hypervisor_id, hypervisor_data, compute_os_aggregates
                )
                self._report_hypervisor_service_check(
                    hypervisor_data.get('state'), hypervisor_data["name"], hypervisor_tags
                )
                if self.config.collect_hypervisor_metrics:
                    self._report_hypervisor_metrics(hypervisor_data, hypervisor_tags)

    def _report_hypervisor_service_check(self, state, name, hypervisor_tags):
        self.service_check(
            NOVA_HYPERVISOR_SERVICE_CHECK,
            HYPERVISOR_SERVICE_CHECK.get(state, AgentCheck.UNKNOWN),
            hostname=name,
            tags=hypervisor_tags,
        )

    def _report_hypervisor_metrics(self, hypervisor_data, hypervisor_tags):
        for metric, value in hypervisor_data.get('metrics', {}).items():
            if metric in NOVA_HYPERVISOR_METRICS:
                self._report_hypervisor_metric(metric, value, hypervisor_tags)
        self._report_hypervisor_metric(
            NOVA_HYPERVISOR_SERVICE_CHECK, 1 if hypervisor_data.get('state') == 'up' else 0, hypervisor_tags
        )

    def _report_hypervisor_metric(self, long_metric_name, value, tags):
        if long_metric_name in NOVA_HYPERVISOR_METRICS:
            self.gauge(long_metric_name, value, tags=tags)

    def _report_network_metrics(self, api, project_id, project_tags):
        try:
            self._report_network_response_time(api, project_id, project_tags)
            self._report_network_quotas(api, project_id, project_tags)
            self._report_network_agents(api, project_id, project_tags)
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting network metrics: %s", e)
            self.service_check('openstack.neutron.api.up', AgentCheck.CRITICAL, tags=project_tags)
        except Exception as e:
            self.warning("Exception while reporting network metrics: %s", e)

    def _report_network_response_time(self, api, project_id, project_tags):
        response_time = api.get_network_response_time(project_id)
        self.log.debug("network response time: %s", response_time)
        if response_time is not None:
            self.gauge('openstack.neutron.response_time', response_time, tags=project_tags)
            self.service_check('openstack.neutron.api.up', AgentCheck.OK, tags=project_tags)
        else:
            self.service_check('openstack.neutron.api.up', AgentCheck.UNKNOWN, tags=project_tags)

    def _report_network_quotas(self, api, project_id, project_tags):
        network_quotas = api.get_network_quotas(project_id)
        self.log.debug("network_quotas: %s", network_quotas)
        if network_quotas is not None:
            for metric, value in network_quotas.items():
                if metric in NEUTRON_QUOTAS_METRICS:
                    self.gauge(metric, value, tags=project_tags)
                else:
                    self.log.warning("%s metric not reported as neutron quotas metric", metric)

    def _report_network_agents(self, api, project_id, project_tags):
        network_agents = api.get_network_agents(project_id)
        self.log.debug("network_agents: %s", network_agents)
        if network_agents is not None:
            self.gauge(f'{NEUTRON_AGENTS_METRICS_PREFIX}.count', len(network_agents), tags=project_tags)
            for agent_id, agent_data in network_agents.items():
                for metric, value in agent_data['metrics'].items():
                    if metric in NEUTRON_AGENTS_METRICS:
                        self.gauge(
                            metric,
                            value,
                            tags=project_tags
                            + [
                                f'agent_id:{agent_id}',
                                f'agent_name:{agent_data["name"]}',
                                f'agent_host:{agent_data["host"]}',
                                f'agent_availability_zone:{agent_data["availability_zone"]}',
                                f'agent_type:{agent_data["type"]}',
                            ],
                        )

    def _report_block_storage_metrics(self, api, project_id, project_tags):
        try:
            self._report_block_storage_response_time(api, project_id, project_tags)
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting block storage metrics: %s", e)
            self.service_check('openstack.cinder.api.up', AgentCheck.CRITICAL, tags=project_tags)
        except Exception as e:
            self.warning("Exception while reporting block storage metrics: %s", e)

    def _report_block_storage_response_time(self, api, project_id, project_tags):
        response_time = api.get_block_storage_response_time(project_id)
        self.log.debug("block storage response time: %s", response_time)
        if response_time is not None:
            self.gauge('openstack.cinder.response_time', response_time, tags=project_tags)
            self.service_check('openstack.cinder.api.up', AgentCheck.OK, tags=project_tags)
        else:
            self.service_check('openstack.cinder.api.up', AgentCheck.UNKNOWN, tags=project_tags)

    def _report_baremetal_metrics(self, api, project_id, project_tags):
        try:
            self._report_baremetal_response_time(api, project_id, project_tags)
            self._report_baremetal_nodes(api, project_id, project_tags)
            self._report_baremetal_conductors(api, project_id, project_tags)
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting baremetal metrics: %s", e)
            self.service_check('openstack.ironic.api.up', AgentCheck.CRITICAL, tags=project_tags)
        except Exception as e:
            self.warning("Exception while reporting baremetal metrics: %s", e)

    def _report_baremetal_response_time(self, api, project_id, project_tags):
        response_time = api.get_baremetal_response_time(project_id)
        self.log.debug("baremetal response time: %s", response_time)
        if response_time is not None:
            self.gauge('openstack.ironic.response_time', response_time, tags=project_tags)
            self.service_check('openstack.ironic.api.up', AgentCheck.OK, tags=project_tags)
        else:
            self.service_check('openstack.ironic.api.up', AgentCheck.UNKNOWN, tags=project_tags)

    def _report_baremetal_nodes(self, api, project_id, project_tags):
        nodes_data = api.get_baremetal_nodes(project_id)
        if nodes_data is not None:
            for node_data in nodes_data:
                is_up = node_data.get('is_up')
                node_tags = _create_baremetal_nodes_metric_tags(
                    node_data.get('node_name'),
                    node_data.get('node_uuid'),
                    node_data.get('conductor_group'),
                    node_data.get('power_state'),
                )
                all_tags = node_tags + project_tags
                self.gauge('openstack.ironic.node.up', value=is_up, tags=all_tags)
                self.gauge('openstack.ironic.node.count', value=1, tags=all_tags)

    def _report_baremetal_conductors(self, api, project_id, project_tags):
        conductors_data = api.get_baremetal_conductors(project_id)
        if conductors_data:
            for conductor_data in conductors_data:
                conductor_tags = _create_baremetal_conductors_metric_tags(
                    conductor_data.get('hostname'),
                    conductor_data.get('conductor_group'),
                )
                all_tags = conductor_tags + project_tags
                self.gauge('openstack.ironic.conductor.up', value=conductor_data.get('alive'), tags=all_tags)

    def _report_load_balancer_metrics(self, api, project_id, project_tags):
        try:
            self._report_load_balancer_response_time(api, project_id, project_tags)
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting load balancer metrics: %s", e)
            self.service_check('openstack.octavia.api.up', AgentCheck.CRITICAL, tags=project_tags)
        except Exception as e:
            self.warning("Exception while reporting load balancer metrics: %s", e)

    def _report_load_balancer_response_time(self, api, project_id, project_tags):
        response_time = api.get_load_balancer_response_time(project_id)
        self.log.debug("load balancer response time: %s", response_time)
        if response_time is not None:
            self.gauge('openstack.octavia.response_time', response_time, tags=project_tags)
            self.service_check('openstack.octavia.api.up', AgentCheck.OK, tags=project_tags)
        else:
            self.service_check('openstack.octavia.api.up', AgentCheck.UNKNOWN, tags=project_tags)
