# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base import OpenMetricsBaseCheckV2, is_affirmative
from datadog_checks.base.errors import SkipInstanceError


class DynamoCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'dynamo'

    def __init__(self, name, init_config, instances):
        # Dynamo ships as part of the GPU monitoring SKU; only run it when GPU monitoring is on.
        if not is_affirmative(datadog_agent.get_config('gpu.enabled')):
            raise SkipInstanceError("GPU monitoring (gpu.enabled) is not enabled.")
        super().__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'histogram_buckets_as_distributions': True,
            'collect_counters_with_distributions': True,
        }

    def configure_scrapers(self):
        super().configure_scrapers()

        # Dynamo exposes this ratio as per-mille (0-1000); submit a fraction so its metadata unit is accurate.
        self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.transformer_data[
            'dynamo_tokio_worker_busy_ratio'
        ] = (None, self._transform_worker_busy_ratio)

    def _transform_worker_busy_ratio(self, _metric, sample_data, _runtime_data):
        for sample, tags, hostname in sample_data:
            self.gauge('tokio.worker_busy_ratio', sample.value / 1000, tags=tags, hostname=hostname)
