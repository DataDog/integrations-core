# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base import OpenMetricsBaseCheckV2, is_affirmative
from datadog_checks.base.checks.openmetrics.v2.metrics_mapping import MetricsMapping


class GpuMonitoringEnabled:
    def should_load(self, config):
        return is_affirmative(datadog_agent.get_config('gpu.enabled'))


class DynamoCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'dynamo'

    # Frontend and router metrics come from CPU nodes and are always collected. Worker metrics ship
    # as part of the GPU monitoring SKU and are only collected when GPU monitoring is on.
    METRICS_MAP = (
        MetricsMapping(Path('metrics.yaml')),
        MetricsMapping(Path('gpu_metrics.yaml'), predicate=GpuMonitoringEnabled()),
    )

    def get_default_config(self):
        return {
            'histogram_buckets_as_distributions': True,
            'collect_counters_with_distributions': True,
        }
