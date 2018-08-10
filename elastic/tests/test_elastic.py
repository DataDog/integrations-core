# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from mock import patch
import logging
import os
import socket
import time

import pytest
import requests

from datadog_checks.elastic import ESCheck
from .common import (
    BAD_CONFIG, CHECK_NAME, CLUSTER_TAG, CONF_HOSTNAME,
    CONFIG, HOST, PASSWORD, PORT, TAGS, URL, USER,
    INDEX_METRICS_MOCK_DATA, get_es_version
)

log = logging.getLogger('test_elastic')


def test_bad_port():
    elastic_check = ESCheck(CHECK_NAME, {}, {})
    with pytest.raises(Exception):
        elastic_check.check(BAD_CONFIG)


def test_url_join(aggregator):
    elastic_check = ESCheck(CHECK_NAME, {}, {})
    adm_forwarder_joined_url = elastic_check._join_url(
        "https://localhost:9444/elasticsearch-admin",
        "/stats",
        admin_forwarder=True
    )
    assert adm_forwarder_joined_url == "https://localhost:9444/elasticsearch-admin/stats"

    joined_url = elastic_check._join_url("https://localhost:9444/elasticsearch-admin", "/stats")
    assert joined_url == "https://localhost:9444/stats"


def test_check(aggregator):
    elastic_check = ESCheck(CHECK_NAME, {}, {})
    default_tags = ["url:http://{0}:{1}".format(HOST, PORT)]

    for _ in xrange(2):
        try:
            elastic_check.check(CONFIG)
        except Exception:
            time.sleep(1)

    elastic_check.check(CONFIG)

    expected_metrics = dict(ESCheck.STATS_METRICS)
    ESCheck.CLUSTER_HEALTH_METRICS.update(ESCheck.CLUSTER_PENDING_TASKS)
    expected_metrics.update(ESCheck.CLUSTER_HEALTH_METRICS)

    instance = elastic_check.get_instance_config(CONFIG)
    es_version = elastic_check._get_es_version(instance)

    assert es_version == get_es_version()

    if es_version >= [6, 3, 0]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_POST_6_3)
    else:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_PRE_6_3)

    if es_version < [5, 0, 0]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_PRE_5_0_0)

    if es_version >= [0, 90, 5]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_POST_0_90_5)
        if es_version >= [0, 90, 10]:
            expected_metrics.update(ESCheck.JVM_METRICS_POST_0_90_10)
        else:
            expected_metrics.update(ESCheck.JVM_METRICS_PRE_0_90_10)
    else:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_PRE_0_90_5)
        expected_metrics.update(ESCheck.JVM_METRICS_PRE_0_90_10)

    if es_version >= [1, 0, 0]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_POST_1_0_0)

    if es_version < [2, 0, 0]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_PRE_2_0)
        if es_version >= [0, 90, 5]:
            expected_metrics.update(ESCheck.ADDITIONAL_METRICS_POST_0_90_5_PRE_2_0)
        # Currently has issues in test framework
        # if es_version >= [1, 0, 0]:
            # expected_metrics.update(ESCheck.ADDITIONAL_METRICS_1_x)

    if es_version >= [1, 3, 0]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_POST_1_3_0)

    if es_version >= [1, 4, 0]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_POST_1_4_0)

    if es_version >= [1, 5, 0]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_POST_1_5_0)

    if es_version >= [1, 6, 0]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_POST_1_6_0)

    if es_version >= [2, 0, 0]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_POST_2_0)

    if es_version >= [2, 1, 0]:
        expected_metrics.update(ESCheck.ADDITIONAL_METRICS_POST_2_1)

    if os.environ.get("DD_ELASTIC_LOCAL_HOSTNAME"):
        local_hostname = os.environ.get("DD_ELASTIC_LOCAL_HOSTNAME")
    elif es_version < [2, 0, 0]:
        local_hostname = socket.gethostname()
    else:
        local_hostname = '127.0.0.1'

    contexts = [
        (CONF_HOSTNAME, default_tags + TAGS),
        (local_hostname, default_tags + TAGS)
    ]

    stats_keys = (
        set(expected_metrics.keys()) - set(ESCheck.CLUSTER_HEALTH_METRICS.keys()) -
        set(ESCheck.CLUSTER_PENDING_TASKS.keys())
    )

    # index_writer_max_memory metric was removed in v5
    deprecated_metrics = ['elasticsearch.indices.segments.index_writer_max_memory_in_bytes']
    for m_name, desc in set(expected_metrics.iteritems()):
        for hostname, m_tags in contexts:
            m_tags = m_tags + CLUSTER_TAG
            if (m_name in ESCheck.CLUSTER_HEALTH_METRICS and
                    hostname == local_hostname):
                hostname = CONF_HOSTNAME

            if m_name in stats_keys:
                m_tags = m_tags + [u"node_name:batman"]

            m_tags.sort()
            if desc[0] == "gauge":
                aggregator.metrics(m_name)
                if es_version < [2, 0, 0]:
                    aggregator.assert_metric(m_name, tags=m_tags)
                elif not (m_name in deprecated_metrics):
                    aggregator.assert_metric(m_name)

    good_sc_tags = ['host:{0}'.format(HOST), 'port:{0}'.format(PORT)]
    aggregator.assert_service_check('elasticsearch.can_connect',
                                    status=ESCheck.OK,  # OK
                                    tags=good_sc_tags + TAGS)

    # Assert service metadata
    # self.assertServiceMetadata(['version'], count=3)
    # FIXME: 0.90.13 returns randomly a red status instead of yellow,
    # so we don't do a coverage test for it
    # Remove me when we stop supporting 0.90.x (not supported anymore by ES)
    if get_es_version() != [0, 90, 13]:
        # Warning because elasticsearch status should be yellow, according to
        # http://chrissimpson.co.uk/elasticsearch-yellow-cluster-status-explained.html
        aggregator.assert_service_check('elasticsearch.cluster_health')


