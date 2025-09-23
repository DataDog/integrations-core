# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.temporal.config_models import ConfigMixin
from datadog_checks.temporal.metrics import METRIC_MAP


class TemporalCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'temporal.server'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            "metrics": [METRIC_MAP],
        }

    def configure_scrapers(self):
        super().configure_scrapers()

        self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.add_custom_transformer(
            "build_information",
            self._transform_build_information,
        )

    def _transform_build_information(self, metric, sample_data, runtime_data):
        for sample, *_ in sample_data:
            self.set_metadata('version', sample.labels['build_version'].replace('_', '.'))
