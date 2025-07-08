# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.base import OpenMetricsBaseCheckV2  # noqa: F401
from datadog_checks.litellm.metrics import METRICS


class LitellmCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'litellm'

    DEFAULT_METRIC_LIMIT = 0
    METRIC_ENDPOINT_INFO = 'endpoint.info'
    METRIC_HEALTHY_COUNT = 'endpoint.healthy_count'
    METRIC_UNHEALTHY_COUNT = 'endpoint.unhealthy_count'

    def __init__(self, name, init_config, instances):
        super(LitellmCheck, self).__init__(name, init_config, instances)
        self.health_endpoint = self.instance.get('litellm_health_endpoint')
        self.tags = self.instance.get('tags', [])

    def get_default_config(self):
        return {
            'metrics': [METRICS],
        }

    def check(self, instance):
        super(LitellmCheck, self).check(instance)
        if self.health_endpoint:
            self.check_health_endpoint()

    def _build_tags(self, endpoint, extra_tags=None):
        tags = [
            f"llm_model:{endpoint.get('model', 'unknown')}",
            f"custom_llm_provider:{endpoint.get('custom_llm_provider', 'unknown')}",
        ]
        if extra_tags:
            tags.extend(extra_tags)
        return self.tags + tags

    def _extract_error_type(self, error_msg):
        match = re.search(r"litellm\.([A-Za-z0-9_]+):", error_msg)
        return match.group(1) if match else "unknown"

    def check_health_endpoint(self):
        self.log.debug("Checking health endpoint: %s", self.health_endpoint)
        response = self.http.get(self.health_endpoint)
        response.raise_for_status()
        data = response.json()

        base_tags = list(self.tags) + [f"health_endpoint:{self.health_endpoint}"]

        for endpoint in data.get('healthy_endpoints', []):
            health_tag = "endpoint_health:healthy"
            self.gauge(self.METRIC_ENDPOINT_INFO, 1, tags=self._build_tags(endpoint, [health_tag] + base_tags))

        for endpoint in data.get('unhealthy_endpoints', []):
            error_type = self._extract_error_type(endpoint.get('error', ''))
            error_tag = f"endpoint_error:{error_type}"
            health_tag = "endpoint_health:unhealthy"
            self.gauge(
                self.METRIC_ENDPOINT_INFO, 1, tags=self._build_tags(endpoint, [error_tag, health_tag] + base_tags)
            )

        self.gauge(self.METRIC_HEALTHY_COUNT, data.get('healthy_count', 0), tags=base_tags)
        self.gauge(self.METRIC_UNHEALTHY_COUNT, data.get('unhealthy_count', 0), tags=base_tags)
