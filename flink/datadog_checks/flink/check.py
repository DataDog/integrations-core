# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP


class FlinkCheck(OpenMetricsBaseCheckV2):
    """
    Collects Flink metrics by scraping the OpenMetrics/Prometheus endpoint
    exposed by Flink's `flink-metrics-prometheus` reporter.

    This is an alternative to configuring Flink's native Datadog HTTP
    Reporter; see the README for guidance on which collection mode to use.
    """

    __NAMESPACE__ = 'flink'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
        }
