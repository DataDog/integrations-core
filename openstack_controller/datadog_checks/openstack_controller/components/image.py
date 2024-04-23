# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    GLANCE_IMAGE_TAGS,
    GLANCE_IMAGE_UP,
    GLANCE_IMAGES_COUNT,
    GLANCE_IMAGES_PREFIX,
    GLANCE_IMAGES_TAGS,
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
            self.check.log.debug("images data: %s", data)
            for item in data:
                images = get_metrics_and_tags(
                    item,
                    tags=GLANCE_IMAGES_TAGS,
                    prefix=GLANCE_IMAGES_PREFIX,
                    metrics=[GLANCE_IMAGES_COUNT],
                )
                self.check.log.debug("images: %s", images)
                self.check.gauge(GLANCE_IMAGES_COUNT, 1, tags=tags + images['tags'])
                self._report_image(tags, item['id'])

    @Component.http_error()
    def _report_image(self, tags, image_id):
        image_data = self.check.api.get_glance_image(image_id)
        self.check.log.debug("image data: %s", image_data)
        image = get_metrics_and_tags(
            image_data,
            tags=GLANCE_IMAGE_TAGS,
            prefix=GLANCE_IMAGES_PREFIX,
            metrics=[GLANCE_IMAGE_UP],
        )
        is_active = 1 if image_data['status'] == 'active' else 0
        self.check.gauge(GLANCE_IMAGE_UP, is_active, tags=tags + image['tags'])
