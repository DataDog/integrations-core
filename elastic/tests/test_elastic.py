# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import time

from mock import patch
import pytest
import requests

from datadog_checks.elastic import ESCheck
from datadog_checks.elastic.config import from_instance
from datadog_checks.elastic.metrics import (
    INDEX_STATS_METRICS, CLUSTER_PENDING_TASKS, ADDITIONAL_METRICS_1_x,
    stats_for_version, pshard_stats_for_version, health_stats_for_version
)
from .common import CLUSTER_TAG, PASSWORD, URL, USER, INDEX_METRICS_MOCK_DATA


TEST_LATENCY = 5


log = logging.getLogger('test_elastic')


@pytest.mark.unit
def test__join_url(elastic_check):
    adm_forwarder_joined_url = elastic_check._join_url(
        "https://localhost:9444/elasticsearch-admin",
        "/stats",
        admin_forwarder=True
    )
    assert adm_forwarder_joined_url == "https://localhost:9444/elasticsearch-admin/stats"

    joined_url = elastic_check._join_url("https://localhost:9444/elasticsearch-admin", "/stats")
    assert joined_url == "https://localhost:9444/stats"


@pytest.mark.unit
def test__get_urls(elastic_check):
    health_url, stats_url, pshard_stats_url, pending_tasks_url = elastic_check._get_urls([], True)
    assert health_url == '/_cluster/health'
    assert stats_url == '/_cluster/nodes/stats?all=true'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url is None

    health_url, stats_url, pshard_stats_url, pending_tasks_url = elastic_check._get_urls([], False)
    assert health_url == '/_cluster/health'
    assert stats_url == '/_cluster/nodes/_local/stats?all=true'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url is None

    health_url, stats_url, pshard_stats_url, pending_tasks_url = elastic_check._get_urls([1, 0, 0], True)
    assert health_url == '/_cluster/health'
    assert stats_url == '/_nodes/stats?all=true'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url == '/_cluster/pending_tasks'

    health_url, stats_url, pshard_stats_url, pending_tasks_url = elastic_check._get_urls([1, 0, 0], False)
    assert health_url == '/_cluster/health'
    assert stats_url == '/_nodes/_local/stats?all=true'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url == '/_cluster/pending_tasks'

    health_url, stats_url, pshard_stats_url, pending_tasks_url = elastic_check._get_urls([6, 0, 0], True)
    assert health_url == '/_cluster/health'
    assert stats_url == '/_nodes/stats'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url == '/_cluster/pending_tasks'

    health_url, stats_url, pshard_stats_url, pending_tasks_url = elastic_check._get_urls([6, 0, 0], False)
    assert health_url == '/_cluster/health'
    assert stats_url == '/_nodes/_local/stats'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url == '/_cluster/pending_tasks'


def test_check(elastic_cluster, elastic_check, instance, aggregator, cluster_tags, node_tags):
    config = from_instance(instance)
    es_version = elastic_check._get_es_version(config)

    elastic_check.check(instance)

    # node stats
    for m_name, desc in stats_for_version(es_version).iteritems():
        # exclude metrics that cannot be tested within a CI environment
        if m_name in ADDITIONAL_METRICS_1_x:
            continue
        aggregator.assert_metric(m_name, count=1, tags=node_tags)

    # cluster stats
    expected_metrics = health_stats_for_version(es_version)
    expected_metrics.update(CLUSTER_PENDING_TASKS)
    for m_name, desc in expected_metrics.iteritems():
        aggregator.assert_metric(m_name, count=1, tags=cluster_tags)

    aggregator.assert_service_check('elasticsearch.can_connect', status=ESCheck.OK, tags=node_tags)

    # Assert service metadata
    # self.assertServiceMetadata(['version'], count=3)
    # FIXME: 0.90.13 returns randomly a red status instead of yellow,
    # so we don't do a coverage test for it
    # Remove me when we stop supporting 0.90.x (not supported anymore by ES)
    if es_version != [0, 90, 13]:
        # Warning because elasticsearch status should be yellow, according to
        # http://chrissimpson.co.uk/elasticsearch-yellow-cluster-status-explained.html
        aggregator.assert_service_check('elasticsearch.cluster_health')


def test_pshard_metrics(aggregator, elastic_check):
    """
    Tests that the pshard related metrics are forwarded and that the
    document count for primary indexes is twice smaller as the global
    document count when "number_of_replicas" is set to 1
    """
    instance = {'url': URL, 'pshard_stats': True, 'username': USER, 'password': PASSWORD}
    config = from_instance(instance)
    es_version = elastic_check._get_es_version(config)

    requests.put(URL + '/_settings', data='{"index": {"number_of_replicas": 1}}')
    requests.put(URL + '/testindex/testtype/2', data='{"name": "Jane Doe", "age": 27}')
    requests.put(URL + '/testindex/testtype/1', data='{"name": "John Doe", "age": 42}')
    time.sleep(TEST_LATENCY)

    elastic_check.check(instance)

    pshard_stats_metrics = pshard_stats_for_version(es_version)
    for m_name, desc in pshard_stats_metrics.iteritems():
        if desc[0] == 'gauge':
            aggregator.assert_metric(m_name)

    # Our pshard metrics are getting sent, let's check that they're accurate
    # Note: please make sure you don't install Maven on the CI for future
    # elastic search CI integrations. It would make the line below fail :/
    aggregator.assert_metric('elasticsearch.primaries.docs.count')


