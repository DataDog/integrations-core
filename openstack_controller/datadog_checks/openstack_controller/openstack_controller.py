# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from requests.exceptions import HTTPError

from datadog_checks.base import AgentCheck
from datadog_checks.openstack_controller.api.factory import make_api


class OpenStackControllerCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(OpenStackControllerCheck, self).__init__(name, init_config, instances)

    def check(self, instance):
        try:
            api = make_api(self.log, instance, self.http)
            api.create_connection()
            self.service_check('openstack.keystone.api.up', AgentCheck.OK)
        except HTTPError as e:
            self.log.error("HTTPError while creating api: %s", e)
            self.service_check('openstack.keystone.api.up', AgentCheck.CRITICAL)
        except Exception as e:
            self.log.error("Exception while creating api: %s", e)
            raise e
        else:
            self._report_metrics(api)

    def _report_metrics(self, api):
        # Artificial metric introduced to distinguish between old and new openstack integrations
        self.gauge("openstack.controller", 1)
        projects = api.get_projects()
        self.log.debug("projects: %s", projects)
        for project in projects:
            self._report_project_metrics(api, project)

    def _report_project_metrics(self, api, project):
        self.log.debug("reporting metrics from project: [id:%s][name:%s]", project['id'], project['name'])
        tags = [f"project_id:{project['id']}", f"project_name:{project['name']}"]
        # compute
        response_time = api.get_compute_response_time(project)
        if response_time:
            self.service_check('openstack.nova.api.up', AgentCheck.OK)
            self.log.debug("response_time: %s", response_time)
            self.gauge('openstack.nova.response_time', response_time, tags=tags)
            compute_limits = api.get_compute_limits(project)
            self.log.debug("compute_limits: %s", compute_limits)
            for metric, value in compute_limits.items():
                self.gauge(f'openstack.nova.limits.{metric}', value, tags=tags)
            compute_quotas = api.get_compute_quotas(project)
            self.log.debug("compute_quotas: %s", compute_quotas)
            for metric, value in compute_quotas.items():
                self.gauge(f'openstack.nova.quota_sets.{metric}', value, tags=tags)
            compute_servers = api.get_compute_servers(project)
            self.log.debug("compute_servers: %s", compute_servers)
            for server_id, server_data in compute_servers.items():
                for metric, value in server_data['metrics'].items():
                    self.gauge(
                        f'openstack.nova.servers.{metric}',
                        value,
                        tags=tags + [f'server_id:{server_id}', f'server_name:{server_data["name"]}'],
                    )
            compute_flavors = api.get_compute_flavors(project)
            self.log.debug("compute_flavors: %s", compute_flavors)
            for flavor_id, flavor_data in compute_flavors.items():
                for metric, value in flavor_data['metrics'].items():
                    self.gauge(
                        f'openstack.nova.flavors.{metric}',
                        value,
                        tags=tags + [f'flavor_id:{flavor_id}', f'flavor_name:{flavor_data["name"]}'],
                    )
        else:
            self.service_check('openstack.nova.api.up', AgentCheck.CRITICAL, tags=tags)
        # network
        response_time = api.get_network_response_time(project)
        if response_time:
            self.service_check('openstack.neutron.api.up', AgentCheck.OK)
            self.log.debug("response_time: %s", response_time)
            self.gauge('openstack.neutron.response_time', response_time, tags=tags)
            networking_quotas = api.get_networking_quotas(project)
            self.log.debug("networking_quotas: %s", networking_quotas)
            for metric, value in networking_quotas.items():
                self.gauge(f'openstack.neutron.quotas.{metric}', value, tags=tags)
        else:
            self.service_check('openstack.neutron.api.up', AgentCheck.CRITICAL, tags=tags)
        # baremetal
        response_time = api.get_baremetal_response_time(project)
        if response_time:
            self.service_check('openstack.ironic.api.up', AgentCheck.OK, tags=tags)
            self.log.debug("response_time: %s", response_time)
            self.gauge('openstack.baremetal.response_time', response_time, tags=tags)
        else:
            self.service_check('openstack.ironic.api.up', AgentCheck.CRITICAL, tags=tags)
