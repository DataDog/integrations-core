# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import psycopg2
import pytest
import socket

from datadog_checks.postgres import PostgreSql

from .common import DB_NAME, HOST, PORT, POSTGRES_VERSION, check_bgw_metrics, check_common_metrics
from .utils import requires_over_10

CONNECTION_METRICS = ['postgresql.max_connections', 'postgresql.percent_usage_connections']

ACTIVITY_METRICS = [
    'postgresql.transactions.open',
    'postgresql.transactions.idle_in_transaction',
    'postgresql.active_queries',
    'postgresql.waiting_queries',
]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_common_metrics(aggregator, integration_check, pg_instance):
    integration_check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT)]
    check_bgw_metrics(aggregator, expected_tags)

    expected_tags += ['db:{}'.format(DB_NAME)]
    check_common_metrics(aggregator, expected_tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_common_metrics_without_size(aggregator, integration_check, pg_instance):
    pg_instance['collect_database_size_metrics'] = False
    integration_check.check(pg_instance)
    assert 'postgresql.database_size' not in aggregator.metric_names


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_can_connect_service_check(aggregator, integration_check, pg_instance):
    expected_tags = pg_instance['tags'] + [
        'host:{}'.format(HOST),
        'server:{}'.format(HOST),
        'port:{}'.format(PORT),
        'db:{}'.format(DB_NAME),
    ]
    integration_check.check(pg_instance)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.OK, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_schema_metrics(aggregator, integration_check, pg_instance):
    pg_instance['table_count_limit'] = 1
    integration_check.check(pg_instance)

    expected_tags = pg_instance['tags'] + [
        'db:{}'.format(DB_NAME),
        'server:{}'.format(HOST),
        'port:{}'.format(PORT),
        'schema:public',
    ]
    aggregator.assert_metric('postgresql.table.count', value=1, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.db.count', value=2, count=1)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connections_metrics(aggregator, integration_check, pg_instance):
    integration_check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT)]
    for name in CONNECTION_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)
    expected_tags += ['db:datadog_test']
    aggregator.assert_metric('postgresql.connections', count=1, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_locks_metrics(aggregator, integration_check, pg_instance):
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres") as conn:
        with conn.cursor() as cur:
            cur.execute('LOCK persons')
            integration_check.check(pg_instance)

    expected_tags = pg_instance['tags'] + [
        'server:{}'.format(HOST),
        'port:{}'.format(PORT),
        'db:datadog_test',
        'lock_mode:AccessExclusiveLock',
        'table:persons',
        'schema:public',
    ]
    aggregator.assert_metric('postgresql.locks', count=1, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_activity_metrics(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    integration_check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT), 'db:datadog_test']
    for name in ACTIVITY_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)


@requires_over_10
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_wrong_version(aggregator, integration_check, pg_instance):
    # Enforce to cache wrong version
    db_key = ('localhost', 5432, 'datadog_test')
    integration_check.version = [9, 6, 0]

    integration_check.check(pg_instance)
    assert_state_clean(integration_check)

    integration_check.check(pg_instance)
    assert integration_check.version[0] == int(POSTGRES_VERSION)
    assert_state_set(integration_check)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_state_clears_on_connection_error(integration_check, pg_instance):
    db_key = ('localhost', 5432, 'datadog_test')

    integration_check.check(pg_instance)
    assert_state_set(integration_check, db_key)

    def throw_exception_first_time(*args, **kwargs):
        throw_exception_first_time.counter += 1
        if throw_exception_first_time.counter > 1:
            pass  # avoid throwing exception again
        else:
            raise socket.error

    throw_exception_first_time.counter = 0

    with mock.patch('datadog_checks.postgres.PostgreSql._collect_stats', side_effect=throw_exception_first_time):
        integration_check.check(pg_instance)
    assert_state_clean(integration_check, db_key)


def assert_state_clean(check):
    assert check.version is None
    assert check.instance_metrics is None
    assert check.bgw_metrics is None
    assert check.archiver_metrics is None
    assert check.db_bgw_metrics == []
    assert check.db_archiver_metrics == []
    assert check.replication_metrics is None
    assert check.activity_metrics is None


def assert_state_set(check,):
    assert check.versions
    assert check.instance_metrics
    assert check.bgw_metrics
    if POSTGRES_VERSION != '9.3':
        assert check.archiver_metrics
        assert check.db_archiver_metrics != []
    assert check.db_bgw_metrics != []
    assert check.replication_metrics
