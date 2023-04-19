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
    LEGACY_NOVA_HYPERVISOR_LOAD_METRICS,
    LEGACY_NOVA_HYPERVISOR_METRICS,
    NOVA_FLAVOR_METRICS,
    NOVA_HYPERVISOR_LOAD_METRICS,
    NOVA_HYPERVISOR_METRICS,
    NOVA_LIMITS_METRICS,
    NOVA_LIMITS_METRICS_PREFIX,
    NOVA_QUOTA_SETS_METRICS,
    NOVA_QUOTA_SETS_METRICS_PREFIX,
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


def _create_project_tags(project):
    return [f"project_id:{project.get('id')}", f"project_name:{project.get('name')}"]


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
                long_metric_name = f'{NOVA_LIMITS_METRICS_PREFIX}.{metric}'
                if long_metric_name in NOVA_LIMITS_METRICS:
                    self.gauge(long_metric_name, value, tags=project_tags)
                else:
                    self.log.warning("%s metric not reported as nova limits metric", long_metric_name)

    def _report_compute_quotas(self, api, project_id, project_tags):
        compute_quotas = api.get_compute_quota_set(project_id)
        self.log.debug("compute_quotas: %s", compute_quotas)
        if compute_quotas:
            for metric, value in compute_quotas['metrics'].items():
                long_metric_name = f'{NOVA_QUOTA_SETS_METRICS_PREFIX}.{metric}'
                tags = project_tags + [f'quota_id:{compute_quotas["id"]}']
                if long_metric_name in NOVA_QUOTA_SETS_METRICS:
                    self.gauge(long_metric_name, value, tags=tags)
                else:
                    self.log.warning("%s metric not reported as nova quota metric", long_metric_name)

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
                        + [
                            f'server_id:{server_id}',
                            f'server_name:{server_data["name"]}',
                            f'server_status:{server_data["status"]}',
                            f'hypervisor:{server_data["hypervisor_hostname"]}',
                            f'flavor_name:{server_data["flavor_name"]}',
                        ],
                    )
                for metric, value in server_data['metrics'].items():
                    long_metric_name = f'openstack.nova.server.{metric}'
                    if long_metric_name in NOVA_SERVER_METRICS:
                        self.gauge(
                            long_metric_name,
                            value,
                            tags=project_tags
                            + [
                                f'server_id:{server_id}',
                                f'server_name:{server_data["name"]}',
                                f'server_status:{server_data["status"]}',
                                f'hypervisor:{server_data["hypervisor_hostname"]}',
                                f'flavor_name:{server_data["flavor_name"]}',
                            ],
                        )

    def _report_compute_flavors(self, api, project_id, project_tags):
        compute_flavors = api.get_compute_flavors(project_id)
        self.log.debug("compute_flavors: %s", compute_flavors)
        if compute_flavors:
            for flavor_id, flavor_data in compute_flavors.items():
                for metric, value in flavor_data['metrics'].items():
                    long_metric_name = f'openstack.nova.flavor.{metric}'
                    if long_metric_name in NOVA_FLAVOR_METRICS:
                        self.gauge(
                            long_metric_name,
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
            'openstack.nova.hypervisor.up',
            HYPERVISOR_SERVICE_CHECK.get(state, AgentCheck.UNKNOWN),
            hostname=name,
            tags=hypervisor_tags,
        )

    def _report_hypervisor_metrics(self, hypervisor_data, hypervisor_tags):
        for metric, value in hypervisor_data.get('metrics', {}).items():
            long_metric_name = f'openstack.nova.hypervisor.{metric}'
            self._report_hypervisor_metric(long_metric_name, value, hypervisor_tags)
            if self.config.report_legacy_metrics:
                self._report_hypervisor_legacy_metric(long_metric_name, value, hypervisor_tags)
        self._report_hypervisor_metric(
            'openstack.nova.hypervisor.up', 1 if hypervisor_data.get('state') == 'up' else 0, hypervisor_tags
        )

    def _report_hypervisor_metric(self, long_metric_name, value, tags):
        if long_metric_name in NOVA_HYPERVISOR_METRICS:
            self.gauge(long_metric_name, value, tags=tags)
        elif self.config.collect_hypervisor_load and long_metric_name in NOVA_HYPERVISOR_LOAD_METRICS:
            self.gauge(long_metric_name, value, tags=tags)

    def _report_hypervisor_legacy_metric(self, metric, value, tags):
        if metric in LEGACY_NOVA_HYPERVISOR_METRICS:
            self.gauge(f'openstack.nova.{metric}', value, tags=tags)
        elif self.config.collect_hypervisor_load and metric in LEGACY_NOVA_HYPERVISOR_LOAD_METRICS:
            self.gauge(f'openstack.nova.{LEGACY_NOVA_HYPERVISOR_LOAD_METRICS[metric]}', value, tags=tags)

    def _report_network_metrics(self, api, project_id, project_tags):
        try:
            self._report_network_response_time(api, project_id, project_tags)
            self._report_network_quotas(api, project_id, project_tags)
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
        if network_quotas:
            for metric, value in network_quotas.items():
                self.gauge(f'openstack.neutron.quotas.{metric}', value, tags=project_tags)

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
