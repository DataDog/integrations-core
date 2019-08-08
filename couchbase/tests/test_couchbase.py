# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import pytest

from datadog_checks.couchbase import Couchbase
from datadog_checks.couchbase.couchbase_consts import (
    NODE_CLUSTER_SERVICE_CHECK_NAME,
    NODE_HEALTH_SERVICE_CHECK_NAME,
    QUERY_STATS,
    SERVICE_CHECK_NAME,
)

from .common import BUCKET_NAME, CHECK_TAGS, PORT


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_service_check(aggregator, instance, couchbase_container_ip):
    """
    Assert the OK service check
    """
    couchbase = Couchbase('couchbase', {}, {}, instances=[instance])
    couchbase.check(instance)

    NODE_HOST = '{}:{}'.format(couchbase_container_ip, PORT)
    NODE_TAGS = ['node:{}'.format(NODE_HOST)]

    aggregator.assert_service_check(SERVICE_CHECK_NAME, tags=CHECK_TAGS, status=Couchbase.OK, count=1)
    aggregator.assert_service_check(
        NODE_CLUSTER_SERVICE_CHECK_NAME, tags=CHECK_TAGS + NODE_TAGS, status=Couchbase.OK, count=1
    )
    aggregator.assert_service_check(
        NODE_HEALTH_SERVICE_CHECK_NAME, tags=CHECK_TAGS + NODE_TAGS, status=Couchbase.OK, count=1
    )


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_metrics(aggregator, instance, couchbase_container_ip):
    """
    Test couchbase metrics not including 'couchbase.query.'
    """
    couchbase = Couchbase('couchbase', {}, {}, instances=[instance])
    couchbase.check(instance)
    assert_basic_couchbase_metrics(aggregator, couchbase_container_ip)


@pytest.mark.e2e
@pytest.mark.usefixtures("dd_environment")
def test_e2e(dd_agent_check, instance, couchbase_container_ip):
    """
    Test couchbase metrics not including 'couchbase.query.'
    """
    aggregator = dd_agent_check(instance, rate=True)
    assert_basic_couchbase_metrics(aggregator, couchbase_container_ip, extract_device=True)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_query_monitoring_metrics(aggregator, instance_query, couchbase_container_ip):
    """
    Test system vitals metrics (prefixed "couchbase.query.")
    """
    couchbase = Couchbase('couchbase', {}, {}, instances=[instance_query])
    couchbase.check(instance_query)

    for mname in QUERY_STATS:
        aggregator.assert_metric('couchbase.query.{}'.format(mname), tags=CHECK_TAGS, count=1)


def assert_basic_couchbase_metrics(aggregator, couchbase_container_ip, extract_device=False):
    """
    Assert each type of metric (buckets, nodes, totals) except query
    """
    # Assert 'couchbase.by_bucket.' metrics
    #  Because some metrics are deprecated, we can just see if we get an arbitrary number
    #  of bucket metrics. If there are more than that number, we assume that we're getting
    #  all the bucket metrics we should be getting
    tags = CHECK_TAGS + ['bucket:{}'.format(BUCKET_NAME)]

    device = 'device:{}'.format(BUCKET_NAME)
    if not extract_device:
        tags.append(device)
        device = None

    bucket_metric_count = 0
    for bucket_metric in aggregator.metric_names:
        if bucket_metric.find('couchbase.by_bucket.') == 0:
            aggregator.assert_metric(bucket_metric, tags=tags, count=1, device=device)
            bucket_metric_count += 1

    assert bucket_metric_count > 10

    # Assert 'couchbase.by_node.' metrics
    tags = CHECK_TAGS + [
        'device:{}:{}'.format(couchbase_container_ip, PORT),
        'node:{}:{}'.format(couchbase_container_ip, PORT),
    ]

    NODE_STATS = [
        'cmd_get',
        'curr_items',
        'curr_items_tot',
        'couch_docs_data_size',
        'couch_docs_actual_disk_size',
        'couch_spatial_data_size',
        'couch_spatial_disk_size',
        'couch_views_data_size',
        'couch_views_actual_disk_size',
        'ep_bg_fetched',
        'get_hits',
        'mem_used',
        'ops',
        'vb_active_num_non_resident',
        'vb_replica_curr_items',
    ]
    for mname in NODE_STATS:
        aggregator.assert_metric('couchbase.by_node.{}'.format(mname), tags=tags, count=1)

    # Assert 'couchbase.' metrics
    TOTAL_STATS = [
        'hdd.free',
        'hdd.used',
        'hdd.total',
        'hdd.quota_total',
        'hdd.used_by_data',
        'ram.used',
        'ram.total',
        'ram.quota_total',
        'ram.quota_total_per_node',
        'ram.quota_used_per_node',
        'ram.quota_used',
        'ram.used_by_data',
    ]
    for mname in TOTAL_STATS:
        aggregator.assert_metric('couchbase.{}'.format(mname), tags=CHECK_TAGS, count=1)
    aggregator.assert_all_metrics_covered()
