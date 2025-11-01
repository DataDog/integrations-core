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
    aggregator.assert_metric('redis.mem.dataset', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.fragmentation', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.clients_slaves', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.clients_normal', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.scripts', count=2, tags=tags)

    aggregator.assert_metric('redis.allocator.active', count=2, tags=tags)
    aggregator.assert_metric('redis.allocator.allocated', count=2, tags=tags)
    aggregator.assert_metric('redis.allocator.frag_ratio', count=2, tags=tags)
    aggregator.assert_metric('redis.allocator.resident', count=2, tags=tags)
    aggregator.assert_metric('redis.allocator.rss_bytes', count=2, tags=tags)
    aggregator.assert_metric('redis.allocator.rss_ratio', count=2, tags=tags)
    aggregator.assert_metric('redis.aof.enabled', count=2, tags=tags)
    aggregator.assert_metric('redis.aof.last_cow_size', count=2, tags=tags)
    aggregator.assert_metric('redis.aof.rewrite.current_time_sec', count=2, tags=tags)
    aggregator.assert_metric('redis.aof.rewrite.scheduled', count=2, tags=tags)
    aggregator.assert_metric('redis.cluster.enabled', count=2, tags=tags)
    aggregator.assert_metric('redis.expired.time_cap_reached_count', count=2, tags=tags)
    aggregator.assert_metric('redis.loading.loading', count=2, tags=tags)
    aggregator.assert_metric('redis.memory.aof_buffer', count=2, tags=tags)
    aggregator.assert_metric('redis.memory.not_counted_for_evict', count=2, tags=tags)
    aggregator.assert_metric('redis.memory.replication_backlog', count=2, tags=tags)
    aggregator.assert_metric('redis.memory.rss_overhead_bytes', count=2, tags=tags)
    aggregator.assert_metric('redis.memory.rss_overhead_ratio', count=2, tags=tags)
    aggregator.assert_metric('redis.net.migrate_cached_sockets', count=2, tags=tags)
    aggregator.assert_metric('redis.net.total_input_bytes', count=2, tags=tags)
    aggregator.assert_metric('redis.net.total_output_bytes', count=2, tags=tags)
    aggregator.assert_metric('redis.rdb.current_bgsave_time_sec', count=2, tags=tags)
    aggregator.assert_metric('redis.rdb.last_cow_size', count=2, tags=tags)
    aggregator.assert_metric('redis.rdb.last_save_time', count=2, tags=tags)
    aggregator.assert_metric('redis.replication.backlog_active', count=2, tags=tags)
    aggregator.assert_metric('redis.replication.backlog_first_byte_offset', count=2, tags=tags)
    aggregator.assert_metric('redis.replication.backlog_size', count=2, tags=tags)
    aggregator.assert_metric('redis.replication.second_repl_offset', count=2, tags=tags)
    aggregator.assert_metric('redis.replication.slave.expires_tracked_keys', count=2, tags=tags)
    aggregator.assert_metric('redis.replication.sync.full', count=2, tags=tags)
    aggregator.assert_metric('redis.replication.sync.partial_err', count=2, tags=tags)
    aggregator.assert_metric('redis.replication.sync.partial_ok', count=2, tags=tags)
    aggregator.assert_metric('redis.scripts.cached', count=2, tags=tags)

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
        aggregator.assert_metric('redis.clients.timeout_table', count=2, tags=tags)
        aggregator.assert_metric('redis.errors.unexpected_replies', count=2, tags=tags)
        aggregator.assert_metric('redis.expire_cycle.cpu_milliseconds', count=2, tags=tags)
        aggregator.assert_metric('redis.ops.reads_processed', count=2, tags=tags)
        aggregator.assert_metric('redis.ops.writes_processed', count=2, tags=tags)
        aggregator.assert_metric('redis.tracking.clients', count=2, tags=tags)
        aggregator.assert_metric('redis.tracking.total_items', count=2, tags=tags)
        aggregator.assert_metric('redis.tracking.total_keys', count=2, tags=tags)
        aggregator.assert_metric('redis.tracking.total_prefixes', count=2, tags=tags)
    if redis_version == 'latest' or int(redis_version) > 6:
        aggregator.assert_metric('redis.cpu.sys_main_thread', count=1, tags=tags)
        aggregator.assert_metric('redis.cpu.user_main_thread', count=1, tags=tags)
        aggregator.assert_metric('redis.mem.functions', count=2, tags=tags)
        aggregator.assert_metric('redis.mem.scripts_eval', count=2, tags=tags)
        aggregator.assert_metric('redis.mem.total_replication_buffers', count=2, tags=tags)
        aggregator.assert_metric('redis.mem.vm_eval', count=2, tags=tags)
        aggregator.assert_metric('redis.mem.vm_functions', count=2, tags=tags)
        aggregator.assert_metric('redis.mem.vm_total', count=2, tags=tags)
        aggregator.assert_metric('redis.replication.input_total_bytes', count=2, tags=tags)
        aggregator.assert_metric('redis.replication.output_total_bytes', count=2, tags=tags)
        aggregator.assert_metric('redis.aof.rewrites', count=2, tags=tags)
        aggregator.assert_metric('redis.clients.evicted', count=2, tags=tags)
        aggregator.assert_metric('redis.cluster.connections', count=2, tags=tags)
        aggregator.assert_metric('redis.cow.current_peak', count=2, tags=tags)
        aggregator.assert_metric('redis.cow.current_size', count=2, tags=tags)
        aggregator.assert_metric('redis.cow.current_size_age', count=2, tags=tags)
        aggregator.assert_metric('redis.defrag.current_active_time', count=2, tags=tags)
        aggregator.assert_metric('redis.defrag.total_active_time', count=2, tags=tags)
        aggregator.assert_metric('redis.errors.total_replies', count=2, tags=tags)
        aggregator.assert_metric('redis.eviction.current_exceeded_time', count=2, tags=tags)
        aggregator.assert_metric('redis.eviction.total_exceeded_time', count=2, tags=tags)
        aggregator.assert_metric('redis.fork.total', count=2, tags=tags)
        aggregator.assert_metric('redis.functions.count', count=2, tags=tags)
        aggregator.assert_metric('redis.libraries.count', count=2, tags=tags)
        aggregator.assert_metric('redis.memory.cluster_links', count=2, tags=tags)
        aggregator.assert_metric('redis.pubsub.shard_channels', count=2, tags=tags)
        aggregator.assert_metric('redis.rdb.last_load.keys_expired', count=2, tags=tags)
        aggregator.assert_metric('redis.rdb.last_load.keys_loaded', count=2, tags=tags)
        aggregator.assert_metric('redis.rdb.saves', count=2, tags=tags)
        aggregator.assert_metric('redis.replication.instantaneous_input_kbps', count=2, tags=tags)
        aggregator.assert_metric('redis.replication.instantaneous_output_kbps', count=2, tags=tags)
        aggregator.assert_metric('redis.reply_buffer.expands', count=2, tags=tags)
        aggregator.assert_metric('redis.reply_buffer.shrinks', count=2, tags=tags)
    if redis_version == 'latest' or int(redis_version) > 7:
        aggregator.assert_metric('redis.acl.denied.auth', count=2, tags=tags)
        aggregator.assert_metric('redis.acl.denied.channel', count=2, tags=tags)
        aggregator.assert_metric('redis.acl.denied.cmd', count=2, tags=tags)
        aggregator.assert_metric('redis.acl.denied.key', count=2, tags=tags)
        aggregator.assert_metric('redis.allocator.muzzy', count=2, tags=tags)
        aggregator.assert_metric('redis.clients.output_buffer_limit_disconnections', count=2, tags=tags)
        aggregator.assert_metric('redis.clients.query_buffer_limit_disconnections', count=2, tags=tags)
        aggregator.assert_metric('redis.clients.watching', count=2, tags=tags)
        aggregator.assert_metric('redis.eventloop.cycles', count=2, tags=tags)
        aggregator.assert_metric('redis.eventloop.duration_cmd_sum', count=2, tags=tags)
        aggregator.assert_metric('redis.eventloop.duration_sum', count=2, tags=tags)
        aggregator.assert_metric('redis.eventloop.instantaneous_cycles_per_sec', count=2, tags=tags)
        aggregator.assert_metric('redis.eventloop.instantaneous_duration_usec', count=2, tags=tags)
        aggregator.assert_metric('redis.expired.subkeys', count=2, tags=tags)
        aggregator.assert_metric('redis.keys.total_blocking', count=2, tags=tags)
        aggregator.assert_metric('redis.keys.total_blocking_on_nokey', count=2, tags=tags)
        aggregator.assert_metric('redis.keys.total_watched', count=2, tags=tags)
        aggregator.assert_metric('redis.memory.overhead_db_hashtable_rehashing', count=2, tags=tags)
        aggregator.assert_metric('redis.pubsub.clients', count=2, tags=tags)
        aggregator.assert_metric('redis.scripts.evicted', count=2, tags=tags)

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
