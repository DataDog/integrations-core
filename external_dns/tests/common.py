# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Test constants for external_dns integration.

Supports two dimensions:
- external-dns versions: v1.15.0 (legacy) vs v1.20.0 (new)
- Datadog integration versions: OpenMetrics V1 vs V2
"""

import os

from datadog_checks.dev import get_here

HERE = get_here()
FIXTURE_DIR = os.path.join(HERE, 'fixtures')
CHECK_NAME = 'external_dns'
NAMESPACE = 'external_dns'

E2E_PROMETHEUS_URL = 'http://localhost:7979/metrics'
HEALTH_TAGS = ['custom:tag', f'endpoint:{E2E_PROMETHEUS_URL}']

SERVICE_CHECK_OMV1 = f'{NAMESPACE}.prometheus.health'
SERVICE_CHECK_OMV2 = f'{NAMESPACE}.openmetrics.health'

# Non-zero counter values in metrics-legacy.txt and metrics-1.20.txt
REGISTRY_ERRORS_COUNT = 3
SOURCE_ERRORS_COUNT = 7

# =============================================================================
# external-dns v1.15.0 (legacy) metrics
# Uses separate metrics per record type (a_records, aaaa_records)
# =============================================================================

# Gauges in legacy version
LEGACY_GAUGE_METRICS = [
    NAMESPACE + '.registry.endpoints.total',
    NAMESPACE + '.source.endpoints.total',
    NAMESPACE + '.controller.consecutive.soft.errors',
    NAMESPACE + '.controller.last_reconcile',
    NAMESPACE + '.controller.last_sync',
    NAMESPACE + '.controller.verified_a_records',
    NAMESPACE + '.controller.verified_aaaa_records',
    NAMESPACE + '.registry.a_records',
    NAMESPACE + '.registry.aaaa_records',
    NAMESPACE + '.source.a_records',
    NAMESPACE + '.source.aaaa_records',
]

COUNTER_METRICS_OMV1 = [
    NAMESPACE + '.source.errors.total',
    NAMESPACE + '.registry.errors.total',
]

COUNTER_METRICS_OMV2 = [
    NAMESPACE + '.source.errors.total.count',
    NAMESPACE + '.registry.errors.total.count',
]

# OpenMetrics V1: counters submitted as gauges
LEGACY_METRICS_OMV1 = LEGACY_GAUGE_METRICS + COUNTER_METRICS_OMV1

# OpenMetrics V2: non-zero counters are submitted as monotonic_count with a .count suffix
LEGACY_METRICS_OMV2 = LEGACY_GAUGE_METRICS + COUNTER_METRICS_OMV2


# =============================================================================
# external-dns v1.20.0 metrics
# Uses vector metrics with record_type label
# =============================================================================

# Gauges in v1.20.0
V120_GAUGE_METRICS = [
    NAMESPACE + '.registry.endpoints.total',
    NAMESPACE + '.source.endpoints.total',
    NAMESPACE + '.controller.consecutive.soft.errors',
    NAMESPACE + '.controller.last_reconcile',
    NAMESPACE + '.controller.last_sync',
    NAMESPACE + '.source.records',
    NAMESPACE + '.registry.records',
    NAMESPACE + '.controller.verified_records',
]

# Summary metrics (http_request_duration_seconds)
V120_SUMMARY_BASE = NAMESPACE + '.http.request.duration_seconds'

# OpenMetrics V1: summary generates .quantile, .sum, .count; counters as gauges
V120_METRICS_OMV1 = (
    V120_GAUGE_METRICS
    + COUNTER_METRICS_OMV1
    + [
        V120_SUMMARY_BASE + '.quantile',
        V120_SUMMARY_BASE + '.sum',
        V120_SUMMARY_BASE + '.count',
    ]
)

# OpenMetrics V2: non-zero counters are submitted as monotonic_count with a .count suffix
V120_METRICS_OMV2 = (
    V120_GAUGE_METRICS
    + COUNTER_METRICS_OMV2
    + [
        V120_SUMMARY_BASE + '.quantile',
        V120_SUMMARY_BASE + '.sum',
        V120_SUMMARY_BASE + '.count',
    ]
)

# Metrics documented in metadata.csv but only emitted by one external-dns version
LEGACY_ONLY_METADATA_METRICS = [
    NAMESPACE + '.controller.verified_a_records',
    NAMESPACE + '.controller.verified_aaaa_records',
    NAMESPACE + '.registry.a_records',
    NAMESPACE + '.registry.aaaa_records',
    NAMESPACE + '.source.a_records',
    NAMESPACE + '.source.aaaa_records',
]

V120_ONLY_METADATA_METRICS = [
    NAMESPACE + '.controller.verified_records',
    V120_SUMMARY_BASE + '.count',
    V120_SUMMARY_BASE + '.quantile',
    V120_SUMMARY_BASE + '.sum',
    NAMESPACE + '.registry.records',
    NAMESPACE + '.source.records',
]
