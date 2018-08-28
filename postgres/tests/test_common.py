# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
import os

from datadog_checks.postgres import PostgreSql

from .common import HOST, PORT, DB_NAME


COMMON_METRICS = [
    'postgresql.connections',
    'postgresql.commits',
    'postgresql.rollbacks',
    'postgresql.disk_read',
    'postgresql.buffer_hit',
    'postgresql.rows_returned',
    'postgresql.rows_fetched',
    'postgresql.rows_inserted',
    'postgresql.rows_updated',
    'postgresql.rows_deleted',
    'postgresql.database_size',
    'postgresql.deadlocks',
    'postgresql.temp_bytes',
    'postgresql.temp_files',
]

COMMON_BGW_METRICS = [
    'postgresql.bgwriter.checkpoints_timed',
    'postgresql.bgwriter.checkpoints_requested',
    'postgresql.bgwriter.buffers_checkpoint',
    'postgresql.bgwriter.buffers_clean',
    'postgresql.bgwriter.maxwritten_clean',
    'postgresql.bgwriter.buffers_backend',
    'postgresql.bgwriter.buffers_alloc',
    'postgresql.bgwriter.buffers_backend_fsync',
    'postgresql.bgwriter.write_time',
    'postgresql.bgwriter.sync_time',
]

COMMON_BGW_METRICS_PG_ABOVE_94 = [
    'postgresql.archiver.archived_count',
    'postgresql.archiver.failed_count',
]

CONNECTION_METRICS = [
    'postgresql.max_connections',
    'postgresql.percent_usage_connections',
]

ACTIVITY_METRICS = [
    'postgresql.transactions.open',
    'postgresql.transactions.idle_in_transaction',
]


def check_common_metrics(aggregator, expected_tags):
    for name in COMMON_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)


def check_bgw_metrics(aggregator, expected_tags):
    for name in COMMON_BGW_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)

    if float(os.environ['POSTGRES_VERSION']) >= 9.4:
        for name in COMMON_BGW_METRICS_PG_ABOVE_94:
            aggregator.assert_metric(name, count=1, tags=expected_tags)


@pytest.mark.integration
def test_common_metrics(aggregator, check, postgres_standalone, pg_instance):
    expected_tags = pg_instance['tags'] + ['db:{}'.format(DB_NAME)]

    check.check(pg_instance)
    check_common_metrics(aggregator, expected_tags)
    check_bgw_metrics(aggregator, pg_instance['tags'])


@pytest.mark.integration
def test_common_metrics_without_size(aggregator, check, postgres_standalone, pg_instance):
    pg_instance['collect_database_size_metrics'] = False
    check.check(pg_instance)
    assert 'postgresql.database_size' not in aggregator.metric_names


@pytest.mark.integration
def test_can_connect_service_check(aggregator, check, postgres_standalone, pg_instance):
    expected_tags = pg_instance['tags'] + [
        'host:{}'.format(HOST),
        'port:{}'.format(PORT),
        'db:{}'.format(DB_NAME),
    ]
    check.check(pg_instance)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.OK, tags=expected_tags)


@pytest.mark.integration
def test_schema_metrics(aggregator, check, postgres_standalone, pg_instance):
    check.check(pg_instance)

    aggregator.assert_metric('postgresql.table.count', value=1, count=1,
                             tags=pg_instance['tags']+['schema:public'])
    aggregator.assert_metric('postgresql.db.count', value=2, count=1)


@pytest.mark.integration
def test_connections_metrics(aggregator, check, postgres_standalone, pg_instance):
    check.check(pg_instance)

    for name in CONNECTION_METRICS:
        aggregator.assert_metric(name, count=1, tags=pg_instance['tags'])
    aggregator.assert_metric('postgresql.connections', count=1, tags=pg_instance['tags']+['db:datadog_test'])


@pytest.mark.integration
def test_activity_metrics(aggregator, check, postgres_standalone, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    check.check(pg_instance)

    for name in ACTIVITY_METRICS:
        aggregator.assert_metric(name, count=1, tags=pg_instance['tags'] + ['db:datadog_test'])
