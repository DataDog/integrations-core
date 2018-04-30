# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import pytest
import os
import sys
import time
import socket
import requests
import logging
import subprocess
from datadog_checks.utils.common import get_docker_hostname
from datadog_checks.elastic import ESCheck

log = logging.getLogger('test_elastic')

CHECK_NAME = "elastic"

HERE = os.path.dirname(os.path.abspath(__file__))
USER = "elastic"
PASSWORD = "changeme"
HOST = get_docker_hostname()
PORT = '9200'
BAD_PORT = '9405'
CONF_HOSTNAME = "foo"
TAGS = [u"foo:bar", u"baz"]
CLUSTER_TAG = [u"cluster_name:elasticsearch"]
URL = 'http://{0}:{1}'.format(HOST, PORT)
BAD_URL = 'http://{0}:{1}'.format(HOST, BAD_PORT)

CONFIG = {'url': URL, 'username': USER, 'password': PASSWORD, 'tags': TAGS}
BAD_CONFIG = {'url': BAD_URL, 'password': PASSWORD}


@pytest.fixture(scope="session")
def spin_up_elastic():
    env = os.environ
    args = [
        'docker-compose', '-f', os.path.join(HERE, 'compose', 'elastic.yaml')
    ]
    subprocess.check_call(args + ["up", "-d"], env=env)
    sys.stderr.write("Waiting for ES to boot...")

    for _ in xrange(30):
        try:
            res = requests.get(URL)
            res.raise_for_status()
            break
        except Exception:
            time.sleep(1)

    # Create an index in ES
    requests.put(URL, '/datadog/')
    yield
    subprocess.check_call(args + ["down"], env=env)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def get_es_version():
    version = os.environ.get("ELASTIC_VERSION")
    dd_versions = {'0_90': [0, 90, 13], '1_0': [1, 0, 3], '1_1': [1, 1, 2], '1_2': [1, 2, 4]}
    if version is None:
        return [6, 0, 1]
    if '_' in version:
        return dd_versions[version]
    else:
        return [int(k) for k in version.split(".")]


def test_bad_port(aggregator, spin_up_elastic):
    elastic_check = ESCheck(CHECK_NAME, {}, {})
    with pytest.raises(Exception):
        elastic_check.check(BAD_CONFIG)


def test_check(aggregator, spin_up_elastic):
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


def test_config_parser(aggregator, spin_up_elastic):
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
    }
    c = elastic_check.get_instance_config(instance)
    assert c.username == "user"
    assert c.password == "pass"
    assert c.cluster_stats is False
    assert c.url == "https://foo.bar:9200"
    assert c.tags == ["url:https://foo.bar:9200"]
    assert c.timeout == elastic_check.DEFAULT_TIMEOUT
    assert c.service_check_tags == ["host:foo.bar", "port:9200"]
    assert c.ssl_verify == "true"
    assert c.ssl_cert == "/path/to/cert.pem"
    assert c.ssl_key == "/path/to/cert.key"


def test_pshard_metrics(aggregator, spin_up_elastic):
    """ Tests that the pshard related metrics are forwarded and that the
        document count for primary indexes is twice smaller as the global
        document count when "number_of_replicas" is set to 1 """
    elastic_latency = 10
    config = {'url': 'http://localhost:9200', 'pshard_stats': True, 'username': USER, 'password': PASSWORD}

    requests.put('http://localhost:9200/_settings', data='{"index": {"number_of_replicas": 1}}')
    requests.put('http://localhost:9200/testindex/testtype/2', data='{"name": "Jane Doe", "age": 27}')
    requests.put('http://localhost:9200/testindex/testtype/1', data='{"name": "John Doe", "age": 42}')

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


def test_index_metrics(aggregator, spin_up_elastic):
    # Tests that index level metrics are forwarded
    config = {'url': 'http://localhost:9200', 'index_stats': True, 'username': USER, 'password': PASSWORD}

    elastic_check = ESCheck(CHECK_NAME, {}, {})
    index_metrics = dict(ESCheck.INDEX_STATS_METRICS)
    elastic_check.check(config)

    if get_es_version() >= [1, 0, 0]:
        for m_name, desc in index_metrics.iteritems():
            aggregator.assert_metric(m_name)


def test_health_event(aggregator, spin_up_elastic):
    dummy_tags = ['elastique:recherche']
    config = {'url': 'http://localhost:9200', 'username': USER, 'password': PASSWORD, 'tags': dummy_tags}

    elastic_check = ESCheck(CHECK_NAME, {}, {})
    # Should be yellow at first
    requests.put('http://localhost:9200/_settings', data='{"index": {"number_of_replicas": 100}')
    elastic_check.check(config)
    if get_es_version() < [2, 0, 0]:
        assert len(aggregator.events) == 1
        assert sorted(aggregator.events[0]['tags']) == sorted(set(['url:http://localhost:9200']
                                                              + dummy_tags + CLUSTER_TAG))
    else:
        aggregator.assert_service_check('elasticsearch.cluster_health')
