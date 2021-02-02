# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from copy import deepcopy

import pytest
import requests
from six import iteritems

from datadog_checks.base import ConfigurationError
from datadog_checks.elastic import ESCheck
from datadog_checks.elastic.config import from_instance
from datadog_checks.elastic.metrics import (
    CLUSTER_PENDING_TASKS,
    STATS_METRICS,
    ADDITIONAL_METRICS_1_x,
    health_stats_for_version,
    index_stats_for_version,
    pshard_stats_for_version,
    slm_stats_for_version,
    stats_for_version,
)

from .common import CLUSTER_TAG, JVM_RATES, PASSWORD, URL, USER

log = logging.getLogger('test_elastic')


@pytest.mark.unit
def test__join_url():
    instance = {
        "url": "https://localhost:9444/elasticsearch-admin",
        "admin_forwarder": True,
    }
    check = ESCheck('elastic', {}, instances=[instance])

    adm_forwarder_joined_url = check._join_url("/stats", admin_forwarder=True)
    assert adm_forwarder_joined_url == "https://localhost:9444/elasticsearch-admin/stats"

    joined_url = check._join_url("/stats", admin_forwarder=False)
    assert joined_url == "https://localhost:9444/stats"


@pytest.mark.parametrize(
    'instance, url_fix',
    [
        pytest.param({'url': URL}, '_local/'),
        pytest.param({'url': URL, "cluster_stats": True, "slm_stats": True}, ''),
    ],
)
@pytest.mark.unit
def test__get_urls(instance, url_fix):
    elastic_check = ESCheck('elastic', {}, instances=[instance])

    health_url, stats_url, pshard_stats_url, pending_tasks_url, slm_url = elastic_check._get_urls([])
    assert health_url == '/_cluster/health'
    assert stats_url == '/_cluster/nodes/' + url_fix + 'stats?all=true'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url is None
    assert slm_url is None

    health_url, stats_url, pshard_stats_url, pending_tasks_url, slm_url = elastic_check._get_urls([1, 0, 0])
    assert health_url == '/_cluster/health'
    assert stats_url == '/_nodes/' + url_fix + 'stats?all=true'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url == '/_cluster/pending_tasks'
    assert slm_url is None

    health_url, stats_url, pshard_stats_url, pending_tasks_url, slm_url = elastic_check._get_urls([6, 0, 0])
    assert health_url == '/_cluster/health'
    assert stats_url == '/_nodes/' + url_fix + 'stats'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url == '/_cluster/pending_tasks'
    assert slm_url is None

    health_url, stats_url, pshard_stats_url, pending_tasks_url, slm_url = elastic_check._get_urls([7, 4, 0])
    assert health_url == '/_cluster/health'
    assert stats_url == '/_nodes/' + url_fix + 'stats'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url == '/_cluster/pending_tasks'
    assert slm_url == ('/_slm/policy' if instance.get('slm_stats') is True else None)


@pytest.mark.integration
def test_check(dd_environment, elastic_check, instance, aggregator, cluster_tags, node_tags):
    elastic_check.check(None)
    _test_check(elastic_check, instance, aggregator, cluster_tags, node_tags)


@pytest.mark.integration
def test_check_slm_stats(dd_environment, instance, aggregator, cluster_tags, node_tags, slm_tags):
    slm_instance = deepcopy(instance)
    slm_instance['slm_stats'] = True
    elastic_check = ESCheck('elastic', {}, instances=[slm_instance])
    elastic_check.check(None)

    _test_check(elastic_check, slm_instance, aggregator, cluster_tags, node_tags)

    # SLM stats
    slm_metrics = slm_stats_for_version(elastic_check._get_es_version())
    for m_name in slm_metrics:
        aggregator.assert_metric(m_name, at_least=1, tags=slm_tags)


@pytest.mark.integration
def test_jvm_gc_rate_metrics(dd_environment, instance, aggregator, cluster_tags, node_tags):
    instance['gc_collectors_as_rate'] = True
    check = ESCheck('elastic', {}, instances=[instance])
    check.check(instance)
    for metric in JVM_RATES:
        aggregator.assert_metric(metric, at_least=1, tags=node_tags)

    _test_check(check, instance, aggregator, cluster_tags, node_tags)


def _test_check(elastic_check, instance, aggregator, cluster_tags, node_tags):
    config = from_instance(instance)
    es_version = elastic_check._get_es_version()

    # node stats, blacklist metrics that can't be tested in a small, single node instance
    blacklist = ['elasticsearch.indices.segments.index_writer_max_memory_in_bytes']
    blacklist.extend(ADDITIONAL_METRICS_1_x)
    for m_name in stats_for_version(es_version):
        if m_name in blacklist:
            continue
        aggregator.assert_metric(m_name, at_least=1, tags=node_tags)

    # cluster stats
    expected_metrics = health_stats_for_version(es_version)
    expected_metrics.update(CLUSTER_PENDING_TASKS)
    for m_name in expected_metrics:
        aggregator.assert_metric(m_name, at_least=1, tags=cluster_tags)

    aggregator.assert_service_check('elasticsearch.can_connect', status=ESCheck.OK, tags=config.service_check_tags)

    # Assert service metadata
    # self.assertServiceMetadata(['version'], count=3)
    # FIXME: 0.90.13 returns randomly a red status instead of yellow,
    # so we don't do a coverage test for it
    # Remove me when we stop supporting 0.90.x (not supported anymore by ES)
    if es_version != [0, 90, 13]:
        # Warning because elasticsearch status should be yellow, according to
        # http://chrissimpson.co.uk/elasticsearch-yellow-cluster-status-explained.html
        aggregator.assert_service_check('elasticsearch.cluster_health')


