# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time

import mock
import pytest

from datadog_checks.couchbase import Couchbase
from datadog_checks.couchbase.couchbase_consts import (
    INDEX_STATS_SERVICE_CHECK_NAME,
    NODE_CLUSTER_SERVICE_CHECK_NAME,
    NODE_HEALTH_SERVICE_CHECK_NAME,
    QUERY_STATS,
    SERVICE_CHECK_NAME,
    SG_SERVICE_CHECK_NAME,
)

from .common import (
    BUCKET_NAME,
    CHECK_TAGS,
    COUCHBASE_MAJOR_VERSION,
    INDEX_STATS_COUNT_METRICS,
    INDEX_STATS_GAUGE_METRICS,
    INDEX_STATS_INDEXER_METRICS,
    INDEX_STATS_TAGS,
    PORT,
    SYNC_GATEWAY_METRICS,
)

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

if COUCHBASE_MAJOR_VERSION == 7:
    NODE_STATS += ['index_data_size', 'index_disk_size']

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

BUCKET_TAGS = CHECK_TAGS + ['bucket:{}'.format(BUCKET_NAME)]


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_service_check(aggregator, instance, couchbase_container_ip):
    """
    Assert the OK service check
    """
    couchbase = Couchbase('couchbase', {}, instances=[instance])
    couchbase.check(None)

    NODE_HOST = '{}:{}'.format(couchbase_container_ip, PORT)
    NODE_TAGS = ['node:{}'.format(NODE_HOST)]

    aggregator.assert_service_check(SERVICE_CHECK_NAME, tags=CHECK_TAGS, status=Couchbase.OK, count=1)
    aggregator.assert_service_check(
        NODE_CLUSTER_SERVICE_CHECK_NAME, tags=CHECK_TAGS + NODE_TAGS, status=Couchbase.OK, count=1
    )
    aggregator.assert_service_check(
        NODE_HEALTH_SERVICE_CHECK_NAME, tags=CHECK_TAGS + NODE_TAGS, status=Couchbase.OK, count=1
    )


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


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_query_monitoring_metrics(aggregator, dd_run_check, instance_query, couchbase_container_ip):
    """
    Test system vitals metrics (prefixed "couchbase.query.")
    """
    couchbase = Couchbase('couchbase', {}, [instance_query])
    dd_run_check(couchbase)

    for mname in QUERY_STATS:
        aggregator.assert_metric('couchbase.query.{}'.format(mname), tags=CHECK_TAGS, count=1)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_sync_gateway_metrics(aggregator, dd_run_check, instance_sg, couchbase_container_ip):
    """
    Test Sync Gateway metrics (prefixed "couchbase.sync_gateway.")
    """
    couchbase = Couchbase('couchbase', {}, [instance_sg])
    dd_run_check(couchbase)
    db_tags = ['db:sync_gateway'] + CHECK_TAGS
    for mname in SYNC_GATEWAY_METRICS:
        if mname.count('.') > 2:
            # metrics tagged by database have an additional namespace
            aggregator.assert_metric(mname, tags=db_tags, count=1)
        else:
            aggregator.assert_metric(mname, tags=CHECK_TAGS, count=1)
    aggregator.assert_service_check(SG_SERVICE_CHECK_NAME, status=Couchbase.OK, tags=CHECK_TAGS)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_metadata(instance_query, dd_run_check, datadog_agent):
    check = Couchbase('couchbase', {}, [instance_query])
    check.check_id = 'test:123'
    dd_run_check(check)

    data = check.get_data()

    nodes = data['stats']['nodes']

    raw_version = ""

    # Next, get all the nodes
    if nodes is not None:
        for node in nodes:
            raw_version = node['version']

    major, minor, patch = raw_version.split("-")[0].split(".")

    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.release': mock.ANY,
        'version.build': 'enterprise',
        'version.raw': raw_version.replace('-enterprise', '+enterprise'),
    }

    datadog_agent.assert_metadata('test:123', version_metadata)


def _assert_bucket_metrics(aggregator, tags, device=None):
    # Assert 'couchbase.by_bucket.' metrics
    #  Because some metrics are deprecated, we can just see if we get an arbitrary number
    #  of bucket metrics. If there are more than that number, we assume that we're getting
    #  all the bucket metrics we should be getting
    bucket_metrics = []
    for metric in aggregator.metric_names:
        if metric.find('couchbase.by_bucket.') == 0:
            aggregator.assert_metric(metric, tags=tags, count=1, device=device)
            bucket_metrics.append(metric)

    assert len(bucket_metrics) > 4, "Expected at least 5 bucket metrics found: " + str(bucket_metrics)


def _assert_stats(aggregator, node_tags, device=None):
    for mname in NODE_STATS:
        aggregator.assert_metric('couchbase.by_node.{}'.format(mname), tags=node_tags, count=1, device=device)
    # Assert 'couchbase.' metrics
    for mname in TOTAL_STATS:
        aggregator.assert_metric('couchbase.{}'.format(mname), tags=CHECK_TAGS, count=1)


@pytest.mark.skipif(COUCHBASE_MAJOR_VERSION < 7, reason='Index metrics are only available for Couchbase 7+')
@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_index_stats_metrics(aggregator, dd_run_check, instance_index_stats, couchbase_container_ip):
    """
    Test Index Statistics metrics (prefixed "couchbase.index." and "couchbase.indexer.")
    """
    couchbase = Couchbase('couchbase', {}, [instance_index_stats])
    dd_run_check(couchbase)
    for mname in INDEX_STATS_INDEXER_METRICS:
        aggregator.assert_metric(mname, metric_type=aggregator.GAUGE, tags=CHECK_TAGS)

    for mname in INDEX_STATS_GAUGE_METRICS:
        aggregator.assert_metric(mname, metric_type=aggregator.GAUGE, tags=INDEX_STATS_TAGS)

    for mname in INDEX_STATS_COUNT_METRICS:
        aggregator.assert_metric(mname, metric_type=aggregator.MONOTONIC_COUNT, tags=INDEX_STATS_TAGS)

    aggregator.assert_service_check(INDEX_STATS_SERVICE_CHECK_NAME, status=Couchbase.OK, tags=CHECK_TAGS)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_metrics(aggregator, dd_run_check, instance, couchbase_container_ip):
    """
    Test couchbase metrics not including 'couchbase.query.'
    """
    # Few metrics are only available after some time post launch. Sleep to ensure they're present before we validate
    time.sleep(15)
    couchbase = Couchbase('couchbase', {}, instances=[instance])
    dd_run_check(couchbase)

    # Assert each type of metric (buckets, nodes, totals) except query
    _assert_bucket_metrics(aggregator, BUCKET_TAGS + ['device:{}'.format(BUCKET_NAME)])

    # Assert 'couchbase.by_node.' metrics
    node_tags = CHECK_TAGS + [
        'node:{}:{}'.format(couchbase_container_ip, PORT),
        'device:{}:{}'.format(couchbase_container_ip, PORT),
    ]
    _assert_stats(aggregator, node_tags)

    aggregator.assert_all_metrics_covered()
