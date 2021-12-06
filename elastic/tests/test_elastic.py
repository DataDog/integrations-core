# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from copy import deepcopy

import pytest
import requests
from six import iteritems

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.elastic import ESCheck
from datadog_checks.elastic.config import from_instance
from datadog_checks.elastic.metrics import (
    CAT_ALLOCATION_METRICS,
    CLUSTER_PENDING_TASKS,
    STATS_METRICS,
    ADDITIONAL_METRICS_1_x,
    health_stats_for_version,
    index_stats_for_version,
    pshard_stats_for_version,
    slm_stats_for_version,
    stats_for_version,
)

from .common import CLUSTER_TAG, IS_OPENSEARCH, JVM_RATES, PASSWORD, URL, USER

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


@pytest.mark.skipif(IS_OPENSEARCH, reason='Test unavailable for OpenSearch')
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
def test_disable_cluster_tag(dd_environment, instance, aggregator, new_cluster_tags):
    disable_instance = deepcopy(instance)
    disable_instance['disable_legacy_cluster_tag'] = True
    elastic_check = ESCheck('elastic', {}, instances=[disable_instance])
    elastic_check.check(None)
    es_version = elastic_check._get_es_version()

    # cluster stats
    expected_metrics = health_stats_for_version(es_version)
    expected_metrics.update(CLUSTER_PENDING_TASKS)
    for m_name in expected_metrics:
        aggregator.assert_metric(m_name, at_least=1, tags=new_cluster_tags)


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


