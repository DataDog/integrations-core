# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from requests.exceptions import HTTPError

from datadog_checks.base import AgentCheck
from datadog_checks.openstack_controller.api.factory import make_api
from datadog_checks.openstack_controller.config import OpenstackConfig
from datadog_checks.openstack_controller.http_error import http_error
from datadog_checks.openstack_controller.metrics import (
    HYPERVISOR_SERVICE_CHECK,
    KEYSTONE_DOMAINS_COUNT,
    KEYSTONE_DOMAINS_METRICS,
    KEYSTONE_PROJECTS_COUNT,
    KEYSTONE_PROJECTS_METRICS,
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


def _create_load_balancer_loadbalancer_tags(loadbalancer_data):
    tags = [
        f'loadbalancer_id:{loadbalancer_data.get("id")}',
        f'loadbalancer_name:{loadbalancer_data.get("name")}',
        f'provisioning_status:{loadbalancer_data.get("provisioning_status")}',
        f'operating_status:{loadbalancer_data.get("operating_status")}',
    ]

    listeners = loadbalancer_data.get("listeners")
    if listeners:
        for listener in listeners:
            tags.append(f'listener_id:{listener.get("id")}')

    pools = loadbalancer_data.get("pools")
    if pools:
        for pool in pools:
            tags.append(f'pool_id:{pool.get("id")}')

    return tags


def _create_load_balancer_listener_tags(listener_data, loadbalancers_data):
    tags = [
        f'listener_id:{listener_data.get("id")}',
        f'listener_name:{listener_data.get("name")}',
    ]

    loadbalancers = listener_data.get("loadbalancers")
    if loadbalancers:
        for loadbalancer in loadbalancers:
            loadbalancer_id = loadbalancer.get("id")
            loadbalancer_data = loadbalancers_data.get(loadbalancer_id)
            tags.append(f'loadbalancer_id:{loadbalancer_id}')
            tags.append(f'loadbalancer_name:{loadbalancer_data.get("name")}')

    return tags


def _create_load_balancer_member_tags(member_data, loadbalancer_data, pool_data):
    tags = [
        f'member_id:{member_data.get("id")}',
        f'member_name:{member_data.get("name")}',
        f'provisioning_status:{member_data.get("provisioning_status")}',
        f'operating_status:{member_data.get("operating_status")}',
    ]

    if loadbalancer_data:
        tags.append(f'loadbalancer_id:{loadbalancer_data.get("id")}')
        tags.append(f'loadbalancer_name:{loadbalancer_data.get("name")}')

    if pool_data:
        tags.append(f'pool_id:{pool_data.get("id")}')
        tags.append(f'pool_name:{pool_data.get("name")}')

    return tags


def _create_load_balancer_healthmonitor_tags(healthmonitor_data, pool_data):
    tags = [
        f'healthmonitor_id:{healthmonitor_data.get("id")}',
        f'healthmonitor_name:{healthmonitor_data.get("name")}',
        f'provisioning_status:{healthmonitor_data.get("provisioning_status")}',
        f'operating_status:{healthmonitor_data.get("operating_status")}',
        f'type:{healthmonitor_data.get("type")}',
    ]

    if pool_data:
        tags.append(f'pool_id:{pool_data.get("id")}')
        tags.append(f'pool_name:{pool_data.get("name")}')

    return tags


def _create_load_balancer_pool_tags(pool_data, loadbalancers_data, listeners_data, members_data, healthmonitors_data):
    tags = [
        f'pool_id:{pool_data.get("id")}',
        f'pool_name:{pool_data.get("name")}',
        f'provisioning_status:{pool_data.get("provisioning_status")}',
        f'operating_status:{pool_data.get("operating_status")}',
    ]

    loadbalancers = pool_data.get("loadbalancers")
    if loadbalancers:
        for loadbalancer in loadbalancers:
            loadbalancer_id = loadbalancer.get("id")
            loadbalancer_data = loadbalancers_data.get(loadbalancer_id)
            tags.append(f'loadbalancer_id:{loadbalancer_id}')
            tags.append(f'loadbalancer_name:{loadbalancer_data.get("name")}')

    listeners = pool_data.get("listeners")
    if listeners:
        for listener in listeners:
            listener_id = listener.get("id")
            listener_data = listeners_data.get(listener_id)
            tags.append(f'listener_id:{listener_id}')
            tags.append(f'listener_name:{listener_data.get("name")}')

    members = pool_data.get("members")
    if members:
        for member in members:
            member_id = member.get("id")
            member_data = members_data.get(member_id)
            tags.append(f'member_id:{member_id}')
            tags.append(f'member_name:{member_data.get("name")}')

    healthmonitor_id = pool_data.get("healthmonitor_id")
    if healthmonitor_id:
        healthmonitor_data = healthmonitors_data.get(healthmonitor_id)
        tags.append(f'healthmonitor_id:{healthmonitor_id}')
        tags.append(f'healthmonitor_name:{healthmonitor_data.get("name")}')

    return tags


def _create_load_balancer_amphora_tags(amphora_data, amphora_stats, loadbalancers_data, listeners_data):
    tags = [
        f'amphora_id:{amphora_data.get("id")}',
        f'amphora_compute_id:{amphora_data.get("compute_id")}',
        f'status:{amphora_data.get("status")}',
    ]

    loadbalancer_id = amphora_stats.get("loadbalancer_id")
    if loadbalancer_id:
        tags.append(f'loadbalancer_id:{loadbalancer_id}')
        tags.append(f'loadbalancer_name:{loadbalancers_data.get(loadbalancer_id).get("name")}')

    listener_id = amphora_stats.get("listener_id")
    if listener_id:
        tags.append(f'listener_id:{listener_id}')
        tags.append(f'listener_name:{listeners_data.get(listener_id).get("name")}')

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
        self.gauge("openstack.controller", 1, tags=tags)
        if self._report_identity_response_time(api, tags):
            if self._authenticate_user(api, tags):
                self._report_metrics(api, tags)

    def _authenticate_user(self, api, tags):
        self.log.debug("authenticating user unscoped")
        try:
            api.post_auth_unscoped()
            self.log.debug("authentication ok")
            return True
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while authenticating user unscoped: %s", e)
        except Exception as e:
            self.warning("Exception while authenticating user unscoped: %s", e)
        return False

    def _report_metrics(self, api, tags):
        auth_projects = api.get_auth_projects()
        self.log.debug("auth_projects: %s", auth_projects)
        reported_global_metrics = False
        if self._authenticate_domain(api):
            self.log.debug("Authenticated user for domain, reporting metrics using domain scope")
            reported_identity_metrics = self._report_identity_metrics(api, tags)
            reported_domain_metrics = self._report_domain_metrics(api, tags + ['domain_id:{}'.format(self.config.domain_id)])
            reported_global_metrics = reported_identity_metrics and reported_domain_metrics
        for project in auth_projects:
            if self._authenticate_project(api, project):
                if not reported_global_metrics:
                    self.log.debug("Authenticated user for project %s, reporting metrics using project scope", project)
                    reported_identity_metrics = self._report_identity_metrics(api, tags)
                    reported_domain_metrics = self._report_domain_metrics(api, tags + ['domain_id:{}'.format(self.config.domain_id)])
                    reported_global_metrics = reported_identity_metrics and reported_domain_metrics
                self._report_project_metrics(api, project, tags + ['domain_id:{}'.format(self.config.domain_id)])

    def _authenticate_domain(self, api):
        self.log.debug("authenticating user domain scope")
        try:
            api.post_auth_domain(self.config.domain_id)
            self.log.debug("authentication ok")
            return True
        except HTTPError as e:
            self.log.error("HTTPError while authenticating domain scoped: %s", e)
        except Exception as e:
            self.warning("Exception while authenticating domain scoped: %s", e)
        return False

    def _report_identity_metrics(self, api, tags):
        try:
            self._report_identity_domains(api, tags)
            self._report_identity_projects(api, tags)
            self._report_identity_users(api, tags)
            self._report_identity_groups(api, tags)
            self._report_identity_services(api, tags)
            self._report_identity_limits(api, tags)
            return True
        except Exception as e:
            self.warning("Exception while reporting identity metrics: %s", e)
            return False

    def _report_identity_response_time(self, api, tags):
        try:
            response_time = api.get_identity_response_time()
            self.log.debug("identity response time: %s", response_time)
            self.gauge('openstack.keystone.response_time', response_time, tags=tags)
            self.service_check(KEYSTONE_SERVICE_CHECK, AgentCheck.OK, tags=tags)
            return True
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting identity response time: %s", e)
            self.service_check(KEYSTONE_SERVICE_CHECK, AgentCheck.CRITICAL, tags=tags)
        except Exception as e:
            self.warning("Exception while reporting identity response time: %s", e)
        return False

    @http_error("HTTPError while reporting identity domains metrics")
    def _report_identity_domains(self, api, tags):
        identity_domains = api.get_identity_domains()
        self.log.debug("identity_domains: %s", identity_domains)
        self.gauge(KEYSTONE_DOMAINS_COUNT, len(identity_domains), tags=tags)
        for domain_id, domain_data in identity_domains.items():
            domain_tags = [
                'domain_id:{}'.format(domain_id),
                'domain_name:{}'.format(domain_data['name']),
            ] + domain_data['tags']
            for metric, value in domain_data['metrics'].items():
                if metric in KEYSTONE_DOMAINS_METRICS:
                    self.gauge(
                        metric,
                        value,
                        tags=tags + domain_tags,
                    )
                else:
                    self.log.warning("%s metric not reported as identity domain metric", metric)

    @http_error("HTTPError while reporting identity projects metrics")
    def _report_identity_projects(self, api, tags):
        identity_projects = api.get_identity_projects()
        self.log.debug("identity_projects: %s", identity_projects)
        self.gauge(
            KEYSTONE_PROJECTS_COUNT,
            len(identity_projects),
            tags=tags + ['domain_id:{}'.format(self.config.domain_id)],
        )
        if identity_projects:
            for project_id, project_data in identity_projects.items():
                project_tags = [
                    'domain_id:{}'.format(self.config.domain_id),
                    'project_id:{}'.format(project_id),
                    'project_name:{}'.format(project_data['name']),
                ] + project_data['tags']
                for metric, value in project_data['metrics'].items():
                    if metric in KEYSTONE_PROJECTS_METRICS:
                        self.gauge(
                            metric,
                            value,
                            tags=tags + project_tags,
                        )
                    else:
                        self.log.warning("%s metric not reported as identity project metric", metric)

    @http_error("HTTPError while reporting identity users metrics")
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

    @http_error("HTTPError while reporting identity groups metrics")
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

    @http_error("HTTPError while reporting identity services metrics")
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

    @http_error("HTTPError while reporting identity limits metrics")
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
                + ['domain_id:{}'.format(self.config.domain_id)]
                + [
                    'limit_id:{}'.format(limit_id),
                    'resource_name:{}'.format(limit_data['resource_name']),
                    'service_id:{}'.format(limit_data.get('service_id', '')),
                    'region_id:{}'.format(limit_data.get('region_id', '')),
                ]
                + optional_tags,
            )

    def _report_domain_metrics(self, api, tags):
        reported_compute_metrics = self._report_compute_domain_metrics(api, tags)
        reported_network_metrics = self._report_network_domain_metrics(api, tags)
        reported_baremetal_metrics = self._report_baremetal_domain_metrics(api, tags)
        reported_load_balancer_metrics = self._report_load_balancer_domain_metrics(api, tags)
        return reported_compute_metrics and reported_network_metrics and reported_baremetal_metrics and reported_load_balancer_metrics

    def _authenticate_project(self, api, project):
        self.log.debug("authenticating user project scope")
        try:
            api.post_auth_project(project.get('id'))
            self.log.debug("authentication ok")
            return True
        except HTTPError as e:
            self.log.error("HTTPError while authenticating project scoped: %s", e)
        except Exception as e:
            self.warning("Exception while authenticating project scoped: %s", e)
        return False

    def _report_project_metrics(self, api, project, tags):
        project_id = project.get('id')
        project_name = project.get('name')
        self.log.debug("reporting metrics from project: [id:%s][name:%s]", project_id, project_name)
        project_tags = _create_project_tags(project)
        self._report_compute_project_metrics(api, project_id, tags + project_tags)
        self._report_network_project_metrics(api, project_id, tags + project_tags)
        self._report_block_storage_metrics(api, project_id, tags + project_tags)
        self._report_load_balancer_project_metrics(api, project_id, tags + project_tags)

    def _report_compute_domain_metrics(self, api, tags):
        try:
            self._report_compute_response_time(api, tags)
            self._report_compute_limits(api, tags)
            self._report_compute_services(api, tags)
            self._report_compute_flavors(api, tags)
            self._report_compute_hypervisors(api, tags)
            return True
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting compute domain metrics: %s", e)
            self.service_check(NOVA_SERVICE_CHECK, AgentCheck.CRITICAL, tags=tags)
            return False
        except Exception as e:
            self.warning("Exception while reporting compute domain metrics: %s", e)
            return False

    def _report_compute_project_metrics(self, api, project_id, project_tags):
        try:
            self._report_compute_quotas(api, project_id, project_tags)
            self._report_compute_servers(api, project_id, project_tags)
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting compute project metrics: %s", e)
        except Exception as e:
            self.warning("Exception while reporting compute project metrics: %s", e)

    def _report_compute_response_time(self, api, tags):
        response_time = api.get_compute_response_time()
        self.log.debug("compute response time: %s", response_time)
        if response_time is not None:
            self.gauge('openstack.nova.response_time', response_time, tags=tags)
            self.service_check(NOVA_SERVICE_CHECK, AgentCheck.OK, tags=tags)
        else:
            self.service_check(NOVA_SERVICE_CHECK, AgentCheck.UNKNOWN, tags=tags)

    def _report_compute_limits(self, api, tags):
        compute_limits = api.get_compute_limits()
        self.log.debug("compute_limits: %s", compute_limits)
        if compute_limits:
            for metric, value in compute_limits.items():
                if metric in NOVA_LIMITS_METRICS:
                    self.gauge(metric, value, tags=tags)
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

    def _report_compute_services(self, api, tags):
        compute_services = api.get_compute_services()
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
                all_tags = tags + service_tags
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

    def _report_compute_flavors(self, api, tags):
        compute_flavors = api.get_compute_flavors()
        self.log.debug("compute_flavors: %s", compute_flavors)
        if compute_flavors:
            for flavor_id, flavor_data in compute_flavors.items():
                for metric, value in flavor_data['metrics'].items():
                    # long_metric_name = f'openstack.nova.flavor.{metric}'
                    if metric in NOVA_FLAVOR_METRICS:
                        self.gauge(
                            metric,
                            value,
                            tags=tags + [f'flavor_id:{flavor_id}', f'flavor_name:{flavor_data["name"]}'],
                        )

    def _report_compute_hypervisors(self, api, tags):
        compute_hypervisors = api.get_compute_hypervisors()
        self.log.debug("compute_hypervisors: %s", compute_hypervisors)
        compute_os_aggregates = api.get_compute_os_aggregates()
        self.log.debug("compute_os_aggregates: %s", compute_os_aggregates)
        if compute_hypervisors:
            for hypervisor_id, hypervisor_data in compute_hypervisors.items():
                hypervisor_tags = tags + _create_hypervisor_metric_tags(
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

    def _report_network_project_metrics(self, api, project_id, project_tags):
        try:
            self._report_network_quotas(api, project_id, project_tags)

        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting network project metrics: %s", e)
        except Exception as e:
            self.warning("Exception while reporting network project metrics: %s", e)

    def _report_network_domain_metrics(self, api, tags):
        try:
            self._report_network_response_time(api, tags)
            self._report_network_agents(api, tags)
            return True
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting network domain metrics: %s", e)
            self.service_check('openstack.neutron.api.up', AgentCheck.CRITICAL, tags=tags)
            return False
        except Exception as e:
            self.warning("Exception while reporting network domain metrics: %s", e)
            return False

    def _report_network_response_time(self, api, tags):
        response_time = api.get_network_response_time()
        self.log.debug("network response time: %s", response_time)
        if response_time is not None:
            self.gauge('openstack.neutron.response_time', response_time, tags=tags)
            self.service_check('openstack.neutron.api.up', AgentCheck.OK, tags=tags)
        else:
            self.service_check('openstack.neutron.api.up', AgentCheck.UNKNOWN, tags=tags)

    def _report_network_quotas(self, api, project_id, project_tags):
        network_quotas = api.get_network_quotas(project_id)
        self.log.debug("network_quotas: %s", network_quotas)
        if network_quotas is not None:
            for metric, value in network_quotas.items():
                if metric in NEUTRON_QUOTAS_METRICS:
                    self.gauge(metric, value, tags=project_tags)
                else:
                    self.log.warning("%s metric not reported as neutron quotas metric", metric)

    def _report_network_agents(self, api, tags):
        network_agents = api.get_network_agents()
        self.log.debug("network_agents: %s", network_agents)
        if network_agents is not None:
            self.gauge(f'{NEUTRON_AGENTS_METRICS_PREFIX}.count', len(network_agents), tags=tags)
            for agent_id, agent_data in network_agents.items():
                for metric, value in agent_data['metrics'].items():
                    if metric in NEUTRON_AGENTS_METRICS:
                        self.gauge(
                            metric,
                            value,
                            tags=tags
                            + [
                                f'agent_id:{agent_id}',
                                f'agent_name:{agent_data["name"]}',
                                f'agent_host:{agent_data["host"]}',
                                f'agent_availability_zone:{agent_data.get("availability_zone", None)}',
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

    def _report_baremetal_domain_metrics(self, api, tags):
        try:
            self._report_baremetal_response_time(api, tags)
            self._report_baremetal_nodes(api, tags)
            self._report_baremetal_conductors(api, tags)
            return True
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting baremetal metrics: %s", e)
            self.service_check('openstack.ironic.api.up', AgentCheck.CRITICAL, tags)
            return False
        except Exception as e:
            self.warning("Exception while reporting baremetal metrics: %s", e)
            return False

    def _report_baremetal_response_time(self, api, tags):
        response_time = api.get_baremetal_response_time()
        self.log.debug("baremetal response time: %s", response_time)
        if response_time is not None:
            self.gauge('openstack.ironic.response_time', response_time, tags=tags)
            self.service_check('openstack.ironic.api.up', AgentCheck.OK, tags=tags)
        else:
            self.service_check('openstack.ironic.api.up', AgentCheck.UNKNOWN, tags=tags)

    def _report_baremetal_nodes(self, api, tags):
        nodes_data = api.get_baremetal_nodes()
        if nodes_data is not None:
            for node_data in nodes_data:
                is_up = node_data.get('is_up')
                node_tags = _create_baremetal_nodes_metric_tags(
                    node_data.get('node_name'),
                    node_data.get('node_uuid'),
                    node_data.get('conductor_group'),
                    node_data.get('power_state'),
                )
                all_tags = node_tags + tags
                self.gauge('openstack.ironic.node.up', value=is_up, tags=all_tags)
                self.gauge('openstack.ironic.node.count', value=1, tags=all_tags)

    def _report_baremetal_conductors(self, api, tags):
        conductors_data = api.get_baremetal_conductors()
        if conductors_data:
            for conductor_data in conductors_data:
                conductor_tags = _create_baremetal_conductors_metric_tags(
                    conductor_data.get('hostname'),
                    conductor_data.get('conductor_group'),
                )
                all_tags = conductor_tags + tags
                self.gauge('openstack.ironic.conductor.up', value=conductor_data.get('alive'), tags=all_tags)

    def _report_load_balancer_project_metrics(self, api, project_id, project_tags):
        try:
            self._report_load_balancer_loadbalancers(api, project_id, project_tags)
            self._report_load_balancer_listeners(api, project_id, project_tags)
            self._report_load_balancer_members(api, project_id, project_tags)
            self._report_load_balancer_healthmonitors(api, project_id, project_tags)
            self._report_load_balancer_pools(api, project_id, project_tags)
            self._report_load_balancer_amphorae(api, project_id, project_tags)

        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while reporting load balancer metrics: %s", e)
        except Exception as e:
            self.warning("Exception while reporting load balancer metrics: %s", e)

    def _report_load_balancer_domain_metrics(self, api, tags):
        try:
            self._report_load_balancer_response_time(api, tags)
            return True
        except HTTPError as e:
            # TODO: don't submit SC multiple times if failed
            self.warning(e)
            self.log.error("HTTPError while reporting load balancer metrics: %s", e)
            self.service_check('openstack.octavia.api.up', AgentCheck.CRITICAL, tags=tags)
            return False
        except Exception as e:
            self.warning("Exception while reporting load balancer metrics: %s", e)
            return False

    def _report_load_balancer_response_time(self, api, tags):
        response_time = api.get_load_balancer_response_time()
        self.log.debug("load balancer response time: %s", response_time)
        if response_time is not None:
            self.gauge('openstack.octavia.response_time', response_time, tags=tags)
            self.service_check('openstack.octavia.api.up', AgentCheck.OK, tags=tags)
        else:
            self.service_check('openstack.octavia.api.up', AgentCheck.UNKNOWN, tags=tags)

    def _report_load_balancer_loadbalancers(self, api, project_id, project_tags):
        loadbalancers_data = api.get_load_balancer_loadbalancers(project_id)
        if loadbalancers_data is not None:
            for loadbalancer_id, loadbalancer_data in loadbalancers_data.items():
                loadbalancer_tags = _create_load_balancer_loadbalancer_tags(loadbalancer_data)
                all_tags = loadbalancer_tags + project_tags  # TODO: add loadbalancer api tags

                # report status
                self.gauge(
                    "openstack.octavia.loadbalancer.admin_state_up",
                    value=int(loadbalancer_data.get("admin_state_up")),
                    tags=all_tags,
                )

                # loadbalancer statistics
                stats = api.get_load_balancer_loadbalancer_statistics(project_id, loadbalancer_id)
                if stats is not None:
                    self.gauge(
                        'openstack.octavia.loadbalancer.active_connections',
                        value=stats.get("active_connections"),
                        tags=all_tags,
                    )
                    self.gauge('openstack.octavia.loadbalancer.bytes_in', value=stats.get("bytes_in"), tags=all_tags)
                    self.gauge('openstack.octavia.loadbalancer.bytes_out', value=stats.get("bytes_out"), tags=all_tags)
                    self.gauge(
                        'openstack.octavia.loadbalancer.request_errors',
                        value=stats.get("request_errors"),
                        tags=all_tags,
                    )
                    self.gauge(
                        'openstack.octavia.loadbalancer.total_connections',
                        value=stats.get("total_connections"),
                        tags=all_tags,
                    )

    def _report_load_balancer_listeners(self, api, project_id, project_tags):
        loadbalancers_data = api.get_load_balancer_loadbalancers(project_id)
        listeners_data = api.get_load_balancer_listeners(project_id)
        if listeners_data is not None:
            for listener_id, listener_data in listeners_data.items():
                listener_tags = _create_load_balancer_listener_tags(listener_data, loadbalancers_data)
                all_tags = listener_tags + project_tags

                self.gauge(
                    'openstack.octavia.listener.connection_limit',
                    value=listener_data.get("connection_limit"),
                    tags=all_tags,
                )
                self.gauge(
                    'openstack.octavia.listener.timeout_client_data',
                    value=listener_data.get("timeout_client_data"),
                    tags=all_tags,
                )
                self.gauge(
                    'openstack.octavia.listener.timeout_member_connect',
                    value=listener_data.get("timeout_member_connect"),
                    tags=all_tags,
                )
                self.gauge(
                    'openstack.octavia.listener.timeout_member_data',
                    value=listener_data.get("timeout_member_data"),
                    tags=all_tags,
                )
                self.gauge(
                    'openstack.octavia.listener.timeout_tcp_inspect',
                    value=listener_data.get("timeout_tcp_inspect"),
                    tags=all_tags,
                )

                # listeners statistics
                stats = api.get_load_balancer_listener_statistics(project_id, listener_id)
                if stats is not None:
                    self.gauge(
                        'openstack.octavia.listener.active_connections',
                        value=stats.get("active_connections"),
                        tags=all_tags,
                    )
                    self.gauge('openstack.octavia.listener.bytes_in', value=stats.get("bytes_in"), tags=all_tags)
                    self.gauge('openstack.octavia.listener.bytes_out', value=stats.get("bytes_out"), tags=all_tags)
                    self.gauge(
                        'openstack.octavia.listener.request_errors',
                        value=stats.get("request_errors"),
                        tags=all_tags,
                    )
                    self.gauge(
                        'openstack.octavia.listener.total_connections',
                        value=stats.get("total_connections"),
                        tags=all_tags,
                    )

    def _report_load_balancer_members(self, api, project_id, project_tags):
        loadbalancers_data = api.get_load_balancer_loadbalancers(project_id)
        if loadbalancers_data is not None:
            for loadbalancer_id, loadbalancer_data in loadbalancers_data.items():
                pools_data = api.get_load_balancer_pools_by_loadbalancer(project_id, loadbalancer_id)
                if pools_data:
                    for pool_id, pool_data in pools_data.items():
                        members_data = api.get_load_balancer_members_by_pool(project_id, pool_id)
                        if members_data is not None:
                            for _, member_data in members_data.items():
                                member_tags = _create_load_balancer_member_tags(
                                    member_data, loadbalancer_data, pool_data
                                )
                                all_tags = member_tags + project_tags

                                # # report status
                                self.gauge(
                                    "openstack.octavia.member.admin_state_up",
                                    value=int(member_data.get("admin_state_up")),
                                    tags=all_tags,
                                )

                                self.gauge(
                                    'openstack.octavia.member.weight',
                                    value=member_data.get("weight"),
                                    tags=all_tags,
                                )

    def _report_load_balancer_healthmonitors(self, api, project_id, project_tags):
        pools_data = api.get_load_balancer_pools(project_id)
        if pools_data:
            for pool_id, pool_data in pools_data.items():
                healthmonitors_data = api.get_load_balancer_healthmonitors_by_pool(project_id, pool_id)

                if healthmonitors_data is not None:
                    for _, healthmonitor_data in healthmonitors_data.items():
                        healthmonitor_tags = _create_load_balancer_healthmonitor_tags(healthmonitor_data, pool_data)
                        all_tags = healthmonitor_tags + project_tags

                        # report status
                        self.gauge(
                            'openstack.octavia.healthmonitor.admin_state_up',
                            value=int(healthmonitor_data.get("admin_state_up")),
                            tags=all_tags,
                        )

                        self.gauge(
                            'openstack.octavia.healthmonitor.delay',
                            value=healthmonitor_data.get("delay"),
                            tags=all_tags,
                        )
                        self.gauge(
                            'openstack.octavia.healthmonitor.max_retries',
                            value=healthmonitor_data.get("max_retries"),
                            tags=all_tags,
                        )
                        self.gauge(
                            'openstack.octavia.healthmonitor.max_retries_down',
                            value=healthmonitor_data.get("max_retries_down"),
                            tags=all_tags,
                        )
                        self.gauge(
                            'openstack.octavia.healthmonitor.timeout',
                            value=healthmonitor_data.get("timeout"),
                            tags=all_tags,
                        )

    def _report_load_balancer_pools(self, api, project_id, project_tags):
        loadbalancers_data = api.get_load_balancer_loadbalancers(project_id)
        listeners_data = api.get_load_balancer_listeners(project_id)
        pools_data = api.get_load_balancer_pools(project_id)

        if pools_data:
            for pool_id, pool_data in pools_data.items():
                healthmonitors_data = api.get_load_balancer_healthmonitors_by_pool(project_id, pool_id)
                members_data = api.get_load_balancer_members_by_pool(project_id, pool_id)

                pool_tags = _create_load_balancer_pool_tags(
                    pool_data, loadbalancers_data, listeners_data, members_data, healthmonitors_data
                )

                all_tags = pool_tags + project_tags

                # report status
                self.gauge(
                    'openstack.octavia.pool.admin_state_up',
                    value=int(pool_data.get("admin_state_up")),
                    tags=all_tags,
                )

    def _report_load_balancer_amphorae(self, api, project_id, project_tags):
        loadbalancers_data = api.get_load_balancer_loadbalancers(project_id)
        listeners_data = api.get_load_balancer_listeners(project_id)
        amphorae_data = api.get_load_balancer_amphorae(project_id)

        if amphorae_data:
            for amphora_id, amphora_data in amphorae_data.items():
                stats = api.get_load_balancer_amphora_statistics(project_id, amphora_id)
                for _, amphora_stat in stats.items():
                    amphora_tags = _create_load_balancer_amphora_tags(
                        amphora_data, amphora_stat, loadbalancers_data, listeners_data
                    )

                    all_tags = amphora_tags + project_tags

                    self.gauge(
                        'openstack.octavia.amphora.active_connections',
                        value=amphora_stat.get("active_connections"),
                        tags=all_tags,
                    )
                    self.gauge('openstack.octavia.amphora.bytes_in', value=amphora_stat.get("bytes_in"), tags=all_tags)
                    self.gauge(
                        'openstack.octavia.amphora.bytes_out', value=amphora_stat.get("bytes_out"), tags=all_tags
                    )
                    self.gauge(
                        'openstack.octavia.amphora.request_errors',
                        value=amphora_stat.get("request_errors"),
                        tags=all_tags,
                    )
                    self.gauge(
                        'openstack.octavia.amphora.total_connections',
                        value=amphora_stat.get("total_connections"),
                        tags=all_tags,
                    )
