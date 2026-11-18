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


class LlmDCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'llm_d_inference'

    def __init__(self, name: str, init_config: dict[str, Any], instances: list[dict[str, Any]]) -> None:
        # llm-d ships as part of the GPU monitoring SKU; only run it when GPU monitoring is on.
        if not is_affirmative(datadog_agent.get_config('gpu.enabled')):
            raise SkipInstanceError("GPU monitoring (gpu.enabled) is not enabled.")
        super().__init__(name, init_config, instances)

    def get_default_config(self) -> dict[str, Any]:
        return {
            'histogram_buckets_as_distributions': True,
            'collect_counters_with_distributions': True,
            'rename_labels': {
                # EPP pool name, labelled `name` on pool metrics and `inference_pool` on Flow Control metrics.
                # The `inference_pool` tag comes from the pod annotation instead, so the two don't collide.
                'name': 'llm_d_pool',
                'inference_pool': 'llm_d_pool',
                # Scheduler and in-flight metrics describe the target endpoint, not the scraped pod.
                'namespace': 'endpoint_namespace',
                'port': 'endpoint_port',
            },
        }
