# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import AgentCheck
from datadog_checks.dev import get_docker_hostname
from datadog_checks.elastic.config import from_instance
from datadog_checks.elastic.metrics import (
    CLUSTER_PENDING_TASKS,
    ADDITIONAL_METRICS_1_x,
    health_stats_for_version,
    stats_for_version,
)

HERE = os.path.dirname(os.path.abspath(__file__))
USER = "admin"
PASSWORD = "admin"
HOST = get_docker_hostname()
PORT = '9200'
CLUSTER_TAG = ["cluster_name:test-cluster"]
ELASTIC_CLUSTER_TAG = ["elastic_cluster:test-cluster"]
IS_OPENSEARCH = 'opensearch' in os.getenv('ELASTIC_REGISTRY')
URL = 'http://{}:{}'.format(HOST, PORT)

ELASTIC_VERSION = os.getenv('ELASTIC_VERSION', os.environ['ELASTIC_IMAGE'])
ELASTIC_FLAVOR = os.environ.get('ELASTIC_FLAVOR', 'elasticsearch')

JVM_RATES = [
    'jvm.gc.collectors.young.rate',
    'jvm.gc.collectors.young.collection_time.rate',
    'jvm.gc.collectors.old.rate',
    'jvm.gc.collectors.old.collection_time.rate',
]


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

    aggregator.assert_service_check('elasticsearch.can_connect', status=AgentCheck.OK, tags=config.service_check_tags)

    # Assert service metadata
    # self.assertServiceMetadata(['version'], count=3)
    # FIXME: 0.90.13 returns randomly a red status instead of yellow,
    # so we don't do a coverage test for it
    # Remove me when we stop supporting 0.90.x (not supported anymore by ES)
    if es_version != [0, 90, 13]:
        # Warning because elasticsearch status should be yellow, according to
        # http://chrissimpson.co.uk/elasticsearch-yellow-cluster-status-explained.html
        aggregator.assert_service_check('elasticsearch.cluster_health')


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)
