# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    GLANCE_IMAGE_COUNT,
    GLANCE_IMAGE_TAGS,
    GLANCE_METRICS_PREFIX,
    GLANCE_RESPONSE_TIME,
    GLANCE_SERVICE_CHECK,
    get_metrics_and_tags,
)


class Image(Component):
    ID = Component.Id.IMAGE
    TYPES = Component.Types.IMAGE
    SERVICE_CHECK = GLANCE_SERVICE_CHECK

    def __init__(self, check):
        super(Image, self).__init__(check)

    @Component.register_global_metrics(ID)
    @Component.http_error(report_service_check=True)
    def _report_response_time(self, global_components_config, tags):
        self.check.log.debug("reporting `%s` response time", Image.ID.value)
        response_time = self.check.api.get_response_time(Image.TYPES.value)
        self.check.log.debug("`%s` response time: %s", Image.ID.value, response_time)
        self.check.gauge(GLANCE_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_images(self, config, tags):
        report_images = config.get('images', True)
        if report_images:
            data = self.check.api.get_glance_images()
            for item in data:
                image = get_metrics_and_tags(
                    item,
                    tags=GLANCE_IMAGE_TAGS,
                    prefix=GLANCE_METRICS_PREFIX,
                    metrics=[GLANCE_IMAGE_COUNT],
                )
                self.check.log.debug("image: %s", image)
                self.check.gauge(GLANCE_IMAGE_COUNT, 1, tags=tags + image['tags'])
