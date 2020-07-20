# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

from copy import deepcopy
from distutils.version import StrictVersion

import mock
import pytest
import redis

from datadog_checks.redisdb import Redis

from .common import HOST, PASSWORD, PORT, REDIS_VERSION
from .utils import requires_static_version

# Following metrics are tagged by db
DB_TAGGED_METRICS = ['redis.persist.percent', 'redis.expires.percent', 'redis.persist', 'redis.keys', 'redis.expires']

STAT_METRICS = ['redis.command.calls', 'redis.command.usec_per_call']

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_aof_loading_metrics(aggregator, redis_instance):
    """AOF loading metrics are only available when redis is loading an AOF file.
    It is not possible to collect them using integration/e2e testing so let's mock
    redis output to assert that they are collected correctly (assuming that the redis output is formatted
    correctly)."""
    with mock.patch("redis.Redis") as redis:
        redis_check = Redis('redisdb', {}, [redis_instance])
        conn = redis.return_value
        conn.config_get.return_value = {}
        conn.info = (
            lambda *args: []
            if args
            else {
                'role': 'foo',
                'total_commands_processed': 0,
                'loading_total_bytes': 42,
                'loading_loaded_bytes': 43,
                'loading_loaded_perc': 44,
                'loading_eta_seconds': 45,
            }
        )
        redis_check._check_db()

        aggregator.assert_metric('redis.info.latency_ms')
        aggregator.assert_metric('redis.net.commands', 0)
        aggregator.assert_metric('redis.key.length', 0)

        aggregator.assert_metric('redis.aof.loading_total_bytes', 42)
        aggregator.assert_metric('redis.aof.loading_loaded_bytes', 43)
        aggregator.assert_metric('redis.aof.loading_loaded_perc', 44)
        aggregator.assert_metric('redis.aof.loading_eta_seconds', 45)
        aggregator.assert_all_metrics_covered()


def test_redis_default(aggregator, redis_auth, redis_instance):
    db = redis.Redis(port=PORT, db=14, password=PASSWORD, host=HOST)
    db.flushdb()
    db.lpush("test_list", 1)
    db.lpush("test_list", 2)
    db.lpush("test_list", 3)
    db.set("key1", "value")
    db.set("key2", "value")
    db.setex("expirekey", 1000, "expirevalue")

    redis_check = Redis('redisdb', {}, [redis_instance])
    redis_check.check(redis_instance)

    # check the aggregator received some metrics
    assert aggregator.metric_names, "No metrics returned"

    # check those metrics have the right tags
    expected = ['foo:bar', 'redis_host:{}'.format(HOST), 'redis_port:6379', 'redis_role:master']
    expected_db = expected + ['redis_db:db14']

    assert aggregator.metric_names
    for name in aggregator.metric_names:
        if name in DB_TAGGED_METRICS:
            aggregator.assert_metric(name, tags=expected_db)
        elif name not in ('redis.key.length', 'redis.net.connections'):
            aggregator.assert_metric(name, tags=expected)

    aggregator.assert_metric('redis.key.length', 3, count=1, tags=expected_db + ['key:test_list', 'key_type:list'])
    aggregator.assert_metric('redis.net.connections', count=1, tags=expected + ['source:unknown'])

    aggregator.assert_metric('redis.net.maxclients')

    # in the old tests these was explicitly asserted, keeping it like that
    assert 'redis.net.commands' in aggregator.metric_names
    version = db.info().get('redis_version')
    if StrictVersion(version) >= StrictVersion('2.6.0'):
        # instantaneous_ops_per_sec info is only available on redis>=2.6
        assert 'redis.net.instantaneous_ops_per_sec' in aggregator.metric_names
    db.flushdb()


def test_service_check(aggregator, redis_auth, redis_instance):
    redis_check = Redis('redisdb', {}, [redis_instance])
    redis_check.check(redis_instance)

    assert len(aggregator.service_checks('redis.can_connect')) == 1
    sc = aggregator.service_checks('redis.can_connect')[0]
    assert sc.tags == ['foo:bar', 'redis_host:{}'.format(HOST), 'redis_port:6379', 'redis_role:master']


def test_disabled_config_get(aggregator, redis_auth, redis_instance):
    redis_check = Redis('redisdb', {}, [redis_instance])
    with mock.patch.object(redis.client.Redis, 'config_get') as get:
        get.side_effect = redis.ResponseError()
        redis_check.check(redis_instance)

    assert len(aggregator.service_checks('redis.can_connect')) == 1
    sc = aggregator.service_checks('redis.can_connect')[0]
    assert sc.tags == ['foo:bar', 'redis_host:{}'.format(HOST), 'redis_port:6379', 'redis_role:master']