def test_index_metrics(aggregator, elastic_check):
    instance = {'url': URL, 'index_stats': True, 'username': USER, 'password': PASSWORD}
    config = from_instance(instance)
    es_version = elastic_check._get_es_version(config)

    # Tests that index level metrics are forwarded
    if es_version < [1, 0, 0]:
        pytest.skip("Index metrics are only tested in version 1.0.0+")

    elastic_check.check(instance)
    for m_name, desc in INDEX_STATS_METRICS.iteritems():
        aggregator.assert_metric(m_name)


def test_health_event(aggregator, elastic_check):
    dummy_tags = ['elastique:recherche']
    instance = {'url': URL, 'username': USER, 'password': PASSWORD, 'tags': dummy_tags}
    config = from_instance(instance)
    es_version = elastic_check._get_es_version(config)

    # Should be yellow at first
    requests.put(URL + '/_settings', data='{"index": {"number_of_replicas": 100}')

    elastic_check.check(instance)

    if es_version < [2, 0, 0]:
        assert len(aggregator.events) == 1
        assert sorted(aggregator.events[0]['tags']) == sorted(set(['url:' + URL]
                                                              + dummy_tags + CLUSTER_TAG))
    else:
        aggregator.assert_service_check('elasticsearch.cluster_health')


def mock_output(*args, **kwargse):
    return INDEX_METRICS_MOCK_DATA if "/_cat/indices" in args[0] else {}


@patch('datadog_checks.elastic.elastic.ESCheck._get_data', side_effect=mock_output)
def test_get_index_metrics(mock_output, aggregator, elastic_check):
    dummy_tags = ['elastique:recherche']
    instance = {'url': URL, 'username': USER, 'password': PASSWORD, 'tags': dummy_tags, "index_stats": True}

    elastic_check.check(instance)

    tags = ['url:http://localhost:9200', 'elastique:recherche']
    aggregator.assert_metric('elasticsearch.pending_tasks_priority_high', value=0.0, tags=tags, count=1)
    aggregator.assert_metric('elasticsearch.index.health', value=0.0, tags=tags + ['index_name:index_1'], count=1)
    aggregator.assert_metric('elasticsearch.index.health', value=0.0, tags=tags + ['index_name:index_2'], count=1)
    aggregator.assert_metric('elasticsearch.index.store_size', value=29.2, tags=tags + ['index_name:index_1'], count=1)
    aggregator.assert_metric('elasticsearch.index.store_size', value=31.7, tags=tags + ['index_name:index_2'], count=1)
    aggregator.assert_metric('elasticsearch.index.primary_store_size', value=9.7, tags=tags + ['index_name:index_1'],
                             count=1)
    aggregator.assert_metric('elasticsearch.index.primary_store_size', value=10.5, tags=tags + ['index_name:index_2'])
    aggregator.assert_metric('elasticsearch.index.primary_shards', value=1.0, tags=tags + ['index_name:index_1'],
                             count=1)
    aggregator.assert_metric('elasticsearch.index.primary_shards', value=1.0, tags=tags + ['index_name:index_2'])
    aggregator.assert_metric('elasticsearch.pending_tasks_priority_urgent', value=0.0, tags=tags, count=1)
    aggregator.assert_metric('elasticsearch.pending_tasks_time_in_queue', value=0.0, tags=tags, count=1)
    aggregator.assert_metric('elasticsearch.index.docs.deleted', value=0.0, tags=tags + ['index_name:index_1'], count=1)
    aggregator.assert_metric('elasticsearch.index.docs.deleted', value=0.0, tags=tags + ['index_name:index_2'])
    aggregator.assert_metric('elasticsearch.index.docs.count', value=66354395.0, tags=tags + ['index_name:index_1'],
                             count=1)
    aggregator.assert_metric('elasticsearch.index.docs.count', value=50678201.0, tags=tags + ['index_name:index_2'])
    aggregator.assert_metric('elasticsearch.pending_tasks_total', value=0.0, tags=tags, count=1)
    aggregator.assert_metric('elasticsearch.index.replica_shards', value=2.0, tags=tags + ['index_name:index_1'],
                             count=1)
    aggregator.assert_metric('elasticsearch.index.replica_shards', value=2.0, tags=tags + ['index_name:index_2'])

    aggregator.assert_all_metrics_covered()
