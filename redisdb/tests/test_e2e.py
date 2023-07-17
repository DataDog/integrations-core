# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.base import is_affirmative
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.redisdb import Redis

from . import common
from .common import REDIS_VERSION

pytestmark = pytest.mark.e2e


def assert_common_metrics(aggregator):
    base_tags = ['redis_host:{}'.format(common.HOST), 'redis_port:6382']

    aggregator.assert_service_check('redis.can_connect', status=Redis.OK, tags=base_tags)
    tags = base_tags + ['redis_role:master']
    aggregator.assert_metric('redis.mem.fragmentation_ratio', count=2, tags=tags)
    aggregator.assert_metric('redis.rdb.bgsave', count=2, tags=tags)
    aggregator.assert_metric('redis.aof.last_rewrite_time', count=2, tags=tags)
    aggregator.assert_metric('redis.replication.master_repl_offset', count=2, tags=tags)
    aggregator.assert_metric('redis.net.rejected', count=2, tags=tags)
    aggregator.assert_metric('redis.cpu.sys_children', count=1, tags=tags)
    aggregator.assert_metric('redis.aof.rewrite', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.maxmemory', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.lua', count=2, tags=tags)
    aggregator.assert_metric('redis.net.instantaneous_ops_per_sec', count=2, tags=tags)
    aggregator.assert_metric('redis.perf.latest_fork_usec', count=2, tags=tags)
    aggregator.assert_metric('redis.net.total_connections_received', count=2, tags=tags)
    aggregator.assert_metric('redis.net.instantaneous_input', count=2, tags=tags)
    aggregator.assert_metric('redis.net.instantaneous_output', count=2, tags=tags)
    aggregator.assert_metric('redis.keys.evicted', count=2, tags=tags)
    aggregator.assert_metric('redis.net.slaves', count=2, tags=tags)
    aggregator.assert_metric('redis.clients.blocked', count=2, tags=tags)
    aggregator.assert_metric('redis.stats.keyspace_misses', count=1, tags=tags)
    aggregator.assert_metric('redis.pubsub.channels', count=2, tags=tags)
    aggregator.assert_metric('redis.net.clients', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.used', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.peak', count=2, tags=tags)
    aggregator.assert_metric('redis.stats.keyspace_hits', count=1, tags=tags)
    aggregator.assert_metric('redis.net.commands', count=1, tags=tags)
    aggregator.assert_metric('redis.replication.backlog_histlen', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.rss', count=2, tags=tags)
    aggregator.assert_metric('redis.cpu.sys', count=1, tags=tags)
    aggregator.assert_metric('redis.pubsub.patterns', count=2, tags=tags)
    aggregator.assert_metric('redis.keys.expired', count=2, tags=tags)
    aggregator.assert_metric('redis.info.latency_ms', count=2, tags=tags)
    aggregator.assert_metric('redis.ping.latency_ms', count=2, tags=tags)
    aggregator.assert_metric('redis.cpu.user', count=1, tags=tags)
    aggregator.assert_metric('redis.cpu.user_children', count=1, tags=tags)
    aggregator.assert_metric('redis.rdb.last_bgsave_time', count=2, tags=tags)
    aggregator.assert_metric('redis.rdb.changes_since_last', count=2, tags=tags)

    aggregator.assert_metric('redis.mem.startup', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.running', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.hits', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.misses', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.key_hits', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.key_misses', count=2, tags=tags)
    aggregator.assert_metric('redis.clients.recent_max_input_buffer', count=2, tags=tags)
    aggregator.assert_metric('redis.clients.recent_max_output_buffer', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.overhead', count=2, tags=tags)

    if not is_affirmative(common.CLOUD_ENV):
        assert_non_cloud_metrics(aggregator, tags)

    tags_with_db = tags + ['redis_db:db14']
    aggregator.assert_metric('redis.expires', count=2, tags=tags_with_db)
    aggregator.assert_metric('redis.expires.percent', count=2, tags=tags_with_db)
    aggregator.assert_metric('redis.persist', count=2, tags=tags_with_db)
    aggregator.assert_metric('redis.persist.percent', count=2, tags=tags_with_db)
    aggregator.assert_metric('redis.keys', count=2, tags=tags_with_db)

    aggregator.assert_metric('redis.key.length', count=2, tags=(['key:test_key1', 'key_type:list'] + tags_with_db))
    aggregator.assert_metric('redis.key.length', count=2, tags=(['key:test_key2', 'key_type:list'] + tags_with_db))
    aggregator.assert_metric('redis.key.length', count=2, tags=(['key:test_key3', 'key_type:list'] + tags_with_db))
    aggregator.assert_metric(
        'redis.key.length', count=2, value=2, tags=(['key:test_key4', 'key_type:stream'] + tags_with_db)
    )

    aggregator.assert_metric('redis.replication.delay', count=2)


def test_e2e(dd_agent_check, master_instance):
    redis_version = REDIS_VERSION.split('.')[0]
    aggregator = dd_agent_check(master_instance, rate=True)
    assert_common_metrics(aggregator)

    tags = ['redis_host:{}'.format(common.HOST), 'redis_port:6382', 'redis_role:master']

    if redis_version == 'latest' or int(redis_version) > 5:
        aggregator.assert_metric('redis.server.io_threads_active', count=2, tags=tags)
        aggregator.assert_metric('redis.stats.io_threaded_reads_processed', count=1, tags=tags)
        aggregator.assert_metric('redis.stats.io_threaded_writes_processed', count=1, tags=tags)
    if redis_version == 'latest' or int(redis_version) > 6:
        aggregator.assert_metric('redis.cpu.sys_main_thread', count=1, tags=tags)
        aggregator.assert_metric('redis.cpu.user_main_thread', count=1, tags=tags)

    assert_optional_slowlog_metrics(aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def assert_non_cloud_metrics(aggregator, tags):
    """Certain metrics cannot be collected in cloud environments due to disabled commands"""
    aggregator.assert_metric('redis.net.connections', count=2, tags=tags + ['source:unknown'])
    aggregator.assert_metric('redis.net.maxclients', count=2, tags=tags)


def assert_optional_slowlog_metrics(aggregator):
    aggregator.assert_metric('redis.slowlog.micros.95percentile', at_least=0)
    aggregator.assert_metric('redis.slowlog.micros.avg', at_least=0)
    aggregator.assert_metric('redis.slowlog.micros.count', at_least=0)
    aggregator.assert_metric('redis.slowlog.micros.max', at_least=0)
    aggregator.assert_metric('redis.slowlog.micros.median', at_least=0)
