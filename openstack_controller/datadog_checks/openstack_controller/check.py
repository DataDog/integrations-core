# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from requests.exceptions import HTTPError

from datadog_checks.base import AgentCheck
from datadog_checks.openstack_controller.api.factory import make_api
from datadog_checks.openstack_controller.config import OpenstackConfig
from datadog_checks.openstack_controller.metrics import (
    HYPERVISOR_SERVICE_CHECK,
    LEGACY_NOVA_HYPERVISOR_LOAD_METRICS,
    LEGACY_NOVA_HYPERVISOR_METRICS,
    NOVA_HYPERVISOR_LOAD_METRICS,
    NOVA_HYPERVISOR_METRICS,
    NOVA_LATEST_LIMITS_METRICS,
    NOVA_LATEST_QUOTA_SETS_METRICS,
    NOVA_LATEST_SERVER_METRICS,
    NOVA_LIMITS_METRICS,
    NOVA_QUOTA_SETS_METRICS,
    NOVA_SERVER_METRICS,
    NOVA_SERVICE_METRICS,
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


def _create_nova_services_metric_tags(host, state, nova_id, status):
    tags = [
        f'nova_service_host:{host}',
        f'service_status:{status}',
    ]
    if nova_id:
        tags.append(f'nova_service_id:{nova_id}')

    if state:
        tags.append(f'nova_service_state:{state}')
    return tags


def _create_project_tags(project):
    return [f"project_id:{project.get('id')}", f"project_name:{project.get('name')}"]


class OpenStackControllerCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(OpenStackControllerCheck, self).__init__(name, init_config, instances)
        self.config = OpenstackConfig(self.log, self.instance)

    def check(self, _):
        tags = ['keystone_server:{}'.format(self.config.keystone_server_url)] + self.config.custom_tags
        try:
            api = make_api(self.config, self.log, self.http)
            api.create_connection()
            # Artificial metric introduced to distinguish between old and new openstack integrations
            self.gauge("openstack.controller", 1)
            self.service_check('openstack.keystone.api.up', AgentCheck.OK, tags=tags)
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while creating api: %s", e)
            self.service_check('openstack.keystone.api.up', AgentCheck.CRITICAL, message=str(e), tags=tags)
        except Exception as e:
            self.warning("Exception while creating api: %s", e)
            self.service_check('openstack.keystone.api.up', AgentCheck.CRITICAL, message=str(e), tags=tags)
            raise e
        else:
            self._report_metrics(api, tags)

    def _report_metrics(self, api, tags):
        projects = api.get_projects()
        self.log.debug("projects: %s", projects)
        for project in projects:
            self._report_project_metrics(api, project, tags)

    def _report_project_metrics(self, api, project, tags):
        project_id = project.get('id')
        project_name = project.get('name')
        self.log.debug("reporting metrics from project: [id:%s][name:%s]", project_id, project_name)
        project_tags = _create_project_tags(project)
        self._report_compute_metrics(api, project_id, tags + project_tags)
        self._report_network_metrics(api, project_id, tags + project_tags)
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
            self.service_check('openstack.nova.api.up', AgentCheck.CRITICAL, tags=project_tags)
        except Exception as e:
            self.warning("Exception while reporting compute metrics: %s", e)

    def _report_compute_response_time(self, api, project_id, project_tags):
        response_time = api.get_compute_response_time(project_id)
        self.log.debug("compute response_time: %s", response_time)
        if response_time is not None:
            self.gauge('openstack.nova.response_time', response_time, tags=project_tags)
            self.service_check('openstack.nova.api.up', AgentCheck.OK, tags=project_tags)
        else:
            self.service_check('openstack.nova.api.up', AgentCheck.UNKNOWN, tags=project_tags)

    def _report_compute_limits(self, api, project_id, project_tags):
        compute_limits = api.get_compute_limits(project_id)
        self.log.debug("compute_limits: %s", compute_limits)
        if compute_limits:
            for metric, value in compute_limits.items():
                if metric in NOVA_LIMITS_METRICS or metric in NOVA_LATEST_LIMITS_METRICS:
                    self.gauge(f'openstack.nova.limits.{metric}', value, tags=project_tags)

    def _report_compute_quotas(self, api, project_id, project_tags):
        compute_quotas = api.get_compute_quota_set(project_id)
        self.log.debug("compute_quotas: %s", compute_quotas)
        if compute_quotas:
            for metric, value in compute_quotas.items():
                if metric in NOVA_QUOTA_SETS_METRICS or metric in NOVA_LATEST_QUOTA_SETS_METRICS:
                    self.gauge(f'openstack.nova.quota_set.{metric}', value, tags=project_tags)

    def _report_compute_services(self, api, project_id, project_tags):
        compute_services = api.get_compute_services(project_id)
        self.log.debug("compute_services: %s", compute_services)
        if compute_services is not None:
            for compute_service in compute_services:
                service_tags = _create_nova_services_metric_tags(
                    compute_service.get('host'),
                    compute_service.get('state'),
                    compute_service.get('service_id'),
                    compute_service.get('status'),
                )
                all_tags = project_tags + service_tags
                binary = compute_service.get('binary')
                is_up = compute_service.get('is_up')
                if binary in NOVA_SERVICE_METRICS:
                    self.gauge(f'openstack.nova.services.{binary}.up', is_up, tags=all_tags)

    def _report_compute_servers(self, api, project_id, project_tags):
        compute_servers = api.get_compute_servers(project_id)
        self.log.debug("compute_servers: %s", compute_servers)
        if compute_servers:
            for server_id, server_data in compute_servers.items():
                for metric, value in server_data['metrics'].items():
                    if metric in NOVA_SERVER_METRICS or metric in NOVA_LATEST_SERVER_METRICS:
                        self.gauge(
                            f'openstack.nova.server.{metric}',
                            value,
                            tags=project_tags + [f'server_id:{server_id}', f'server_name:{server_data["name"]}'],
                        )

    def _report_compute_flavors(self, api, project_id, project_tags):
        compute_flavors = api.get_compute_flavors(project_id)
        self.log.debug("compute_flavors: %s", compute_flavors)
        if compute_flavors:
            for flavor_id, flavor_data in compute_flavors.items():
                for metric, value in flavor_data['metrics'].items():
                    self.gauge(
                        f'openstack.nova.flavor.{metric}',
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
            self._report_hypervisor_metric(metric, value, hypervisor_tags)
            if self.config.report_legacy_metrics:
                self._report_hypervisor_legacy_metric(metric, value, hypervisor_tags)

    def _report_hypervisor_metric(self, metric, value, tags):
        if metric in NOVA_HYPERVISOR_METRICS:
            self.gauge(f'openstack.nova.hypervisor.{metric}', value, tags=tags)
        elif self.config.collect_hypervisor_load and metric in NOVA_HYPERVISOR_LOAD_METRICS:
            self.gauge(f'openstack.nova.hypervisor.{metric}', value, tags=tags)

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
                self.gauge('openstack.ironic.nodes.up', value=is_up, tags=all_tags)
                self.gauge('openstack.ironic.nodes.count', value=1, tags=all_tags)

    def _report_baremetal_conductors(self, api, project_id, project_tags):
        conductors_data = api.get_baremetal_conductors(project_id)
        if conductors_data:
            for conductor_data in conductors_data:
                conductor_tags = _create_baremetal_conductors_metric_tags(
                    conductor_data.get('hostname'),
                    conductor_data.get('conductor_group'),
                )
                all_tags = conductor_tags + project_tags
                self.gauge('openstack.ironic.conductors.up', value=conductor_data.get('alive'), tags=all_tags)

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
