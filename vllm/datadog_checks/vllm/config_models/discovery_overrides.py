# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Override the generated discovery candidates() for this integration.
#
# Define a candidates(service, default) function to wrap or replace the generated
# candidate generation. `default` is the generated generator; call it to reuse
# the spec-driven candidates, or ignore it to replace them entirely.
#
from collections.abc import Callable, Iterator
from typing import Any

from datadog_checks.base.utils.discovery import Service
from datadog_checks.vllm.check import is_gpu_monitoring_enabled

# The discovery probe accepts a candidate as soon as the check collects any metric, and METRIC_MAP
# carries the generic prometheus_client families. Without this, any Python Prometheus endpoint on
# the service (a Ray metrics agent, a sidecar) would look like vLLM and win the port race.
GENERIC_PROMETHEUS_METRICS = r'^(?:python|process)_'


def candidates(service: Service, default: Callable[[Service], Iterator[dict[str, Any]]]) -> Iterator[dict[str, Any]]:
    if is_gpu_monitoring_enabled():
        for config in default(service):
            instance = config['instances'][0]
            instance['exclude_metrics'] = [GENERIC_PROMETHEUS_METRICS]
            instance['histogram_buckets_as_distributions'] = True
            instance['collect_counters_with_distributions'] = True
            yield config