def test_config_parser():
    elastic_check = ESCheck(CHECK_NAME, {}, {})
    instance = {
        "username": "user",
        "password": "pass",
        "is_external": "yes",
        "url": "http://foo.bar",
        "tags": ["a", "b:c"],
    }
    c = elastic_check.get_instance_config(instance)
    assert c.username == "user"
    assert c.password == "pass"
    assert c.admin_forwarder is False
    assert c.cluster_stats is True
    assert c.url == "http://foo.bar"
    assert c.tags == ["url:http://foo.bar", "a", "b:c"]
    assert c.timeout == elastic_check.DEFAULT_TIMEOUT
    assert c.service_check_tags == ["host:foo.bar", "port:None", "a", "b:c"]

    instance = {
        "url": "http://192.168.42.42:12999",
        "timeout": 15}
    c = elastic_check.get_instance_config(instance)
    assert c.username is None
    assert c.password is None
    assert c.cluster_stats is False
    assert c.url == "http://192.168.42.42:12999"
    assert c.tags == ["url:http://192.168.42.42:12999"]
    assert c.timeout == 15
    assert c.service_check_tags == ["host:192.168.42.42", "port:12999"]

    instance = {
        "username": "user",
        "password": "pass",
        "url": "https://foo.bar:9200",
        "ssl_verify": "true",
        "ssl_cert": "/path/to/cert.pem",
        "ssl_key": "/path/to/cert.key",
        "admin_forwarder": "1"
    }
    c = elastic_check.get_instance_config(instance)
    assert c.username == "user"
    assert c.password == "pass"
    assert c.admin_forwarder is True
    assert c.cluster_stats is False
    assert c.url == "https://foo.bar:9200"
    assert c.tags == ["url:https://foo.bar:9200"]
    assert c.timeout == elastic_check.DEFAULT_TIMEOUT
    assert c.service_check_tags == ["host:foo.bar", "port:9200"]
    assert c.ssl_verify == "true"
    assert c.ssl_cert == "/path/to/cert.pem"
    assert c.ssl_key == "/path/to/cert.key"


def test_pshard_metrics(aggregator):
    """ Tests that the pshard related metrics are forwarded and that the
        document count for primary indexes is twice smaller as the global
        document count when "number_of_replicas" is set to 1 """
    elastic_latency = 10
    config = {'url': URL, 'pshard_stats': True, 'username': USER, 'password': PASSWORD}

    requests.put(URL + '/_settings', data='{"index": {"number_of_replicas": 1}}')
    requests.put(URL + '/testindex/testtype/2', data='{"name": "Jane Doe", "age": 27}')
    requests.put(URL + '/testindex/testtype/1', data='{"name": "John Doe", "age": 42}')

    time.sleep(elastic_latency)
    elastic_check = ESCheck(CHECK_NAME, {}, {})
    elastic_check.check(config)

    pshard_stats_metrics = dict(ESCheck.PRIMARY_SHARD_METRICS)
    if get_es_version() >= [1, 0, 0]:
        pshard_stats_metrics.update(ESCheck.PRIMARY_SHARD_METRICS_POST_1_0)

    for m_name, desc in pshard_stats_metrics.iteritems():
        if desc[0] == "gauge":
            aggregator.assert_metric(m_name, count=1, tags=[])

    # Our pshard metrics are getting sent, let's check that they're accurate
    # Note: please make sure you don't install Maven on the CI for future
    # elastic search CI integrations. It would make the line below fail :/
    aggregator.assert_metric('elasticsearch.primaries.docs.count')


def test_index_metrics(aggregator):
    # Tests that index level metrics are forwarded
    config = {'url': URL, 'index_stats': True, 'username': USER, 'password': PASSWORD}

    elastic_check = ESCheck(CHECK_NAME, {}, {})
    index_metrics = dict(ESCheck.INDEX_STATS_METRICS)
    elastic_check.check(config)

    if get_es_version() >= [1, 0, 0]:
        for m_name, desc in index_metrics.iteritems():
            aggregator.assert_metric(m_name)


def test_health_event(aggregator):
    dummy_tags = ['elastique:recherche']
    config = {'url': URL, 'username': USER, 'password': PASSWORD, 'tags': dummy_tags}

    elastic_check = ESCheck(CHECK_NAME, {}, {})
    # Should be yellow at first
    requests.put(URL + '/_settings', data='{"index": {"number_of_replicas": 100}')
    elastic_check.check(config)
    if get_es_version() < [2, 0, 0]:
        assert len(aggregator.events) == 1
        assert sorted(aggregator.events[0]['tags']) == sorted(set(['url:' + URL]
                                                              + dummy_tags + CLUSTER_TAG))
    else:
        aggregator.assert_service_check('elasticsearch.cluster_health')


def mock_output(*args, **kwargse):
    if "/_cat/indices" in args[0]:
        return INDEX_METRICS_MOCK_DATA
    else:
        return {}


@patch('datadog_checks.elastic.elastic.ESCheck._get_data', side_effect=mock_output)
def test_get_index_metrics(mock_output, aggregator):
    dummy_tags = ['elastique:recherche']
    config = {'url': URL, 'username': USER, 'password': PASSWORD, 'tags': dummy_tags, "index_stats": True}

    elastic_check = ESCheck(CHECK_NAME, {}, {})
    elastic_check.check(config)
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