@requires_static_version
@pytest.mark.usefixtures('dd_environment')
def test_metadata(master_instance, datadog_agent):
    redis_check = Redis('redisdb', {}, [master_instance])
    redis_check.check_id = 'test:123'

    redis_check.check(master_instance)

    major, minor = REDIS_VERSION.split('.')
    version_metadata = {'version.scheme': 'semver', 'version.major': major, 'version.minor': minor}

    datadog_agent.assert_metadata('test:123', version_metadata)
    # We parse the version set in tox which is X.Y so we don't
    # know `version.patch`, and therefore also `version.raw`.
    datadog_agent.assert_metadata_count(len(version_metadata) + 2)


def test_redis_command_stats(aggregator, redis_instance):
    db = redis.Redis(port=PORT, db=14, password=PASSWORD, host=HOST)
    version = db.info().get('redis_version')
    if StrictVersion(version) < StrictVersion('2.6.0'):
        # Command stats only works with Redis >= 2.6.0
        return

    redis_instance['command_stats'] = True
    redis_check = Redis('redisdb', {}, [redis_instance])
    redis_check.check(redis_instance)

    for name in STAT_METRICS:
        aggregator.assert_metric(name)

    # Check the command stats for INFO, since we know we've called it
    for m in aggregator.metrics('redis.command.calls'):
        if 'command:info' in m.tags:
            found = True
            break
    else:
        found = False

    assert found


def test__check_key_lengths_misconfig(aggregator, redis_instance):
    """
    The check shouldn't send anything if misconfigured
    """
    redis_check = Redis('redisdb', {}, [redis_instance])
    c = redis_check._get_conn(redis_instance)

    # `keys` param is missing
    del redis_instance['keys']
    redis_check._check_key_lengths(c, [])
    assert len(list(aggregator.metrics('redis.key.length'))) == 0

    # `keys` is not a list
    redis_instance['keys'] = 'FOO'
    redis_check._check_key_lengths(c, [])
    assert len(list(aggregator.metrics('redis.key.length'))) == 0

    # `keys` is an empty list
    redis_instance['keys'] = []
    redis_check._check_key_lengths(c, [])
    assert len(list(aggregator.metrics('redis.key.length'))) == 0


def test__check_key_lengths_single_db(aggregator, redis_instance):
    """
    Keys are stored in multiple databases but we collect data from
    one database only
    """
    redis_check = Redis('redisdb', {}, [redis_instance])
    tmp = deepcopy(redis_instance)

    # fill db 0
    tmp['db'] = 0
    conn = redis_check._get_conn(tmp)
    conn.flushdb()
    conn.lpush('test_foo', 'value1')
    conn.lpush('test_foo', 'value2')

    # fill db 3
    tmp['db'] = 3
    conn = redis_check._get_conn(tmp)
    conn.flushdb()
    conn.lpush('test_foo', 'value3')
    conn.lpush('test_foo', 'value4')

    # collect only from 3
    redis_instance['db'] = 3
    redis_check._check_key_lengths(conn, [])

    # metric should be only one, not regarding the number of databases
    aggregator.assert_metric('redis.key.length', count=1)

    # that single metric should have value=2
    aggregator.assert_metric('redis.key.length', value=2)


def test__check_key_lengths_multi_db(aggregator, redis_instance):
    """
    Keys are stored across different databases
    """
    redis_check = Redis('redisdb', {}, [redis_instance])
    c = redis_check._get_conn(redis_instance)
    tmp = deepcopy(redis_instance)

    # also add a specific key to the instance
    redis_instance['keys'].append('missing_key')

    # fill db 0
    tmp['db'] = 0
    conn = redis_check._get_conn(tmp)
    conn.flushdb()
    conn.lpush('test_foo', 'value1')
    conn.lpush('test_foo', 'value2')
    conn.lpush('test_bar', 'value1')

    # fill db 3
    tmp['db'] = 3
    conn = redis_check._get_conn(tmp)
    conn.flushdb()
    conn.lpush('test_foo', 'value3')
    conn.lpush('test_foo', 'value4')

    redis_check._check_key_lengths(c, [])
    aggregator.assert_metric('redis.key.length', count=4)
    aggregator.assert_metric('redis.key.length', value=2, tags=['key:test_foo', 'key_type:list', 'redis_db:db0'])
    aggregator.assert_metric('redis.key.length', value=2, tags=['key:test_foo', 'key_type:list', 'redis_db:db3'])
    aggregator.assert_metric('redis.key.length', value=1, tags=['key:test_bar', 'key_type:list', 'redis_db:db0'])
    aggregator.assert_metric('redis.key.length', value=0, tags=['key:missing_key'])
