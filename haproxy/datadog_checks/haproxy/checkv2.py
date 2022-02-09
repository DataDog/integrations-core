# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# from collections import ChainMap

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP, construct_metrics_config


class HaproxyCheckV2(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def _parse_config(self):
        self.scraper_configs = []
        openmetrics_endpoint = self.instance.get("openmetrics_endpoint")
        if not openmetrics_endpoint:
            raise ConfigurationError("Must specify a openmetrics_endpoint")
        self.scraper_configs.append(self._generate_config(openmetrics_endpoint, METRIC_MAP, "haproxy"))

    def _generate_config(self, endpoint, metrics, namespace):
        metrics = construct_metrics_config(metrics)
        config = {
            'openmetrics_endpoint': endpoint,
            'metrics': metrics,
            'namespace': namespace,
        }
        config.update(self.instance)
        return config
