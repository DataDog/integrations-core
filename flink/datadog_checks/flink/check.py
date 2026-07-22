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
        # Flink's Prometheus reporter labels every series with `host` to
        # identify the source JobManager/TaskManager. That label collides
        # with Datadog's reserved hostname tag, so we promote it to the
        # metric's hostname and exclude it from the tag set.
        return {
            'hostname_label': 'host',
            'exclude_labels': ['host'],
            'metrics': [METRIC_MAP],
        }
