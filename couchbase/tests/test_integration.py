# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.couchbase import Couchbase
from datadog_checks.couchbase.couchbase_consts import (
    INDEX_STATS_SERVICE_CHECK_NAME,
    NODE_CLUSTER_SERVICE_CHECK_NAME,
    NODE_HEALTH_SERVICE_CHECK_NAME,
    SERVICE_CHECK_NAME,
    SG_SERVICE_CHECK_NAME,
)
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    BUCKET_NAME,
    BUCKET_TAGS,
    CHECK_TAGS,
    COUCHBASE_MAJOR_VERSION,
    INDEX_STATS_COUNT_METRICS,
    INDEX_STATS_GAUGE_METRICS,
    INDEX_STATS_INDEXER_METRICS,
    INDEX_STATS_TAGS,
    PORT,
    QUERY_STATS,
    SYNC_GATEWAY_METRICS,
    _assert_bucket_metrics,
    _assert_stats,
)

pytestmark = [pytest.mark.usefixtures("dd_environment"), pytest.mark.integration]


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


def test_query_monitoring_metrics(aggregator, dd_run_check, instance_query, couchbase_container_ip):
    """
    Test system vitals metrics (prefixed "couchbase.query.")
    """
    couchbase = Couchbase('couchbase', {}, [instance_query])
    dd_run_check(couchbase)

    for metric_name in QUERY_STATS:
        aggregator.assert_metric('couchbase.{}'.format(metric_name), tags=CHECK_TAGS, at_least=0)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


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
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


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


@pytest.mark.skipif(COUCHBASE_MAJOR_VERSION < 7, reason='Index metrics are only available for Couchbase 7+')
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
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_metrics(aggregator, dd_run_check, instance, couchbase_container_ip):
    """
    Test couchbase metrics not including 'couchbase.query.'
    """
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
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
