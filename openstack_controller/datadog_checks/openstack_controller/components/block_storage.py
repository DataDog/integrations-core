# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    CINDER_RESPONSE_TIME,
    CINDER_SERVICE_CHECK,
    CINDER_VOLUME_COUNT,
    CINDER_VOLUME_TAGS,
    CINDER_METRICS_PREFIX,
    get_metrics_and_tags,
)


class BlockStorage(Component):
    ID = Component.Id.BLOCK_STORAGE
    TYPES = Component.Types.BLOCK_STORAGE
    SERVICE_CHECK = CINDER_SERVICE_CHECK

    def __init__(self, check):
        super(BlockStorage, self).__init__(check)

    @Component.register_global_metrics(ID)
    @Component.http_error(report_service_check=True)
    def _report_response_time(self, global_components_config, tags):
        self.check.log.debug("reporting `%s` response time", BlockStorage.ID.value)
        response_time = self.check.api.get_response_time(BlockStorage.TYPES.value)
        self.check.log.debug("`%s` response time: %s", BlockStorage.ID.value, response_time)
        self.check.gauge(CINDER_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_volumes(self, project_id, tags, config):
        report_volumes = config.get('volumes', True)
        if report_volumes:
            data = self.check.api.get_block_storage_volumes(project_id)
            for item in data:
                volume = get_metrics_and_tags(
                    item,
                    tags=CINDER_VOLUME_TAGS,
                    prefix=CINDER_METRICS_PREFIX,
                    metrics=[CINDER_VOLUME_COUNT],
                )
                self.check.log.debug("volume: %s", volume)
                self.check.gauge(CINDER_VOLUME_COUNT, 1, tags=tags + volume['tags'])
