# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.config import normalize_discover_config_include
from datadog_checks.openstack_controller.metrics import (
    IRONIC_CONDUCTOR_COUNT,
    IRONIC_CONDUCTOR_METRICS,
    IRONIC_CONDUCTOR_METRICS_PREFIX,
    IRONIC_CONDUCTOR_TAGS,
    IRONIC_NODE_COUNT,
    IRONIC_NODE_METRICS,
    IRONIC_NODE_METRICS_PREFIX,
    IRONIC_NODE_TAGS,
    IRONIC_RESPONSE_TIME,
    IRONIC_SERVICE_CHECK,
    get_metrics_and_tags,
)


class BareMetal(Component):
    ID = Component.Id.BAREMETAL
    TYPES = Component.Types.BAREMETAL
    SERVICE_CHECK = IRONIC_SERVICE_CHECK

    def __init__(self, check):
        super(BareMetal, self).__init__(check)

    @Component.register_global_metrics(ID)
    @Component.http_error(report_service_check=True)
    def _report_response_time(self, global_components_config, tags):
        self.check.log.debug("reporting `%s` response time", BareMetal.ID.value)
        response_time = self.check.api.get_response_time(BareMetal.TYPES.value)
        self.check.log.debug("`%s` response time: %s", BareMetal.ID.value, response_time)
        self.check.gauge(IRONIC_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_nodes(self, config, tags):
        report_nodes = True
        config_nodes = config.get('nodes', {})
        if isinstance(config_nodes, bool):
            report_nodes = config_nodes
            config_nodes = {}
        if report_nodes:
            nodes_discovery = None
            if config_nodes:
                config_nodes_include = normalize_discover_config_include(config_nodes, ["name"])
                self.check.log.debug("config_nodes_include: %s", config_nodes_include)
                if config_nodes_include:
                    nodes_discovery = Discovery(
                        lambda: self.check.api.get_baremetal_nodes(),
                        limit=config_nodes.get('limit'),
                        include=config_nodes_include,
                        exclude=config_nodes.get('exclude'),
                        interval=config_nodes.get('interval'),
                        key=lambda server: server.get('name'),
                    )
            if nodes_discovery:
                discovered_nodes = list(nodes_discovery.get_items())
            else:
                discovered_nodes = [
                    (None, node.get('name'), node, None) for node in self.check.api.get_baremetal_nodes()
                ]
        for _pattern, _item_name, item, item_config in discovered_nodes:
            self.check.log.debug("item: %s", item)
            self.check.log.debug("item_config: %s", item_config)
            node = get_metrics_and_tags(
                item,
                tags=IRONIC_NODE_TAGS,
                prefix=IRONIC_NODE_METRICS_PREFIX,
                metrics=IRONIC_NODE_METRICS,
                lambda_name=lambda key: 'up' if key == 'power_state' else key,
                lambda_value=lambda key, value, item=item: (
                    (item.get('power_state') == 'power on' and item.get('maintenance') is False)
                    if key == 'power_state'
                    else value
                ),
            )
            self.check.log.debug("node: %s", node)
            self.check.gauge(IRONIC_NODE_COUNT, 1, tags=tags + node['tags'], hostname=item['uuid'])
            for metric, value in node['metrics'].items():
                self.check.gauge(metric, value, tags=tags + node['tags'], hostname=item['uuid'])
            self.check.external_tags.append((item['uuid'], {'openstack': ['host_type:baremetal']}))

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_conductors(self, config, tags):
        report_conductors = config.get('conductors', True)
        if report_conductors:
            data = self.check.api.get_baremetal_conductors()
            for item in data:
                conductor = get_metrics_and_tags(
                    item,
                    tags=IRONIC_CONDUCTOR_TAGS,
                    prefix=IRONIC_CONDUCTOR_METRICS_PREFIX,
                    metrics=IRONIC_CONDUCTOR_METRICS,
                    lambda_name=lambda key: 'up' if key == 'alive' else key,
                )
                self.check.log.debug("conductor: %s", conductor)
                self.check.gauge(IRONIC_CONDUCTOR_COUNT, 1, tags=tags + conductor['tags'])
                for metric, value in conductor['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + conductor['tags'])
