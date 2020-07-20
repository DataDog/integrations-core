# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.redisdb import Redis

from . import common

pytestmark = pytest.mark.e2e


def assert_common_metrics(aggregator):
    tags = ['redis_host:{}'.format(common.HOST), 'redis_port:6382', 'redis_role:master']

    aggregator.assert_service_check('redis.can_connect', status=Redis.OK, tags=tags)

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
    aggregator.assert_metric('redis.keys.evicted', count=2, tags=tags)
    aggregator.assert_metric('redis.net.slaves', count=2, tags=tags)
    aggregator.assert_metric('redis.net.maxclients', count=2, tags=tags)
    aggregator.assert_metric('redis.clients.blocked', count=2, tags=tags)
    aggregator.assert_metric('redis.stats.keyspace_misses', count=1, tags=tags)
    aggregator.assert_metric('redis.pubsub.channels', count=2, tags=tags)
    aggregator.assert_metric('redis.net.clients', count=2, tags=tags)
    aggregator.assert_metric('redis.net.connections', count=2, tags=tags + ['source:unknown'])
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
    aggregator.assert_metric('redis.cpu.user', count=1, tags=tags)
    aggregator.assert_metric('redis.cpu.user_children', count=1, tags=tags)
    aggregator.assert_metric('redis.rdb.last_bgsave_time', count=2, tags=tags)
    aggregator.assert_metric('redis.rdb.changes_since_last', count=2, tags=tags)

    tags += ['redis_db:db14']
    aggregator.assert_metric('redis.expires', count=2, tags=tags)
    aggregator.assert_metric('redis.expires.percent', count=2, tags=tags)
    aggregator.assert_metric('redis.persist', count=2, tags=tags)
    aggregator.assert_metric('redis.persist.percent', count=2, tags=tags)
    aggregator.assert_metric('redis.keys', count=2, tags=tags)

    aggregator.assert_metric('redis.key.length', count=2, tags=(['key:test_key1', 'key_type:list'] + tags))
    aggregator.assert_metric('redis.key.length', count=2, tags=(['key:test_key2', 'key_type:list'] + tags))
    aggregator.assert_metric('redis.key.length', count=2, tags=(['key:test_key3', 'key_type:list'] + tags))

    aggregator.assert_metric('redis.replication.delay', count=2)


@pytest.mark.skipif(os.environ.get('REDIS_VERSION') != '3.2', reason='Test for redisdb v3.2')
def test_e2e_v_3_2(dd_agent_check, master_instance):
    aggregator = dd_agent_check(master_instance, rate=True)

    assert_common_metrics(aggregator)

    tags = ['redis_host:{}'.format(common.HOST), 'redis_port:6382', 'redis_role:master']
    aggregator.assert_metric('redis.clients.biggest_input_buf', count=2, tags=tags)
    aggregator.assert_metric('redis.clients.longest_output_list', count=2, tags=tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(os.environ.get('REDIS_VERSION') != '4.0', reason='Test for redisdb v4.0')
def test_e2e_v_4_0(dd_agent_check, master_instance):
    aggregator = dd_agent_check(master_instance, rate=True)

    assert_common_metrics(aggregator)

    tags = ['redis_host:{}'.format(common.HOST), 'redis_port:6382', 'redis_role:master']
    aggregator.assert_metric('redis.clients.biggest_input_buf', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.overhead', count=2, tags=tags)
    aggregator.assert_metric('redis.clients.longest_output_list', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.startup', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.running', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.hits', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.misses', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.key_hits', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.key_misses', count=2, tags=tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(os.environ.get('REDIS_VERSION') != 'latest', reason='Test for the latest redisdb version')
def test_e2e_v_latest(dd_agent_check, master_instance):
    aggregator = dd_agent_check(master_instance, rate=True)

    assert_common_metrics(aggregator)

    tags = ['redis_host:{}'.format(common.HOST), 'redis_port:6382', 'redis_role:master']
    aggregator.assert_metric('redis.mem.overhead', count=2, tags=tags)
    aggregator.assert_metric('redis.mem.startup', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.running', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.hits', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.misses', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.key_hits', count=2, tags=tags)
    aggregator.assert_metric('redis.active_defrag.key_misses', count=2, tags=tags)

    aggregator.assert_all_metrics_covered()
