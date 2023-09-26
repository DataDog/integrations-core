# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    NEUTRON_AGENTS_COUNT,
    NEUTRON_AGENTS_METRICS,
    NEUTRON_AGENTS_METRICS_PREFIX,
    NEUTRON_AGENTS_TAGS,
    NEUTRON_QUOTAS_METRICS,
    NEUTRON_QUOTAS_METRICS_PREFIX,
    NEUTRON_QUOTAS_TAGS,
    NEUTRON_RESPONSE_TIME,
    NEUTRON_SERVICE_CHECK,
    get_metrics_and_tags,
)


class Network(Component):
    component_type = Component.Type.NETWORK
    service_check_id = NEUTRON_SERVICE_CHECK

    def __init__(self, check):
        super(Network, self).__init__(self, check)

    @Component.register_global_metrics(Component.Type.NETWORK)
    @Component.http_error(service_check=True)
    def _report_response_time(self, tags):
        self.check.log.debug("reporting `%s` response time", Component.Type.NETWORK.value)
        response_time = self.check.api.get_response_time(Component.Type.NETWORK)
        self.check.log.debug("`%s` response time: %s", Component.Type.NETWORK.value, response_time)
        self.check.gauge(NEUTRON_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_global_metrics(Component.Type.NETWORK)
    @Component.http_error()
    def _report_agents(self, tags):
        data = self.check.api.get_network_agents()
        for item in data:
            agent = get_metrics_and_tags(
                item,
                tags=NEUTRON_AGENTS_TAGS,
                prefix=NEUTRON_AGENTS_METRICS_PREFIX,
                metrics=NEUTRON_AGENTS_METRICS,
                lambda_name=lambda key: 'name' if key == 'binary' else key,
            )
            self.check.log.debug("agent: %s", agent)
            self.check.gauge(NEUTRON_AGENTS_COUNT, 1, tags=tags + agent['tags'])
            for metric, value in agent['metrics'].items():
                self.check.gauge(metric, value, tags=tags + agent['tags'])

    @Component.register_project_metrics(Component.Type.NETWORK)
    @Component.http_error()
    def _report_quotas(self, project_id, tags):
        item = self.check.api.get_network_quotas(project_id)
        quota = get_metrics_and_tags(
            item,
            tags=NEUTRON_QUOTAS_TAGS,
            prefix=NEUTRON_QUOTAS_METRICS_PREFIX,
            metrics=NEUTRON_QUOTAS_METRICS,
        )
        self.check.log.debug("quota: %s", quota)
        for metric, value in quota['metrics'].items():
            self.check.gauge(metric, value, tags=tags + quota['tags'])
