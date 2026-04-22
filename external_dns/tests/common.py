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


# =============================================================================
# external-dns v1.15.0 (legacy) metrics
# Uses separate metrics per record type (a_records, aaaa_records)
# =============================================================================

# Gauges in legacy version
LEGACY_GAUGE_METRICS = [
    NAMESPACE + '.registry.endpoints.total',
    NAMESPACE + '.source.endpoints.total',
    NAMESPACE + '.controller.last_sync',
    NAMESPACE + '.controller.verified_a_records',
    NAMESPACE + '.controller.verified_aaaa_records',
    NAMESPACE + '.registry.a_records',
    NAMESPACE + '.registry.aaaa_records',
    NAMESPACE + '.source.a_records',
    NAMESPACE + '.source.aaaa_records',
]

# Counters in legacy version (value=0 in fixture, won't be submitted by OMV2 on first scrape)
LEGACY_COUNTER_METRICS = [
    NAMESPACE + '.source.errors.total',
    NAMESPACE + '.registry.errors.total',
]

# OpenMetrics V1: counters submitted as gauges
LEGACY_METRICS_OMV1 = LEGACY_GAUGE_METRICS + LEGACY_COUNTER_METRICS

# OpenMetrics V2: counters with value 0 won't appear
LEGACY_METRICS_OMV2 = LEGACY_GAUGE_METRICS


# =============================================================================
# external-dns v1.20.0 metrics
# Uses vector metrics with record_type label
# =============================================================================

# Gauges in v1.20.0
V120_GAUGE_METRICS = [
    NAMESPACE + '.registry.endpoints.total',
    NAMESPACE + '.source.endpoints.total',
    NAMESPACE + '.controller.last_sync',
    NAMESPACE + '.source.records',
    NAMESPACE + '.registry.records',
    NAMESPACE + '.controller.verified_records',
]

# Summary metrics (http_request_duration_seconds)
V120_SUMMARY_BASE = NAMESPACE + '.http.request.duration_seconds'

# Counters in v1.20.0 (value=0 in fixture)
V120_COUNTER_METRICS = [
    NAMESPACE + '.source.errors.total',
    NAMESPACE + '.registry.errors.total',
]

# OpenMetrics V1: summary generates .quantile, .sum, .count; counters as gauges
V120_METRICS_OMV1 = (
    V120_GAUGE_METRICS
    + V120_COUNTER_METRICS
    + [
        V120_SUMMARY_BASE + '.quantile',
        V120_SUMMARY_BASE + '.sum',
        V120_SUMMARY_BASE + '.count',
    ]
)

# OpenMetrics V2: counters with value 0 won't appear
V120_METRICS_OMV2 = V120_GAUGE_METRICS + [
    V120_SUMMARY_BASE + '.quantile',
    V120_SUMMARY_BASE + '.sum',
    V120_SUMMARY_BASE + '.count',
]
