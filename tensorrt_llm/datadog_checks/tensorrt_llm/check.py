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


class TensorrtLlmCheck(OpenMetricsBaseCheckV2):
    AGNOSTIC_HTTP_CLIENT = True
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'tensorrt_llm'

    def __init__(self, name: str, init_config: dict[str, Any], instances: list[dict[str, Any]]) -> None:
        # TensorRT-LLM ships as part of the GPU monitoring SKU; only run it when GPU monitoring is on.
        if not is_affirmative(datadog_agent.get_config('gpu.enabled')):
            raise SkipInstanceError("GPU monitoring (gpu.enabled) is not enabled.")
        # Prometheus multiprocess mode adds the worker pid, which changes on every restart. An instance's
        # `exclude_labels` replaces the default list, so merge `pid` into it rather than setting a default.
        instances = [
            {**instance, 'exclude_labels': list(dict.fromkeys(['pid', *(instance.get('exclude_labels') or [])]))}
            for instance in instances
        ]
        super().__init__(name, init_config, instances)

    def get_default_config(self) -> dict[str, Any]:
        return {
            'histogram_buckets_as_distributions': True,
            'collect_counters_with_distributions': True,
            # vLLM's per-position speculative decoding metrics use the `position` label.
            'rename_labels': {'token_position': 'position'},
        }
