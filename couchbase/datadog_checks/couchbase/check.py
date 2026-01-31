# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheck

from .metrics import (
    get_metric_map_couchbase_to_datadog,
    get_type_overrides,
)


class CouchbaseCheckV2(OpenMetricsBaseCheck):
    """
    Couchbase check using OpenMetrics/Prometheus metrics.
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        instance = instances[0]

        # Configure metrics collection using our curated metric map
        metrics = instance.get("metrics", [])
        if not metrics:
            metric_map = get_metric_map_couchbase_to_datadog()
            metrics = [metric_map]

        metric_type_overrides = get_type_overrides()

        instance.update(
            {
                "prometheus_url": instance.get("prometheus_url"),
                "namespace": "couchbase",
                "metrics": metrics,
                "type_overrides": metric_type_overrides,
                # Use traditional histogram format with separate .sum and .count metrics
                "send_histograms_buckets": True,
                "send_distribution_buckets": False,
                # Send histogram counts and sums as monotonic counters (Prometheus histograms are cumulative)
                "send_distribution_counts_as_monotonic": True,
                "send_distribution_sums_as_monotonic": True,
                # Increase timeout in case Couchbase is slow to respond
                "prometheus_timeout": instance.get("prometheus_timeout", 20),
                # Ensure we collect all metrics (no limit)
                "max_returned_metrics": instance.get("max_returned_metrics", 0),
                # Rename the "service" label to avoid conflict with Datadog's reserved "service" tag
                "labels_mapper": instance.get("labels_mapper", {"service": "couchbase_service"}),
                # Authentication - map 'user' to 'username' for OpenMetrics compatibility
                "username": instance.get("username") or instance.get("user"),
                "password": instance.get("password"),
            }
        )

        super().__init__(name, init_config, [instance])
