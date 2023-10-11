# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    NEUTRON_AGENTS_COUNT,
    NEUTRON_AGENTS_METRICS,
    NEUTRON_AGENTS_METRICS_PREFIX,
    NEUTRON_AGENTS_TAGS,
    NEUTRON_NETWORK_COUNT,
    NEUTRON_NETWORK_METRICS,
    NEUTRON_NETWORK_METRICS_PREFIX,
    NEUTRON_NETWORK_TAGS,
    NEUTRON_QUOTA_METRICS,
    NEUTRON_QUOTA_METRICS_PREFIX,
    NEUTRON_QUOTA_TAGS,
    NEUTRON_RESPONSE_TIME,
    NEUTRON_SERVICE_CHECK,
    get_metrics_and_tags,
)


class Network(Component):
    ID = Component.Id.NETWORK
    TYPES = Component.Types.NETWORK
    SERVICE_CHECK = NEUTRON_SERVICE_CHECK

    def __init__(self, check):
        super(Network, self).__init__(check)

    @Component.register_global_metrics(ID)
    @Component.http_error(report_service_check=True)
    def _report_response_time(self, tags):
        self.check.log.debug("reporting `%s` response time", Network.ID.value)
        response_time = self.check.api.get_response_time(Network.TYPES.value)
        self.check.log.debug("`%s` response time: %s", Network.ID.value, response_time)
        self.check.gauge(NEUTRON_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_global_metrics(ID)
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

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_networks(self, project_id, tags, component_config):
        config_networks = component_config.get('networks', {})
        self.check.log.debug("config_networks: %s", config_networks)
        collect_networks = config_networks.get('collect', True)
        if collect_networks:
            data = self.check.api.get_network_networks(project_id)
            for item in data:
                network = get_metrics_and_tags(
                    item,
                    tags=NEUTRON_NETWORK_TAGS,
                    prefix=NEUTRON_NETWORK_METRICS_PREFIX,
                    metrics=NEUTRON_NETWORK_METRICS,
                )
                self.check.log.debug("network: %s", network)
                self.check.gauge(NEUTRON_NETWORK_COUNT, 1, tags=tags + network['tags'])
                for metric, value in network['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + network['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_quotas(self, project_id, tags, project_config):
        item = self.check.api.get_network_quota(project_id)
        quota = get_metrics_and_tags(
            item,
            tags=NEUTRON_QUOTA_TAGS,
            prefix=NEUTRON_QUOTA_METRICS_PREFIX,
            metrics=NEUTRON_QUOTA_METRICS,
        )
        self.check.log.debug("quota: %s", quota)
        for metric, value in quota['metrics'].items():
            self.check.gauge(metric, value, tags=tags + quota['tags'])
