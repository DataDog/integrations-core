# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import pytest

from datadog_checks.couchbase import Couchbase

from .common import (
    CHECK_TAGS, BUCKET_NAME
)


@pytest.mark.integration
def test_service_check(aggregator, couchbase_metrics, couchbase_config):
    couchbase = Couchbase('couchbase', {}, {})
    couchbase.check(couchbase_config)

    aggregator.assert_service_check(Couchbase.SERVICE_CHECK_NAME, tags=CHECK_TAGS, status=Couchbase.OK, count=1)


@pytest.mark.integration
def test_metrics(aggregator, couchbase_metrics, couchbase_config):
    couchbase = Couchbase('couchbase', {}, {})
    couchbase.check(couchbase_config)

    assert_basic_couchbase_metrics(aggregator)


@pytest.mark.integration
def test_query_monitoring_metrics(aggregator, couchbase_metrics, couchbase_query_config):
    '''
    Test system vitals metrics (prefixed "couchbase.query.")
    '''
    # Add query monitoring endpoint
    couchbase = Couchbase('couchbase', {}, {})
    couchbase.check(couchbase_query_config)

    assert_basic_couchbase_metrics(aggregator)

    # Assert 'couchbase.query.' metrics
    for mname in Couchbase.QUERY_STATS:
        aggregator.assert_metric('couchbase.query.{0}'.format(mname), tags=CHECK_TAGS, count=1)


def assert_basic_couchbase_metrics(aggregator):
    '''
    Assert each type of metric (buckets, nodes, totals) except query
    '''

    # Assert 'couchbase.by_bucket.' metrics
    #  Because some metrics are deprecated, we can just see if we get an arbitrary number
    #  of bucket metrics. If there are more than that number, we assume that we're getting
    #  all the bucket metrics we should be getting
    BUCKET_TAGS = ['device:{0}'.format(BUCKET_NAME), 'bucket:{0}'.format(BUCKET_NAME)]
    bucket_metric_count = 0
    for bucket_metric in aggregator.metric_names:
        if bucket_metric.find(u'couchbase.by_bucket.') == 0:
            aggregator.assert_metric(bucket_metric, tags=CHECK_TAGS + BUCKET_TAGS, count=1)
            bucket_metric_count += 1

    assert(bucket_metric_count > 10)

    # Assert 'couchbase.by_node.' metrics
    NODE_STATS = [
        'curr_items',
        'curr_items_tot',
        'couch_docs_data_size',
        'couch_docs_actual_disk_size',
        'couch_views_data_size',
        'couch_views_actual_disk_size',
        'vb_replica_curr_items'
    ]
    for mname in NODE_STATS:
        aggregator.assert_metric_has_tag_with_tagname('couchbase.by_node.{0}'.format(mname), tag_name='node', count=1)

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
        'ram.used_by_data'
    ]
    for mname in TOTAL_STATS:
        aggregator.assert_metric('couchbase.{0}'.format(mname), tags=CHECK_TAGS, count=1)
