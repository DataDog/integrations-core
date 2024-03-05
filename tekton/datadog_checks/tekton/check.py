# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.tekton.config_models import ConfigMixin

from .metrics import ENDPOINTS_METRICS_MAP


class TektonCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(TektonCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self.parse_config)

    def parse_config(self):
        self.scraper_configs = []

        if not any(self.instance.get(endpoint) for endpoint in ENDPOINTS_METRICS_MAP):
            raise ConfigurationError(
                f"Must specify at least one of the following: {', '.join(ENDPOINTS_METRICS_MAP.keys())}."
            )

        for endpoint, metrics in ENDPOINTS_METRICS_MAP.items():
            if url := self.instance.get(endpoint):
                self.scraper_configs.append(
                    self.generate_config(url, f"tekton.{endpoint.removesuffix('_endpoint')}", metrics)
                )

    def generate_config(self, endpoint, namespace, metrics):
        config = {
            'openmetrics_endpoint': endpoint,
            'metrics': [metrics],
            'namespace': namespace,
        }
        config |= self.instance
        return config
