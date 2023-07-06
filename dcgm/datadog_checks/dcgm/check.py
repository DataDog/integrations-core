# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.dcgm.metrics import METRIC_MAP


class DcgmCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'dcgm'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            "metrics": [METRIC_MAP],
        }

    def configure_scrapers(self):
        super().configure_scrapers()

        self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.add_custom_transformer(
            "build_information",
            self._add_build_version_to_metadata,
        )

    def _add_build_version_to_metadata(self, _metric, sample_data, _runtime_data):
        for sample, *_ in sample_data:
            self.set_metadata('version', sample.labels['build_version'].replace('_', '.'))
