# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest
import requests
from packaging import version
from six import iteritems

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.elastic import ESCheck
from datadog_checks.elastic.metrics import (
    CAT_ALLOCATION_METRICS,
    CLUSTER_PENDING_TASKS,
    INDEX_SEARCH_STATS,
    STATS_METRICS,
    health_stats_for_version,
    index_stats_for_version,
    pshard_stats_for_version,
    slm_stats_for_version,
)

from .common import CLUSTER_TAG, ELASTIC_VERSION, IS_OPENSEARCH, JVM_RATES, PASSWORD, URL, USER, _test_check

log = logging.getLogger('test_elastic')

pytestmark = pytest.mark.integration


def test_custom_queries_valid_metrics(dd_environment, dd_run_check, instance, aggregator):
    custom_queries = [
        {
            'endpoint': '/_nodes',
            'data_path': '_nodes',
            'columns': [
                {
                    'value_path': 'total',
                    'name': 'elasticsearch.custom.metric',
                },
                {'value_path': 'total', 'name': 'elasticsearch.custom.metric2', 'type': 'monotonic_count'},
            ],
        },
    ]

    instance['custom_queries'] = custom_queries
    check = ESCheck('elastic', {}, instances=[instance])
    dd_run_check(check)

    aggregator.assert_metric('elasticsearch.custom.metric2', metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('elasticsearch.custom.metric', metric_type=aggregator.GAUGE)


def test_custom_queries_one_invalid(dd_environment, dd_run_check, instance, aggregator):
    custom_queries = [
        {
            # Wrong endpoint
            'endpoint': '/_nodes2',
            'data_path': '_nodes',
            'columns': [
                {
                    'value_path': 'total',
                    'name': 'elasticsearch.custom.metric2',
                },
            ],
        },
        {
            # Good endpoint
            'endpoint': '/_nodes',
            'data_path': '_nodes',
            'columns': [
                {
                    'value_path': 'total',
                    'name': 'elasticsearch.custom.metric',
                },
            ],
        },
    ]

    instance['custom_queries'] = custom_queries
    check = ESCheck('elastic', {}, instances=[instance])
    dd_run_check(check)

    aggregator.assert_metric('elasticsearch.custom.metric', metric_type=aggregator.GAUGE)


def test_custom_queries_with_payload(dd_environment, dd_run_check, instance, aggregator, cluster_tags):
    custom_queries = [
        {
            'endpoint': '/_search',
            'data_path': 'hits.total',
            'payload': {"query": {"match": {"phrase": {"query": ""}}}},
            'columns': [
                {
                    'value_path': 'value',
                    'name': 'elasticsearch.custom.metric',
                },
                {'value_path': 'relation', 'name': 'dynamic_tag', 'type': 'tag'},
            ],
        },
    ]

    instance['custom_queries'] = custom_queries
    check = ESCheck('elastic', {}, instances=[instance])
    dd_run_check(check)
    tags = cluster_tags + ['dynamic_tag:eq']

    aggregator.assert_metric('elasticsearch.custom.metric', metric_type=aggregator.GAUGE, tags=tags)


@pytest.mark.skipif(
    version.parse(ELASTIC_VERSION) < version.parse('8.0.0'), reason='Test unavailable for Elasticsearch < 8.0.0'
)
def test_custom_queries_with_payload_multiterm(dd_environment, dd_run_check, instance, aggregator, cluster_tags):
    response = requests.put(
        "{}/multiterm_test".format(instance['url']),
        json={"mappings": {"properties": {"field0": {"type": "keyword"}, "field1": {"type": "keyword"}}}},
    )
    response.raise_for_status()

    response = requests.post(
        "{}/multiterm_test/_doc?refresh=wait_for".format(instance['url']), json={"field0": "foo", "field1": "bar"}
    )
    response.raise_for_status()

    custom_queries = [
        {
            'endpoint': '/_search',
            'data_path': 'aggregations.values.buckets',
            'payload': {
                "size": 0,
                "aggs": {"values": {"multi_terms": {"terms": [{"field": "field0"}, {"field": "field1"}]}}},
            },
            'columns': [
                {
                    'value_path': 'doc_count',
                    'name': 'elasticsearch.custom.metric',
                },
                {'value_path': 'key.0', 'name': 'dynamic_tag0', 'type': 'tag'},
                {'value_path': 'key.1', 'name': 'dynamic_tag1', 'type': 'tag'},
            ],
        },
    ]

    instance['custom_queries'] = custom_queries
    check = ESCheck('elastic', {}, instances=[instance])
    dd_run_check(check)
    tags = cluster_tags + ['dynamic_tag0:foo', "dynamic_tag1:bar"]

    aggregator.assert_metric('elasticsearch.custom.metric', metric_type=aggregator.GAUGE, tags=tags)


def test_custom_queries_valid_tags(dd_environment, dd_run_check, instance, aggregator, cluster_tags):
    custom_queries = [
        {
            'endpoint': '/_nodes',
            'data_path': '_nodes',
            'columns': [
                {
                    'value_path': 'total',
                    'name': 'elasticsearch.custom.metric',
                },
                {'value_path': 'total', 'name': 'dynamic_tag', 'type': 'tag'},
            ],
            'tags': ['custom_tag:1'],
        },
    ]

    instance['custom_queries'] = custom_queries
    check = ESCheck('elastic', {}, instances=[instance])
    dd_run_check(check)
    tags = cluster_tags + ['custom_tag:1'] + ['dynamic_tag:1']

    aggregator.assert_metric('elasticsearch.custom.metric', metric_type=aggregator.GAUGE, tags=tags)


def test_custom_queries_non_existent_metrics(caplog, dd_environment, dd_run_check, instance, aggregator):
    custom_queries = [
        {
            'endpoint': '/_nodes',
            'data_path': '_nodes',
            'columns': [
                {
                    'value_path': 'totals',  # nonexistent elasticsearch metric
                    'name': 'elasticsearch.custom.metric',
                },
            ],
            'tags': ['custom_tag:1'],
        },
    ]
    instance['custom_queries'] = custom_queries
    check = ESCheck('elastic', {}, instances=[instance])
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        dd_run_check(check)

    aggregator.assert_metric('elasticsearch.custom.metric', count=0)
    assert 'Metric not found: _nodes.totals -> elasticsearch.custom.metric' in caplog.text


def test_custom_queries_non_existent_tags(caplog, dd_environment, dd_run_check, instance, aggregator, cluster_tags):
    custom_queries = [
        {
            'endpoint': '/_nodes',
            'data_path': '_nodes',
            'columns': [
                {
                    'value_path': 'total',
                    'name': 'elasticsearch.custom.metric',
                },
                {
                    'value_path': 'totals',  # nonexistent elasticsearch metric as tag
                    'name': 'nonexistent_tag',
                    'type': 'tag',
                },
            ],
        },
    ]
    instance['custom_queries'] = custom_queries
    check = ESCheck('elastic', {}, instances=[instance])
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        dd_run_check(check)

    aggregator.assert_metric('elasticsearch.custom.metric', count=1, tags=cluster_tags)

    assert 'Dynamic tag is null: _nodes.total -> nonexistent_tag' in caplog.text


def test_check(dd_environment, elastic_check, instance, aggregator, cluster_tags, node_tags):
    elastic_check.check(None)
    _test_check(elastic_check, instance, aggregator, cluster_tags, node_tags)


@pytest.mark.skipif(IS_OPENSEARCH, reason='Test unavailable for OpenSearch')
def test_check_slm_stats(dd_environment, instance, aggregator, cluster_tags, node_tags, slm_tags):
    instance['slm_stats'] = True
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    elastic_check.check(None)

    _test_check(elastic_check, instance, aggregator, cluster_tags, node_tags)

    # SLM stats
    slm_metrics = slm_stats_for_version(elastic_check._get_es_version())
    for m_name in slm_metrics:
        aggregator.assert_metric(m_name, at_least=1, tags=slm_tags)


def test_disable_cluster_tag(dd_environment, instance, aggregator, new_cluster_tags):
    instance['disable_legacy_cluster_tag'] = True
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    elastic_check.check(None)
    es_version = elastic_check._get_es_version()

    # cluster stats
    expected_metrics = health_stats_for_version(es_version)
    expected_metrics.update(CLUSTER_PENDING_TASKS)
    for m_name in expected_metrics:
        aggregator.assert_metric(m_name, at_least=1, tags=new_cluster_tags)


def test_jvm_gc_rate_metrics(dd_environment, instance, aggregator, cluster_tags, node_tags):
    instance['gc_collectors_as_rate'] = True
    check = ESCheck('elastic', {}, instances=[instance])
    check.check(instance)
    for metric in JVM_RATES:
        aggregator.assert_metric(metric, at_least=1, tags=node_tags)

    _test_check(check, instance, aggregator, cluster_tags, node_tags)


def test_node_name_as_host(dd_environment, instance_normalize_hostname, aggregator, node_tags):
    elastic_check = ESCheck('elastic', {}, instances=[instance_normalize_hostname])
    elastic_check.check(None)
    node_name = node_tags[-1].split(':')[1]

    for m_name, _ in iteritems(STATS_METRICS):
        aggregator.assert_metric(m_name, count=1, tags=node_tags, hostname=node_name)


def test_pshard_metrics(dd_environment, aggregator):
    instance = {'url': URL, 'pshard_stats': True, 'username': USER, 'password': PASSWORD, 'tls_verify': False}
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    es_version = elastic_check._get_es_version()

    elastic_check.check(None)

    pshard_stats_metrics = pshard_stats_for_version(es_version)
    for m_name, desc in iteritems(pshard_stats_metrics):
        if desc[0] == 'gauge':
            aggregator.assert_metric(m_name)

    # Our pshard metrics are getting sent, let's check that they're accurate
    # Note: please make sure you don't install Maven on the CI for future
    # elastic search CI integrations. It would make the line below fail :/
    aggregator.assert_metric('elasticsearch.primaries.docs.count')


def test_detailed_index_stats(dd_environment, aggregator):
    instance = {
        "url": URL,
        "cluster_stats": True,
        "pshard_stats": True,
        "detailed_index_stats": True,
        "tls_verify": False,
    }
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    es_version = elastic_check._get_es_version()
    elastic_check.check(None)
    pshard_stats_metrics = pshard_stats_for_version(es_version)
    for m_name, desc in iteritems(pshard_stats_metrics):
        if desc[0] == 'gauge' and desc[1].startswith('_all.'):
            aggregator.assert_metric(m_name)

    aggregator.assert_metric_has_tag('elasticsearch.primaries.docs.count', tag='index_name:_all')
    aggregator.assert_metric_has_tag('elasticsearch.primaries.docs.count', tag='index_name:testindex')
    aggregator.assert_metric_has_tag('elasticsearch.primaries.docs.count', tag='index_name:.testindex')
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_metric_type=False,
        exclude=[
            "system.cpu.idle",
            "system.load.1",
            "system.load.15",
            "system.load.5",
            "system.mem.free",
            "system.mem.total",
            "system.mem.usable",
            "system.mem.used",
            "system.net.bytes_rcvd",
            "system.net.bytes_sent",
            "system.swap.free",
            "system.swap.total",
            "system.swap.used",
        ],
    )


