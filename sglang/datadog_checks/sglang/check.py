# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base import OpenMetricsBaseCheckV2, is_affirmative
from datadog_checks.base.errors import SkipInstanceError


class SglangCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'sglang'

    def __init__(self, name: str, init_config: dict[str, Any], instances: list[dict[str, Any]]) -> None:
        # SGLang ships as part of the GPU monitoring SKU; only run it when GPU monitoring is on.
        if not is_affirmative(datadog_agent.get_config('gpu.enabled')):
            raise SkipInstanceError("GPU monitoring (gpu.enabled) is not enabled.")
        super().__init__(name, init_config, instances)

    def get_default_config(self) -> dict[str, Any]:
        return {
            # Distributions make percentile aggregations available for SGLang's latency histograms.
            'histogram_buckets_as_distributions': True,
            'collect_counters_with_distributions': True,
            # Avoid colliding with the endpoint tag added by the OpenMetrics base check.
            'rename_labels': {'endpoint': 'http_endpoint'},
        }
