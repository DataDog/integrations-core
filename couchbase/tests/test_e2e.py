# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    BUCKET_NAME,
    BUCKET_TAGS,
    CHECK_TAGS,
    COUCHBASE_METRIC_SOURCE,
    PORT,
    _assert_bucket_metrics,
    _assert_stats,
)


@pytest.mark.e2e
@pytest.mark.skipif(COUCHBASE_METRIC_SOURCE != "rest", reason='REST-specific test')
def test_e2e(dd_agent_check, instance, couchbase_container_ip):
    """
    Test couchbase metrics not including 'couchbase.query.'
    """
    aggregator = dd_agent_check(instance)

    # Assert each type of metric (buckets, nodes, totals) except query
    _assert_bucket_metrics(aggregator, BUCKET_TAGS, device=BUCKET_NAME)

    # Assert 'couchbase.by_node.' metrics
    node_tags = CHECK_TAGS + ['node:{}:{}'.format(couchbase_container_ip, PORT)]
    device = '{}:{}'.format(couchbase_container_ip, PORT)
    _assert_stats(aggregator, node_tags, device=device)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
@pytest.mark.skipif(COUCHBASE_METRIC_SOURCE != "prometheus", reason='Prometheus-specific test')
def test_e2e_prometheus(dd_agent_check, instance):
    """
    Test Prometheus-based metrics collection end-to-end
    """
    aggregator = dd_agent_check(instance)

    # Verify we collected a substantial number of Prometheus metrics
    metrics = aggregator.metric_names
    couchbase_metrics = [m for m in metrics if m.startswith('couchbase.')]

    assert len(couchbase_metrics) > 100, f"Expected at least 100 Prometheus metrics, got {len(couchbase_metrics)}"

    # Verify some key metric categories are present
    kv_metrics = [m for m in couchbase_metrics if m.startswith('couchbase.kv.')]
    assert len(kv_metrics) > 0, "Expected KV metrics from Prometheus endpoint"

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
