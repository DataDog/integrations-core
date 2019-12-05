# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import mock
import pytest

from datadog_checks.couchbase import Couchbase
from datadog_checks.couchbase.couchbase_consts import (
    NODE_CLUSTER_SERVICE_CHECK_NAME,
    NODE_HEALTH_SERVICE_CHECK_NAME,
    QUERY_STATS,
    SERVICE_CHECK_NAME,
)

from .common import BUCKET_NAME, CHECK_TAGS, PORT

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
    couchbase = Couchbase('couchbase', {}, instances=[instance])
    couchbase.check(instance)

    # Assert each type of metric (buckets, nodes, totals) except query
    _assert_bucket_metrics(aggregator, BUCKET_TAGS + ['device:{}'.format(BUCKET_NAME)])

    # Assert 'couchbase.by_node.' metrics
    node_tags = CHECK_TAGS + [
        'node:{}:{}'.format(couchbase_container_ip, PORT),
        'device:{}:{}'.format(couchbase_container_ip, PORT),
    ]
    _assert_stats(aggregator, node_tags)

    aggregator.assert_all_metrics_covered()


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
def test_query_monitoring_metrics(aggregator, instance_query, couchbase_container_ip):
    """
    Test system vitals metrics (prefixed "couchbase.query.")
    """
    couchbase = Couchbase('couchbase', {}, instances=[instance_query])
    couchbase.check(instance_query)

    for mname in QUERY_STATS:
        aggregator.assert_metric('couchbase.query.{}'.format(mname), tags=CHECK_TAGS, count=1)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_metadata(aggregator, instance_query, datadog_agent):
    check = Couchbase('couchbase', {}, instances=[instance_query])
    check.check_id = 'test:123'
    check.check(instance_query)
    server = instance_query['server']

    data = check.get_data(server, instance_query)

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
    bucket_metric_count = 0
    for bucket_metric in aggregator.metric_names:
        if bucket_metric.find('couchbase.by_bucket.') == 0:
            aggregator.assert_metric(bucket_metric, tags=tags, count=1, device=device)
            bucket_metric_count += 1

    assert bucket_metric_count > 10


def _assert_stats(aggregator, node_tags, device=None):
    for mname in NODE_STATS:
        aggregator.assert_metric('couchbase.by_node.{}'.format(mname), tags=node_tags, count=1, device=device)

    # Assert 'couchbase.' metrics
    for mname in TOTAL_STATS:
        aggregator.assert_metric('couchbase.{}'.format(mname), tags=CHECK_TAGS, count=1)
