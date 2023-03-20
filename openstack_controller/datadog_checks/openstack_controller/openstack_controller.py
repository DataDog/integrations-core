# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from requests.exceptions import HTTPError

from datadog_checks.base import AgentCheck
from datadog_checks.openstack_controller.api.factory import make_api

LEGACY_NOVA_HYPERVISOR_METRICS = [
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


class OpenStackControllerCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(OpenStackControllerCheck, self).__init__(name, init_config, instances)

    def check(self, _instance):
        self.log.debug(self.instance)
        try:
            api = make_api(self.log, self.instance, self.http)
            api.create_connection()
            # Artificial metric introduced to distinguish between old and new openstack integrations
            self.gauge("openstack.controller", 1)
            self.service_check('openstack.keystone.api.up', AgentCheck.OK)
        except HTTPError as e:
            self.warning(e)
            self.log.error("HTTPError while creating api: %s", e)
            self.service_check('openstack.keystone.api.up', AgentCheck.CRITICAL, message=str(e))
            self.service_check('openstack.nova.api.up', AgentCheck.UNKNOWN)
            self.service_check('openstack.neutron.api.up', AgentCheck.UNKNOWN)
            self.service_check('openstack.ironic.api.up', AgentCheck.UNKNOWN)
            self.service_check('openstack.octavia.api.up', AgentCheck.UNKNOWN)
        except Exception as e:
            self.log.error("Exception while creating api: %s", e)
            self.service_check('openstack.keystone.api.up', AgentCheck.CRITICAL)
            self.service_check('openstack.nova.api.up', AgentCheck.UNKNOWN)
            self.service_check('openstack.neutron.api.up', AgentCheck.UNKNOWN)
            self.service_check('openstack.ironic.api.up', AgentCheck.UNKNOWN)
            self.service_check('openstack.octavia.api.up', AgentCheck.UNKNOWN)
            raise e
        else:
            self._report_metrics(api)

    def _report_metrics(self, api):
        projects = api.get_projects()
        self.log.debug("projects: %s", projects)
        for project in projects:
            self._report_project_metrics(api, project)

    def _report_project_metrics(self, api, project):
        self.log.debug("reporting metrics from project: [id:%s][name:%s]", project['id'], project['name'])
        self._report_compute_metrics(api, project)
        self._report_network_metrics(api, project)
        self._report_baremetal_metrics(api, project)
        self._report_load_balancer_metrics(api, project)
        if self.instance.get('report_legacy_metrics', True):
            self._report_legacy_metrics(api, project)

    def _report_compute_metrics(self, api, project):
        tags = [f"project_id:{project['id']}", f"project_name:{project['name']}"]
        response_time = api.get_compute_response_time(project)
        if response_time:
            self.service_check('openstack.nova.api.up', AgentCheck.OK)
            self.log.debug("response_time: %s", response_time)
            self.gauge('openstack.nova.response_time', response_time, tags=tags)
            compute_limits = api.get_compute_limits(project)
            self.log.debug("compute_limits: %s", compute_limits)
            for metric, value in compute_limits.items():
                self.gauge(f'openstack.nova.limits.{metric}', value, tags=tags)
            compute_quotas = api.get_compute_quota_set(project)
            self.log.debug("compute_quotas: %s", compute_quotas)
            for metric, value in compute_quotas.items():
                self.gauge(f'openstack.nova.quota_set.{metric}', value, tags=tags)
            compute_servers = api.get_compute_servers(project)
            self.log.debug("compute_servers: %s", compute_servers)
            for server_id, server_data in compute_servers.items():
                for metric, value in server_data['metrics'].items():
                    self.gauge(
                        f'openstack.nova.server.{metric}',
                        value,
                        tags=tags + [f'server_id:{server_id}', f'server_name:{server_data["name"]}'],
                    )
            compute_flavors = api.get_compute_flavors(project)
            self.log.debug("compute_flavors: %s", compute_flavors)
            for flavor_id, flavor_data in compute_flavors.items():
                for metric, value in flavor_data['metrics'].items():
                    self.gauge(
                        f'openstack.nova.flavor.{metric}',
                        value,
                        tags=tags + [f'flavor_id:{flavor_id}', f'flavor_name:{flavor_data["name"]}'],
                    )
            compute_hypervisors_detail = api.get_compute_hypervisors_detail(project)
            self.log.debug("compute_hypervisors_detail: %s", compute_hypervisors_detail)
            for hypervisor_id, hypervisor_data in compute_hypervisors_detail.items():
                for metric, value in hypervisor_data['metrics'].items():
                    self.gauge(
                        f'openstack.nova.hypervisor.{metric}',
                        value,
                        tags=tags
                        + [f'hypervisor_id:{hypervisor_id}', f'hypervisor_hostname:{hypervisor_data["name"]}'],
                    )
        else:
            self.service_check('openstack.nova.api.up', AgentCheck.CRITICAL)

    def _report_network_metrics(self, api, project):
        tags = [f"project_id:{project['id']}", f"project_name:{project['name']}"]
        response_time = api.get_network_response_time(project)
        if response_time:
            self.service_check('openstack.neutron.api.up', AgentCheck.OK)
            self.log.debug("response_time: %s", response_time)
            self.gauge('openstack.neutron.response_time', response_time, tags=tags)
            network_quotas = api.get_network_quotas(project)
            self.log.debug("network_quotas: %s", network_quotas)
            for metric, value in network_quotas.items():
                self.gauge(f'openstack.neutron.quotas.{metric}', value, tags=tags)
        else:
            self.service_check('openstack.neutron.api.up', AgentCheck.CRITICAL)

    def _report_baremetal_metrics(self, api, project):
        tags = [f"project_id:{project['id']}", f"project_name:{project['name']}"]
        response_time = api.get_baremetal_response_time(project)
        if response_time:
            self.service_check('openstack.ironic.api.up', AgentCheck.OK)
            self.log.debug("response_time: %s", response_time)
            self.gauge('openstack.ironic.response_time', response_time, tags=tags)
        else:
            self.service_check('openstack.ironic.api.up', AgentCheck.CRITICAL)

    def _report_load_balancer_metrics(self, api, project):
        tags = [f"project_id:{project['id']}", f"project_name:{project['name']}"]
        response_time = api.get_load_balancer_response_time(project)
        if response_time:
            self.service_check('openstack.octavia.api.up', AgentCheck.OK)
            self.log.debug("response_time: %s", response_time)
            self.gauge('openstack.octavia.response_time', response_time, tags=tags)
        else:
            self.service_check('openstack.octavia.api.up', AgentCheck.CRITICAL)

    def _report_legacy_metrics(self, api, project):
        tags = [f"project_name:{project['name']}"]
        compute_hypervisors_detail = api.get_compute_hypervisors_detail(project)
        self.log.debug("compute_hypervisors_detail: %s", compute_hypervisors_detail)
        for hypervisor_id, hypervisor_data in compute_hypervisors_detail.items():
            state = hypervisor_data.get('state')
            if not state:
                self.service_check('openstack.nova.hypervisor.up', AgentCheck.UNKNOWN, hostname=hypervisor_data["name"])
            elif state != "up":
                self.service_check(
                    'openstack.nova.hypervisor.up', AgentCheck.CRITICAL, hostname=hypervisor_data["name"]
                )
            else:
                self.service_check('openstack.nova.hypervisor.up', AgentCheck.OK, hostname=hypervisor_data["name"])
            for metric, value in hypervisor_data['metrics'].items():
                if metric in LEGACY_NOVA_HYPERVISOR_METRICS:
                    self.gauge(
                        f'openstack.nova.{metric}',
                        value,
                        tags=tags
                        + [
                            f'hypervisor_id:{hypervisor_id}',
                            f'hypervisor:{hypervisor_data["name"]}',
                            f'virt_type:{hypervisor_data["type"]}',
                            f'status:{hypervisor_data["status"]}',
                        ],
                    )
