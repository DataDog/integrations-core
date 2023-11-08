# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.config import normalize_discover_config_include
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
    def _report_response_time(self, global_components_config, tags):
        self.check.log.debug("reporting `%s` response time", Network.ID.value)
        response_time = self.check.api.get_response_time(Network.TYPES.value)
        self.check.log.debug("`%s` response time: %s", Network.ID.value, response_time)
        self.check.gauge(NEUTRON_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_agents(self, config, tags):
        report_agents = config.get('agents', True)
        if report_agents:
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
    def _report_networks(self, project_id, tags, config):
        report_networks = True
        config_networks = config.get('networks', {})
        if isinstance(config_networks, bool):
            report_networks = config_networks
            config_networks = {}
        if report_networks:
            networks_discovery = None
            if config_networks:
                config_networks_include = normalize_discover_config_include(config_networks, ["name"])
                self.check.log.debug("config_networks_include: %s", config_networks_include)
                if config_networks_include:
                    networks_discovery = Discovery(
                        lambda: self.check.api.get_network_networks(project_id),
                        limit=config_networks.get('limit'),
                        include=config_networks_include,
                        exclude=config_networks.get('exclude'),
                        interval=config_networks.get('interval'),
                        key=lambda network: network.get('name'),
                    )
            if networks_discovery:
                discovered_networks = list(networks_discovery.get_items())
            else:
                discovered_networks = [
                    (None, network.get('name'), network, None)
                    for network in self.check.api.get_network_networks(project_id)
                ]
            for _pattern, _item_name, item, _item_config in discovered_networks:
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
    def _report_quotas(self, project_id, tags, config):
        report_quotas = config.get('quotas', True)
        if report_quotas:
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
