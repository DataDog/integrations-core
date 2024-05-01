# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    GLANCE_IMAGE_COUNT,
    GLANCE_IMAGE_METRICS,
    GLANCE_IMAGE_PREFIX,
    GLANCE_IMAGE_TAGS,
    GLANCE_MEMBER_COUNT,
    GLANCE_MEMBER_PREFIX,
    GLANCE_MEMBER_TAGS,
    GLANCE_RESPONSE_TIME,
    GLANCE_SERVICE_CHECK,
    GLANCE_TASK_COUNT,
    GLANCE_TASK_PREFIX,
    GLANCE_TASK_TAGS,
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
                    prefix=GLANCE_IMAGE_PREFIX,
                    metrics=GLANCE_IMAGE_METRICS,
                    lambda_name=lambda key: 'up' if key == 'status' else key,
                    lambda_value=lambda key, value, item=item: (
                        item['status'] == 'active' if key == 'status' else value
                    ),
                )
                self.check.log.debug("image: %s", image)
                self.check.gauge(GLANCE_IMAGE_COUNT, 1, tags=tags + image['tags'])
                for metric, value in image['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + image['tags'])
                self.check.log.debug("reporting tasks and members for image: %s", item['id'])
                self._report_members(config, tags, item['id'])
                self._report_tasks(config, tags, item['id'])

    @Component.http_error()
    def _report_members(self, config, tags, image_id):
        report_members = config.get('members', True)
        if report_members:
            data = self.check.api.get_glance_members(image_id)
            for item in data:
                member = get_metrics_and_tags(
                    item,
                    tags=GLANCE_MEMBER_TAGS,
                    prefix=GLANCE_MEMBER_PREFIX,
                    metrics=[GLANCE_MEMBER_COUNT],
                )
                self.check.gauge(GLANCE_MEMBER_COUNT, 1, tags=tags + member['tags'])

    @Component.http_error()
    def _report_tasks(self, config, tags, image_id):
        report_tasks = config.get('tasks', True)
        if report_tasks:
            data = self.check.api.get_glance_tasks(image_id)
            for item in data:
                task = get_metrics_and_tags(
                    item,
                    tags=GLANCE_TASK_TAGS,
                    prefix=GLANCE_TASK_PREFIX,
                    metrics=[GLANCE_TASK_COUNT],
                )
                self.check.gauge(GLANCE_TASK_COUNT, 1, tags=tags + task['tags'])
