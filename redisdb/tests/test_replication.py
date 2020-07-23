# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

import pytest
import redis

from datadog_checks.redisdb import Redis

from .common import HOST, MASTER_PORT, REPLICA_PORT, UNHEALTHY_REPLICA_PORT

REPLICA_METRICS = [
    'redis.replication.delay',
    'redis.replication.backlog_histlen',
    'redis.replication.master_repl_offset',
]

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_redis_replication_link_metric(aggregator, replica_instance, dd_environment):
    metric_name = 'redis.replication.master_link_down_since_seconds'

    redis_check = Redis('redisdb', {}, [replica_instance])
    redis_check.check(replica_instance)
    aggregator.assert_metric(metric_name, value=0)

    # Test the same on the unhealthy host
    aggregator.reset()
    replica_instance['port'] = UNHEALTHY_REPLICA_PORT
    redis_check.check(replica_instance)
    metrics = aggregator.metrics(metric_name)
    assert len(metrics) == 1
    assert metrics[0].value > 0


def test_redis_replication_service_check(aggregator, replica_instance, dd_environment):
    service_check_name = 'redis.replication.master_link_status'
    redis_check = Redis('redisdb', {}, [replica_instance])
    redis_check.check(replica_instance)
    assert len(aggregator.service_checks(service_check_name)) == 1

    # Healthy host
    assert aggregator.service_checks(service_check_name)[0].status == Redis.OK

    # Unhealthy host
    aggregator.reset()
    replica_instance['port'] = UNHEALTHY_REPLICA_PORT
    redis_check.check(replica_instance)
    assert len(aggregator.service_checks(service_check_name)) == 1
    assert aggregator.service_checks(service_check_name)[0].status == Redis.CRITICAL


def test_redis_repl(aggregator, dd_environment, master_instance):
    master_db = redis.Redis(port=MASTER_PORT, db=14, host=HOST)
    replica_db = redis.Redis(port=REPLICA_PORT, db=14, host=HOST)
    master_db.flushdb()

    # Ensure the replication works before running the tests
    master_db.set('replicated:test', 'true')
    assert replica_db.get('replicated:test') == b'true'

    redis_check = Redis('redisdb', {}, [master_instance])
    redis_check.check(master_instance)

    for name in REPLICA_METRICS:
        aggregator.assert_metric(name)
