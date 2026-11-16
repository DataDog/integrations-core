# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.base import OpenMetricsBaseCheckV2


class LlmDCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'llm_d'

    def get_default_config(self) -> dict[str, Any]:
        return {
            'histogram_buckets_as_distributions': True,
            'collect_counters_with_distributions': True,
            'rename_labels': {
                # InferencePool name, which identifies the deployment.
                'name': 'inference_pool',
                # Scheduler and in-flight metrics describe the target endpoint, not the scraped pod.
                'namespace': 'endpoint_namespace',
                'port': 'endpoint_port',
            },
        }
