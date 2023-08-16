# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import BUCKET_NAME, BUCKET_TAGS, CHECK_TAGS, PORT, _assert_bucket_metrics, _assert_stats


@pytest.mark.e2e
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
