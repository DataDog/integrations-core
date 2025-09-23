# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .config_models import ConfigMixin
from .metrics import ADDITIONAL_METRICS_MAP, INSTANCE_DEFAULT_METRICS, construct_metrics_config


class ScyllaCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = "scylla"

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

    def get_default_config(self):
        metric_groups = self.instance.get('metric_groups', [])
        additional_metrics = []

        if metric_groups:
            for group in metric_groups:
                additional_metrics.append(ADDITIONAL_METRICS_MAP[group])

        metrics = INSTANCE_DEFAULT_METRICS + additional_metrics

        return {'metrics': construct_metrics_config(metrics)}

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))
