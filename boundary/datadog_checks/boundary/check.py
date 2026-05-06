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
    DISCOVERY_PORT_HINTS = [9203]

    SERVICE_CHECK_CONTROLLER_HEALTH = 'controller.health'

    def __init__(self, name, init_config, instances):
        # Boundary's instance schema requires health_endpoint; placeholder it
        # for trial-mode instances so InstanceConfig validation passes.
        # _resolve_discovery overwrites with the real URL and rebuilds the
        # config model.
        if instances:
            for inst in instances:
                if inst.get("__discovery_service__") is not None and not inst.get("health_endpoint"):
                    inst["health_endpoint"] = "http://discovery-pending.invalid/health"
        super().__init__(name, init_config, instances)

    def _post_discovery_hook(self):
        # Derive health_endpoint from the discovered openmetrics_endpoint.
        base = self.instance["openmetrics_endpoint"].rsplit('/', 1)[0]
        self.instance["health_endpoint"] = f"{base}/health"
        # The cached_property below was computed from the placeholder; clear it.
        self.__dict__.pop('controller_health_tags', None)

    def check(self, _):
        # Resolve trial-mode discovery before reading self.config.health_endpoint
        # so the latter returns the real URL rather than the placeholder.
        self.ensure_discovery_resolved()

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