@pytest.mark.integration
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
    all_other_metrics = {
        "elasticsearch.active_primary_shards",
        "elasticsearch.active_shards",
        "elasticsearch.breakers.fielddata.estimated_size_in_bytes",
        "elasticsearch.breakers.fielddata.overhead",
        "elasticsearch.thread_pool.write.active",
        "elasticsearch.thread_pool.write.completed",
        "elasticsearch.thread_pool.write.completed.count",
        "elasticsearch.thread_pool.write.queue",
        "elasticsearch.thread_pool.write.rejected",
        "elasticsearch.thread_pool.write.rejected.count",
        "elasticsearch.thread_pool.write.threads",
        "elasticsearch.thread_pool.write.threads.count",
        "elasticsearch.transport.rx_count",
        "elasticsearch.transport.rx_count.count",
        "elasticsearch.transport.rx_size",
        "elasticsearch.transport.rx_size.count",
        "elasticsearch.transport.server_open",
        "elasticsearch.transport.tx_count",
        "elasticsearch.transport.tx_count.count",
        "elasticsearch.transport.tx_size",
        "elasticsearch.transport.tx_size.count",
        "elasticsearch.unassigned_shards",
        "jvm.gc.collectors.old.collection_time",
        "jvm.gc.collectors.old.count",
        "jvm.gc.collectors.young.collection_time",
        "jvm.gc.collectors.young.count",
        "jvm.mem.heap_committed",
        "jvm.mem.heap_in_use",
        "jvm.mem.heap_max",
        "jvm.mem.heap_used",
        "jvm.mem.non_heap_committed",
        "jvm.mem.non_heap_used",
        "jvm.mem.pools.old.max",
        "jvm.mem.pools.old.used",
        "jvm.mem.pools.survivor.max",
        "jvm.mem.pools.survivor.used",
        "jvm.mem.pools.young.max",
        "jvm.mem.pools.young.used",
        "jvm.threads.count",
        "jvm.threads.peak_count",
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
        "elasticsearch.breakers.fielddata.tripped",
        "elasticsearch.breakers.inflight_requests.estimated_size_in_bytes",
        "elasticsearch.breakers.inflight_requests.overhead",
        "elasticsearch.breakers.inflight_requests.tripped",
        "elasticsearch.breakers.parent.estimated_size_in_bytes",
        "elasticsearch.breakers.parent.overhead",
        "elasticsearch.breakers.parent.tripped",
        "elasticsearch.breakers.request.estimated_size_in_bytes",
        "elasticsearch.breakers.request.overhead",
        "elasticsearch.breakers.request.tripped",
        "elasticsearch.cgroup.cpu.stat.number_of_elapsed_periods",
        "elasticsearch.cgroup.cpu.stat.number_of_times_throttled",
        "elasticsearch.cluster_status",
        "elasticsearch.delayed_unassigned_shards",
        "elasticsearch.docs.count",
        "elasticsearch.docs.deleted",
        "elasticsearch.fielddata.evictions",
        "elasticsearch.fielddata.evictions.count",
        "elasticsearch.fielddata.size",
        "elasticsearch.flush.total",
        "elasticsearch.flush.total.count",
        "elasticsearch.flush.total.time",
        "elasticsearch.flush.total.time.count",
        "elasticsearch.fs.total.available_in_bytes",
        "elasticsearch.fs.total.free_in_bytes",
        "elasticsearch.fs.total.total_in_bytes",
        "elasticsearch.get.current",
        "elasticsearch.get.exists.time",
        "elasticsearch.get.exists.time.count",
        "elasticsearch.get.exists.total",
        "elasticsearch.get.exists.total.count",
        "elasticsearch.get.missing.time",
        "elasticsearch.get.missing.time.count",
        "elasticsearch.get.missing.total",
        "elasticsearch.get.missing.total.count",
        "elasticsearch.get.time",
        "elasticsearch.get.time.count",
        "elasticsearch.get.total",
        "elasticsearch.get.total.count",
        "elasticsearch.http.current_open",
        "elasticsearch.http.total_opened",
        "elasticsearch.http.total_opened.count",
        "elasticsearch.indexing.delete.current",
        "elasticsearch.indexing.delete.time",
        "elasticsearch.indexing.delete.time.count",
        "elasticsearch.indexing.delete.total",
        "elasticsearch.indexing.delete.total.count",
        "elasticsearch.indexing.index.current",
        "elasticsearch.indexing.index.time",
        "elasticsearch.indexing.index.time.count",
        "elasticsearch.indexing.index.total",
        "elasticsearch.indexing.index.total.count",
        "elasticsearch.indices.count",
        "elasticsearch.indices.indexing.index_failed",
        "elasticsearch.indices.indexing.throttle_time",
        "elasticsearch.indices.indexing.throttle_time.count",
        "elasticsearch.indices.query_cache.cache_count",
        "elasticsearch.indices.query_cache.cache_size",
        "elasticsearch.indices.query_cache.evictions",
        "elasticsearch.indices.query_cache.evictions.count",
        "elasticsearch.indices.query_cache.hit_count",
        "elasticsearch.indices.query_cache.hit_count.count",
        "elasticsearch.indices.query_cache.memory_size_in_bytes",
        "elasticsearch.indices.query_cache.miss_count",
        "elasticsearch.indices.query_cache.miss_count.total",
        "elasticsearch.indices.query_cache.total_count",
        "elasticsearch.indices.recovery.current_as_source",
        "elasticsearch.indices.recovery.current_as_target",
        "elasticsearch.indices.recovery.throttle_time",
        "elasticsearch.indices.recovery.throttle_time.count",
        "elasticsearch.indices.request_cache.evictions",
        "elasticsearch.indices.request_cache.evictions.count",
        "elasticsearch.indices.request_cache.hit_count",
        "elasticsearch.indices.request_cache.memory_size_in_bytes",
        "elasticsearch.indices.request_cache.miss_count",
        "elasticsearch.indices.request_cache.miss_count.count",
        "elasticsearch.indices.segments.count",
        "elasticsearch.indices.segments.doc_values_memory_in_bytes",
        "elasticsearch.indices.segments.fixed_bit_set_memory_in_bytes",
        "elasticsearch.indices.segments.index_writer_memory_in_bytes",
        "elasticsearch.indices.segments.memory_in_bytes",
        "elasticsearch.indices.segments.norms_memory_in_bytes",
        "elasticsearch.indices.segments.stored_fields_memory_in_bytes",
        "elasticsearch.indices.segments.term_vectors_memory_in_bytes",
        "elasticsearch.indices.segments.terms_memory_in_bytes",
        "elasticsearch.indices.segments.version_map_memory_in_bytes",
        "elasticsearch.indices.translog.operations",
        "elasticsearch.indices.translog.size_in_bytes",
        "elasticsearch.initializing_shards",
        "elasticsearch.merges.current",
        "elasticsearch.merges.current.docs",
        "elasticsearch.merges.current.size",
        "elasticsearch.merges.total",
        "elasticsearch.merges.total.count",
        "elasticsearch.merges.total.docs",
        "elasticsearch.merges.total.docs.count",
        "elasticsearch.merges.total.size",
        "elasticsearch.merges.total.size.count",
        "elasticsearch.merges.total.time",
        "elasticsearch.merges.total.time.count",
        "elasticsearch.number_of_data_nodes",
        "elasticsearch.number_of_nodes",
        "elasticsearch.pending_tasks_priority_high",
        "elasticsearch.pending_tasks_priority_urgent",
        "elasticsearch.pending_tasks_time_in_queue",
        "elasticsearch.pending_tasks_total",
        "elasticsearch.process.cpu.percent",
        "elasticsearch.process.open_fd",
        "elasticsearch.refresh.external.total",
        "elasticsearch.refresh.external.total.time",
        "elasticsearch.refresh.total",
        "elasticsearch.refresh.total.count",
        "elasticsearch.refresh.total.time",
        "elasticsearch.refresh.total.time.count",
        "elasticsearch.relocating_shards",
        "elasticsearch.search.fetch.current",
        "elasticsearch.search.fetch.open_contexts",
        "elasticsearch.search.fetch.time",
        "elasticsearch.search.fetch.time.count",
        "elasticsearch.search.fetch.total",
        "elasticsearch.search.fetch.total.count",
        "elasticsearch.search.query.current",
        "elasticsearch.search.query.time",
        "elasticsearch.search.query.time.count",
        "elasticsearch.search.query.total",
        "elasticsearch.search.query.total.count",
        "elasticsearch.search.scroll.current",
        "elasticsearch.search.scroll.time",
        "elasticsearch.search.scroll.time.count",
        "elasticsearch.search.scroll.total",
        "elasticsearch.search.scroll.total.count",
        "elasticsearch.store.size",
        "elasticsearch.thread_pool.fetch_shard_started.active",
        "elasticsearch.thread_pool.fetch_shard_started.queue",
        "elasticsearch.thread_pool.fetch_shard_started.rejected",
        "elasticsearch.thread_pool.fetch_shard_started.threads",
        "elasticsearch.thread_pool.fetch_shard_store.active",
        "elasticsearch.thread_pool.fetch_shard_store.queue",
        "elasticsearch.thread_pool.fetch_shard_store.rejected",
        "elasticsearch.thread_pool.fetch_shard_store.threads",
        "elasticsearch.thread_pool.flush.active",
        "elasticsearch.thread_pool.flush.completed",
        "elasticsearch.thread_pool.flush.completed.count",
        "elasticsearch.thread_pool.flush.queue",
        "elasticsearch.thread_pool.flush.rejected",
        "elasticsearch.thread_pool.flush.rejected.count",
        "elasticsearch.thread_pool.flush.threads",
        "elasticsearch.thread_pool.flush.threads.count",
        "elasticsearch.thread_pool.force_merge.active",
        "elasticsearch.thread_pool.force_merge.queue",
        "elasticsearch.thread_pool.force_merge.rejected",
        "elasticsearch.thread_pool.force_merge.threads",
        "elasticsearch.thread_pool.generic.active",
        "elasticsearch.thread_pool.generic.completed",
        "elasticsearch.thread_pool.generic.completed.count",
        "elasticsearch.thread_pool.generic.queue",
        "elasticsearch.thread_pool.generic.rejected",
        "elasticsearch.thread_pool.generic.rejected.count",
        "elasticsearch.thread_pool.generic.threads",
        "elasticsearch.thread_pool.generic.threads.count",
        "elasticsearch.thread_pool.get.active",
        "elasticsearch.thread_pool.get.completed",
        "elasticsearch.thread_pool.get.completed.count",
        "elasticsearch.thread_pool.get.queue",
        "elasticsearch.thread_pool.get.rejected",
        "elasticsearch.thread_pool.get.rejected.count",
        "elasticsearch.thread_pool.get.threads",
        "elasticsearch.thread_pool.get.threads.count",
        "elasticsearch.thread_pool.listener.active",
        "elasticsearch.thread_pool.listener.queue",
        "elasticsearch.thread_pool.listener.rejected",
        "elasticsearch.thread_pool.listener.rejected.count",
        "elasticsearch.thread_pool.listener.threads",
        "elasticsearch.thread_pool.listener.threads.count",
        "elasticsearch.thread_pool.management.active",
        "elasticsearch.thread_pool.management.completed",
        "elasticsearch.thread_pool.management.completed.count",
        "elasticsearch.thread_pool.management.queue",
        "elasticsearch.thread_pool.management.rejected",
        "elasticsearch.thread_pool.management.rejected.count",
        "elasticsearch.thread_pool.management.threads",
        "elasticsearch.thread_pool.management.threads.count",
        "elasticsearch.thread_pool.refresh.active",
        "elasticsearch.thread_pool.refresh.completed",
        "elasticsearch.thread_pool.refresh.completed.count",
        "elasticsearch.thread_pool.refresh.queue",
        "elasticsearch.thread_pool.refresh.rejected",
        "elasticsearch.thread_pool.refresh.rejected.count",
        "elasticsearch.thread_pool.refresh.threads",
        "elasticsearch.thread_pool.refresh.threads.count",
        "elasticsearch.thread_pool.search.active",
        "elasticsearch.thread_pool.search.completed",
        "elasticsearch.thread_pool.search.completed.count",
        "elasticsearch.thread_pool.search.queue",
        "elasticsearch.thread_pool.search.rejected",
        "elasticsearch.thread_pool.search.rejected.count",
        "elasticsearch.thread_pool.search.threads",
        "elasticsearch.thread_pool.search.threads.count",
        "elasticsearch.thread_pool.snapshot.active",
        "elasticsearch.thread_pool.snapshot.completed",
        "elasticsearch.thread_pool.snapshot.completed.count",
        "elasticsearch.thread_pool.snapshot.queue",
        "elasticsearch.thread_pool.snapshot.rejected",
        "elasticsearch.thread_pool.snapshot.rejected.count",
        "elasticsearch.thread_pool.snapshot.threads",
        "elasticsearch.thread_pool.snapshot.threads.count",
        "elasticsearch.thread_pool.warmer.active",
        "elasticsearch.thread_pool.warmer.completed",
        "elasticsearch.thread_pool.warmer.queue",
        "elasticsearch.thread_pool.warmer.rejected",
        "elasticsearch.thread_pool.warmer.threads",
    }
    for m_name in all_other_metrics:
        aggregator.assert_metric(m_name)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_metric_type=False)


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
        aggregator.assert_metric(m_name, tags=cluster_tags + ['index_name:.testindex'])


@pytest.mark.integration
def test_cat_allocation_metrics(dd_environment, aggregator, instance, cluster_tags):
    instance['cat_allocation_stats'] = True
    elastic_check = ESCheck('elastic', {}, instances=[instance])

    elastic_check.check(None)
    for m_name in CAT_ALLOCATION_METRICS:
        aggregator.assert_metric(m_name)


@pytest.mark.integration
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
