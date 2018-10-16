# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest
import requests

from datadog_checks.elastic import ESCheck
from datadog_checks.elastic.config import from_instance
from datadog_checks.elastic.metrics import (
    INDEX_STATS_METRICS, CLUSTER_PENDING_TASKS, ADDITIONAL_METRICS_1_x,
    stats_for_version, pshard_stats_for_version, health_stats_for_version
)
from .common import CLUSTER_TAG, PASSWORD, URL, USER


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


def test_pshard_metrics(elastic_cluster, elastic_check, aggregator):
    instance = {'url': URL, 'pshard_stats': True, 'username': USER, 'password': PASSWORD}
    config = from_instance(instance)
    es_version = elastic_check._get_es_version(config)

    elastic_check.check(instance)

    pshard_stats_metrics = pshard_stats_for_version(es_version)
    for m_name, desc in pshard_stats_metrics.iteritems():
        if desc[0] == 'gauge':
            aggregator.assert_metric(m_name)

    # Our pshard metrics are getting sent, let's check that they're accurate
    # Note: please make sure you don't install Maven on the CI for future
    # elastic search CI integrations. It would make the line below fail :/
    aggregator.assert_metric('elasticsearch.primaries.docs.count')


def test_index_metrics(elastic_cluster, aggregator, elastic_check, instance, cluster_tags):
    instance['index_stats'] = True
    config = from_instance(instance)
    es_version = elastic_check._get_es_version(config)
    if es_version < [1, 0, 0]:
        pytest.skip("Index metrics are only tested in version 1.0.0+")

    elastic_check.check(instance)
    for m_name, desc in INDEX_STATS_METRICS.iteritems():
        aggregator.assert_metric(m_name, tags=cluster_tags + ['index_name:testindex'])


def test_health_event(elastic_cluster, aggregator, elastic_check):
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
