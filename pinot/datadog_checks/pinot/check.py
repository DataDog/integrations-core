# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import ENDPOINTS_METRICS_MAP, RENAME_LABELS_MAP


class PinotCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    """
    Collects metrics from Apache Pinot components (Controller, Server, Broker, Minion)
    via their JMX Prometheus Exporter endpoints.
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.appendleft(self.parse_config)

    def parse_config(self):
        self.scraper_configs = []

        configured_endpoints = [endpoint for endpoint in ENDPOINTS_METRICS_MAP if self.instance.get(endpoint)]

        if not configured_endpoints:
            raise ConfigurationError(
                f"Must specify at least one of the following: {', '.join(ENDPOINTS_METRICS_MAP.keys())}."
            )

        for endpoint in configured_endpoints:
            url = self.instance.get(endpoint)
            metrics = ENDPOINTS_METRICS_MAP[endpoint]
            namespace = f"pinot.{endpoint.removesuffix('_endpoint')}" #todo: don't like this
            self.scraper_configs.append(self.generate_config(url, namespace, metrics))

    def generate_config(self, endpoint: str, namespace: str, metrics: dict) -> dict:
        config = copy.deepcopy(self.instance)
        config.update({
            'openmetrics_endpoint': endpoint,
            'namespace': namespace,
            'metrics': [metrics],
            'rename_labels': RENAME_LABELS_MAP,
        })
        return config