@pytest.mark.integration
def test_node_name_as_host(dd_environment, instance_normalize_hostname, aggregator, node_tags):
    elastic_check = ESCheck('elastic', {}, instances=[instance_normalize_hostname])
    elastic_check.check(None)
    node_name = node_tags[-1].split(':')[1]

    for m_name, _ in iteritems(STATS_METRICS):
        aggregator.assert_metric(m_name, count=1, tags=node_tags, hostname=node_name)


@pytest.mark.integration
def test_pshard_metrics(dd_environment, aggregator):
    instance = {'url': URL, 'pshard_stats': True, 'username': USER, 'password': PASSWORD}
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


@pytest.mark.integration
def test_index_metrics(dd_environment, aggregator, instance, cluster_tags):
    instance['index_stats'] = True
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    es_version = elastic_check._get_es_version()
    if es_version < [1, 0, 0]:
        pytest.skip("Index metrics are only tested in version 1.0.0+")

    elastic_check.check(None)
    for m_name in index_stats_for_version(es_version):
        aggregator.assert_metric(m_name, tags=cluster_tags + ['index_name:testindex'])


@pytest.mark.integration
def test_health_event(dd_environment, aggregator):
    dummy_tags = ['elastique:recherche']
    instance = {'url': URL, 'username': USER, 'password': PASSWORD, 'tags': dummy_tags}
    elastic_check = ESCheck('elastic', {}, instances=[instance])
    es_version = elastic_check._get_es_version()

    # Should be yellow at first
    requests.put(URL + '/_settings', data='{"index": {"number_of_replicas": 100}')

    elastic_check.check(None)

    if es_version < [2, 0, 0]:
        assert len(aggregator.events) == 1
        assert sorted(aggregator.events[0]['tags']) == sorted(set(['url:{}'.format(URL)] + dummy_tags + CLUSTER_TAG))
    else:
        aggregator.assert_service_check('elasticsearch.cluster_health')


@pytest.mark.integration
def test_metadata(dd_environment, aggregator, elastic_check, instance, version_metadata, datadog_agent):
    elastic_check.check_id = 'test:123'
    elastic_check.check(None)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


@pytest.mark.unit
@pytest.mark.parametrize(
    'instance, expected_aws_host, expected_aws_service',
    [
        pytest.param(
            {'auth_type': 'aws', 'aws_region': 'foo', 'url': 'http://example.com'},
            'example.com',
            'es',
            id='aws_host_from_url',
        ),
        pytest.param(
            {'auth_type': 'aws', 'aws_region': 'foo', 'aws_host': 'foo.com', 'url': 'http://example.com'},
            'foo.com',
            'es',
            id='aws_host_custom_with_url',
        ),
        pytest.param(
            {'auth_type': 'aws', 'aws_region': 'foo', 'aws_service': 'es-foo', 'url': 'http://example.com'},
            'example.com',
            'es-foo',
            id='aws_service_custom',
        ),
    ],
)
def test_aws_auth_url(instance, expected_aws_host, expected_aws_service):
    check = ESCheck('elastic', {}, instances=[instance])

    assert getattr(check.http.options.get('auth'), 'aws_host', None) == expected_aws_host
    assert getattr(check.http.options.get('auth'), 'service', None) == expected_aws_service

    # make sure class attribute HTTP_CONFIG_REMAPPER is not modified
    assert 'aws_host' not in ESCheck.HTTP_CONFIG_REMAPPER


@pytest.mark.unit
@pytest.mark.parametrize(
    'instance, expected_aws_host, expected_aws_service',
    [
        pytest.param({}, None, None, id='not aws auth'),
        pytest.param(
            {'auth_type': 'aws', 'aws_region': 'foo', 'aws_host': 'foo.com'},
            'foo.com',
            'es',
            id='aws_host_custom_no_url',
        ),
    ],
)
def test_aws_auth_no_url(instance, expected_aws_host, expected_aws_service):
    with pytest.raises(ConfigurationError):
        ESCheck('elastic', {}, instances=[instance])


@pytest.mark.e2e
def test_e2e(dd_agent_check, elastic_check, instance, cluster_tags, node_tags):
    aggregator = dd_agent_check(instance, rate=True)
    _test_check(elastic_check, instance, aggregator, cluster_tags, node_tags)
