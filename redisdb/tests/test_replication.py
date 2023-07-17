# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

import pytest
import redis

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.redisdb import Redis

from .common import HOST, MASTER_PORT, REPLICA_PORT, UNHEALTHY_REPLICA_PORT

REPLICA_METRICS = [
    'redis.replication.delay',
    'redis.replication.backlog_histlen',
    'redis.replication.master_repl_offset',
]

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_redis_replication_link_metric(aggregator, replica_instance, dd_run_check, check):
    redis_check = check(replica_instance)
    dd_run_check(redis_check)
    aggregator.assert_metric('redis.replication.master_link_down_since_seconds', value=0)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_redis_replication_link_metric_with_unhealthy_host(aggregator, replica_instance, dd_run_check, check):
    replica_instance['port'] = UNHEALTHY_REPLICA_PORT
    redis_check = check(replica_instance)
    redis_check.check(replica_instance)
    metrics = aggregator.metrics('redis.replication.master_link_down_since_seconds')

    assert len(metrics) == 1
    assert metrics[0].value != 0

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.parametrize(
    'port, expected_status',
    [
        pytest.param(
            REPLICA_PORT,
            Redis.OK,
            id='healthy',
        ),
        pytest.param(
            UNHEALTHY_REPLICA_PORT,
            Redis.CRITICAL,
            id="unhealthy",
        ),
    ],
)
def test_redis_replication_service_check(aggregator, replica_instance, dd_run_check, check, port, expected_status):
    replica_instance['port'] = port
    service_check_name = 'redis.replication.master_link_status'

    redis_check = check(replica_instance)
    dd_run_check(redis_check)
    assert len(aggregator.service_checks(service_check_name)) == 1
    assert aggregator.service_checks(service_check_name)[0].status == expected_status


def test_redis_repl(aggregator, dd_run_check, check, master_instance):
    master_db = redis.Redis(port=MASTER_PORT, db=14, host=HOST)
    replica_db = redis.Redis(port=REPLICA_PORT, db=14, host=HOST)
    master_db.flushdb()

    # Ensure the replication works before running the tests
    master_db.set('replicated:test', 'true')
    assert replica_db.get('replicated:test') == b'true'

    redis_check = check(master_instance)
    dd_run_check(redis_check)

    for name in REPLICA_METRICS:
        aggregator.assert_metric(name)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
