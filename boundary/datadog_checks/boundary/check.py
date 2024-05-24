# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from functools import cached_property

from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import METRIC_MAP


class BoundaryCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'boundary'
    DEFAULT_METRIC_LIMIT = 0

    SERVICE_CHECK_CONTROLLER_HEALTH = 'controller.health'

    def check(self, _):
        try:
            response = self.http.get(self.config.health_endpoint)
        except Exception as e:
            self.submit_controller_health(self.CRITICAL, message=str(e))
        else:
            try:
                response.raise_for_status()
            except Exception as e:
                if response.status_code == 503:
                    self.submit_controller_health(self.WARNING, message=str(e))
                else:
                    self.submit_controller_health(self.CRITICAL, message=str(e))
            else:
                self.submit_controller_health(self.OK)

        super().check(_)

    def get_default_config(self):
        return {'metrics': [METRIC_MAP]}

    def submit_controller_health(self, status, message=None):
        self.service_check(
            self.SERVICE_CHECK_CONTROLLER_HEALTH, status, tags=self.controller_health_tags, message=message
        )

    @cached_property
    def controller_health_tags(self):
        tags = [f'endpoint:{self.config.health_endpoint}']

        if self.config.tags:
            tags.extend(self.config.tags)

        return tags
