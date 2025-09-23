# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    SWIFT_CONTAINER_COUNT,
    SWIFT_CONTAINER_METRICS,
    SWIFT_CONTAINER_PREFIX,
    SWIFT_CONTAINER_TAGS,
    SWIFT_RESPONSE_TIME,
    SWIFT_SERVICE_CHECK,
    get_metrics_and_tags,
)


class Swift(Component):
    ID = Component.Id.SWIFT
    TYPES = Component.Types.SWIFT
    SERVICE_CHECK = SWIFT_SERVICE_CHECK

    def __init__(self, check):
        super(Swift, self).__init__(check)

    @Component.register_global_metrics(ID)
    @Component.http_error(report_service_check=True)
    def _report_response_time(self, global_components_config, tags):
        self.check.log.debug("reporting `%s` response time", Swift.ID.value)
        response_time = self.check.api.get_response_time(Swift.TYPES.value, remove_project_id=False)
        self.check.log.debug("`%s` response time: %s", Swift.ID.value, response_time)
        self.check.gauge(SWIFT_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_containers(self, project_id, tags, config):
        report_containers = config.get('containers', True)
        if report_containers:
            data = self.check.api.get_swift_containers(project_id)
            self.check.log.debug("containers: %s", data)
            for item in data:
                container = get_metrics_and_tags(
                    item,
                    tags=SWIFT_CONTAINER_TAGS,
                    prefix=SWIFT_CONTAINER_PREFIX,
                    metrics=SWIFT_CONTAINER_METRICS,
                )
                self.check.log.debug("container: %s", container)
                self.check.gauge(SWIFT_CONTAINER_COUNT, 1, tags=tags + container['tags'])
                for metric, value in container['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + container['tags'])
