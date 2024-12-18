# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    HEAT_RESPONSE_TIME,
    HEAT_SERVICE_CHECK,
    HEAT_STACK_COUNT,
    HEAT_STACK_PREFIX,
    HEAT_STACK_TAGS,
    get_metrics_and_tags,
)


class Heat(Component):
    ID = Component.Id.HEAT
    TYPES = Component.Types.HEAT
    SERVICE_CHECK = HEAT_SERVICE_CHECK

    def __init__(self, check):
        super(Heat, self).__init__(check)

    @Component.register_global_metrics(ID)
    @Component.http_error(report_service_check=True)
    def _report_response_time(self, global_components_config, tags):
        self.check.log.debug("reporting `%s` response time", Heat.ID.value)
        response_time = self.check.api.get_response_time(Heat.TYPES.value, is_heat=True)
        self.check.log.debug("`%s` response time: %s", Heat.ID.value, response_time)
        self.check.gauge(HEAT_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_stacks(self, project_id, tags, config):
        report_stacks = config.get('stacks', True)
        if report_stacks:
            data = self.check.api.get_heat_stacks(project_id)
            self.check.log.debug("stacks: %s", data)
            for item in data:
                stack = get_metrics_and_tags(
                    item,
                    tags=HEAT_STACK_TAGS,
                    prefix=HEAT_STACK_PREFIX,
                    metrics={},
                )
                self.check.gauge(HEAT_STACK_COUNT, 1, tags=tags + stack['tags'])
                self.check.log.debug("stack: %s", stack)
                for metric, value in stack['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + stack['tags'])