def test_index_metrics(dd_environment, aggregator, instance, cluster_tags):
    instance['index_stats'] = True
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    es_version = elastic_check._get_es_version()
    if es_version < [1, 0, 0]:
        pytest.skip("Index metrics are only tested in version 1.0.0+")

    elastic_check.check(None)
    expected_metrics = list(index_stats_for_version(es_version)) + [name for name, _ in INDEX_SEARCH_STATS]
    for m_name in expected_metrics:
        aggregator.assert_metric(m_name, tags=cluster_tags + ['index_name:testindex'])
        aggregator.assert_metric(m_name, tags=cluster_tags + ['index_name:.testindex'])
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), exclude=['elasticsearch.custom.metric'], check_submission_type=True
    )


def test_cat_allocation_metrics(dd_environment, aggregator, instance, cluster_tags):
    instance['cat_allocation_stats'] = True
    elastic_check = ESCheck('elastic', {}, instances=[instance])

    elastic_check.check(None)
    for m_name in CAT_ALLOCATION_METRICS:
        aggregator.assert_metric(m_name)


def test_health_event(dd_environment, aggregator):
    dummy_tags = ['elastique:recherche']
    instance = {'url': URL, 'username': USER, 'password': PASSWORD, 'tags': dummy_tags, 'tls_verify': False}
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    es_version = elastic_check._get_es_version()

    # Should be yellow at first
    requests.put(URL + '/_settings', data='{"index": {"number_of_replicas": 100}', verify=False)

    elastic_check.check(None)

    if es_version < [2, 0, 0]:
        assert len(aggregator.events) == 1
        assert sorted(aggregator.events[0]['tags']) == sorted(set(['url:{}'.format(URL)] + dummy_tags + CLUSTER_TAG))
    else:
        aggregator.assert_service_check('elasticsearch.cluster_health')


def test_health_event_disabled(dd_environment, aggregator):
    """
    Don't submit an event if user disables event submission.
    """
    dummy_tags = ['elastique:recherche']
    instance = {
        'url': URL,
        'username': USER,
        'password': PASSWORD,
        'tags': dummy_tags,
        'tls_verify': False,
        'submit_events': False,
    }
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    elastic_check._get_es_version()

    # Should be yellow at first
    requests.put(URL + '/_settings', data='{"index": {"number_of_replicas": 100}', verify=False)

    elastic_check.check(None)

    assert not aggregator.events
    aggregator.assert_service_check('elasticsearch.cluster_health')


def test_metadata(dd_environment, aggregator, elastic_check, instance, version_metadata, datadog_agent):
    elastic_check.check_id = 'test:123'
    elastic_check.check(None)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))
