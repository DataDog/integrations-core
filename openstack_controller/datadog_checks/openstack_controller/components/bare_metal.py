# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.openstack_controller.components.component import Component
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
    def _report_response_time(self, tags):
        self.check.log.debug("reporting `%s` response time", BareMetal.ID.value)
        response_time = self.check.api.get_response_time(BareMetal.TYPES.value)
        self.check.log.debug("`%s` response time: %s", BareMetal.ID.value, response_time)
        self.check.gauge(IRONIC_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_nodes(self, tags):
        data = self.check.api.get_baremetal_nodes()
        for item in data:
            node = get_metrics_and_tags(
                item,
                tags=IRONIC_NODE_TAGS,
                prefix=IRONIC_NODE_METRICS_PREFIX,
                metrics=IRONIC_NODE_METRICS,
                lambda_name=lambda key: 'up' if key == 'power_state' else key,
                lambda_value=lambda key, value, item=item: (
                    item.get('power_state') == 'power on' and item.get('maintenance') is False
                )
                if key == 'power_state'
                else value,
            )
            self.check.log.debug("node: %s", node)
            self.check.gauge(IRONIC_NODE_COUNT, 1, tags=tags + node['tags'])
            for metric, value in node['metrics'].items():
                self.check.gauge(metric, value, tags=tags + node['tags'])

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_conductors(self, tags):
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
