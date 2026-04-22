# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Metric definitions for external-dns integration.

This integration supports two versions of external-dns:
- Before v1.18: Uses separate metrics per record type (e.g., _a_records, _aaaa_records)
- v1.18+: Uses vector metrics with record_type label (e.g., _records{record_type="a"})

Metric Type Mapping (OpenMetrics → Datadog):
+------------------+------------------+------------------------+
| Prometheus Type  | OMV1 → Datadog   | OMV2 → Datadog         |
+------------------+------------------+------------------------+
| gauge            | gauge            | gauge                  |
| counter          | gauge (raw value)| monotonic_count (delta)|
| summary.quantile | gauge            | gauge                  |
| summary.sum      | gauge            | monotonic_count        |
| summary.count    | gauge            | monotonic_count        |
+------------------+------------------+------------------------+

Note: Counter metrics with zero values are not emitted by OMV2 on first scrape.
The metadata.csv reflects OMV2 (modern) behavior as the reference.
"""

from copy import deepcopy

# Common metrics present in all external-dns versions
COMMON_METRICS = {
    'external_dns_registry_endpoints_total': 'registry.endpoints.total',  # gauge
    'external_dns_source_endpoints_total': 'source.endpoints.total',  # gauge
    'external_dns_source_errors_total': 'source.errors.total',  # counter
    'external_dns_registry_errors_total': 'registry.errors.total',  # counter
    # Legacy metric names (without external_dns_ prefix, from older versions)
    'source_errors_total': 'source.errors.total',  # counter
    'registry_errors_total': 'registry.errors.total',  # counter
    'external_dns_controller_last_sync_timestamp_seconds': 'controller.last_sync',  # gauge
}

# Metrics specific to external-dns before v1.18 (separate metrics per record type)
LEGACY_METRICS = {
    'external_dns_controller_verified_a_records': 'controller.verified_a_records',  # gauge
    'external_dns_controller_verified_aaaa_records': 'controller.verified_aaaa_records',  # gauge
    'external_dns_registry_a_records': 'registry.a_records',  # gauge
    'external_dns_registry_aaaa_records': 'registry.aaaa_records',  # gauge
    'external_dns_source_a_records': 'source.a_records',  # gauge
    'external_dns_source_aaaa_records': 'source.aaaa_records',  # gauge
}

# Metrics specific to external-dns v1.18+ (vector metrics with record_type label)
NEW_METRICS = {
    'external_dns_source_records': 'source.records',  # gauge
    'external_dns_registry_records': 'registry.records',  # gauge
    'external_dns_controller_verified_records': 'controller.verified_records',  # gauge
    'external_dns_http_request_duration_seconds': 'http.request.duration_seconds',  # summary
}

# Combined metrics for backward compatibility (supports both versions)
DEFAULT_METRICS = {}
DEFAULT_METRICS.update(COMMON_METRICS)
DEFAULT_METRICS.update(LEGACY_METRICS)
DEFAULT_METRICS.update(NEW_METRICS)

METRIC_MAP = deepcopy(DEFAULT_METRICS)


def construct_metrics_config(metric_map: dict) -> list:
    """Convert legacy metric map to OpenMetricsBaseCheckV2 format."""
    metrics = []
    for raw_metric_name, metric_name in metric_map.items():
        config = {raw_metric_name: {'name': metric_name}}
        metrics.append(config)
    return metrics
