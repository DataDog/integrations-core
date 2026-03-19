# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import ENDPOINTS_METRICS_MAP, RENAME_LABELS_MAP

ENDPOINT_NAMESPACE_MAP = {
    'controller_endpoint': 'pinot.controller',
    'server_endpoint': 'pinot.server',
    'broker_endpoint': 'pinot.broker',
    'minion_endpoint': 'pinot.minion',
}


class PinotCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    """
    Collects metrics from Apache Pinot components (Controller, Server, Broker, Minion)
    via their JMX Prometheus Exporter endpoints.
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self._endpoint_namespace_list: list[tuple[str, str]] = []
        self.check_initializations.appendleft(self.parse_config)

    def parse_config(self):
        self.scraper_configs = []
        self._endpoint_namespace_list = []

        configured_endpoints = [endpoint for endpoint in ENDPOINTS_METRICS_MAP if self.instance.get(endpoint)]

        if not configured_endpoints:
            raise ConfigurationError(
                f"Must specify at least one of the following: {', '.join(ENDPOINTS_METRICS_MAP.keys())}."
            )

        for endpoint in configured_endpoints:
            url = self.instance.get(endpoint)
            metrics = ENDPOINTS_METRICS_MAP[endpoint]
            namespace = ENDPOINT_NAMESPACE_MAP[endpoint]
            self._endpoint_namespace_list.append((url, namespace))
            self.scraper_configs.append(self.generate_config(url, namespace, metrics))

    def generate_config(self, endpoint: str, namespace: str, metrics: dict) -> dict:
        config = copy.deepcopy(self.instance)
        config.update(
            {
                'openmetrics_endpoint': endpoint,
                'namespace': namespace,
                'metrics': [metrics],
                'rename_labels': RENAME_LABELS_MAP,
                'enable_health_service_check': False,
            }
        )
        return config

    def check(self, instance):
        for url, namespace in self._endpoint_namespace_list:
            try:
                response = self.http.get(url)
                response.raise_for_status()
                self.gauge(f'{namespace}.can_connect', 1, tags=self._connectivity_tags(url))
            except Exception as e:
                self.log.error("Cannot connect to Pinot endpoint '%s': %s", url, e)
                self.gauge(f'{namespace}.can_connect', 0, tags=self._connectivity_tags(url))
        super().check(instance)

    def _connectivity_tags(self, url: str) -> list[str]:
        return [f'endpoint:{url}'] + list(self.instance.get('tags', []))
