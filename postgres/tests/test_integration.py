# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket

import mock
import psycopg2
import pytest
from semver import VersionInfo

from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.util import PartialFormatter, fmt

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
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT)]
    check_bgw_metrics(aggregator, expected_tags)

    expected_tags += ['db:{}'.format(DB_NAME)]
    check_common_metrics(aggregator, expected_tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_common_metrics_without_size(aggregator, integration_check, pg_instance):
    pg_instance['collect_database_size_metrics'] = False
    check = integration_check(pg_instance)
    check.check(pg_instance)
    assert 'postgresql.database_size' not in aggregator.metric_names


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_unsupported_replication(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)

    unpatched_fmt = PartialFormatter()

    called = []

    def format_with_error(value, **kwargs):
        if 'pg_is_in_recovery' in value:
            called.append(True)
            raise psycopg2.errors.FeatureNotSupported("Not available")
        return unpatched_fmt.format(value, **kwargs)

    # This simulate an error in the fmt function, as it's a bit hard to mock psycopg
    with mock.patch.object(fmt, 'format', passthrough=True) as mock_fmt:
        mock_fmt.side_effect = format_with_error
        check.check(pg_instance)

    # Verify our mocking was called
    assert called == [True]

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT)]
    check_bgw_metrics(aggregator, expected_tags)

    expected_tags += ['db:{}'.format(DB_NAME)]
    check_common_metrics(aggregator, expected_tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_can_connect_service_check(aggregator, integration_check, pg_instance):
    # First: check run with a valid postgres instance
    check = integration_check(pg_instance)
    expected_tags = pg_instance['tags'] + [
        'host:{}'.format(HOST),
        'server:{}'.format(HOST),
        'port:{}'.format(PORT),
        'db:{}'.format(DB_NAME),
    ]
    check.check(pg_instance)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.OK, tags=expected_tags)
    aggregator.reset()

    # Second: keep the connection open but an unexpected error happens during check run
    orig_db = check.db
    check.db = mock.MagicMock(spec=('closed', 'status'), closed=False, status=psycopg2.extensions.STATUS_READY)
    with pytest.raises(AttributeError):
        check.check(pg_instance)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.CRITICAL, tags=expected_tags)
    aggregator.reset()

    # Third: connection still open but this time no error
    check.db = orig_db
    check.check(pg_instance)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.OK, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_schema_metrics(aggregator, integration_check, pg_instance):
    pg_instance['table_count_limit'] = 1
    check = integration_check(pg_instance)
    check.check(pg_instance)

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
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT)]
    for name in CONNECTION_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)
    expected_tags += ['db:datadog_test']
    aggregator.assert_metric('postgresql.connections', count=1, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_locks_metrics_no_relations(aggregator, integration_check, pg_instance):
    """
    Since 4.0.0, to prevent tag explosion, lock metrics are not collected anymore unless relations are specified
    """
    check = integration_check(pg_instance)
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        with conn.cursor() as cur:
            cur.execute('LOCK persons')
            check.check(pg_instance)

    aggregator.assert_metric('postgresql.locks', count=0)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_activity_metrics(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT), 'db:datadog_test']
    for name in ACTIVITY_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)


@requires_over_10
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_wrong_version(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    # Enforce to cache wrong version
    check._version = VersionInfo(*[9, 6, 0])

    check.check(pg_instance)
    assert_state_clean(check)

    check.check(pg_instance)
    assert_state_set(check)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_version_metadata(integration_check, pg_instance, datadog_agent):
    check = integration_check(pg_instance)
    check.check_id = 'test:123'
    # Enforce to cache wrong version
    check.check(pg_instance)
    version = POSTGRES_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': version[0],
    }
    if len(version) == 2:
        version_metadata['version.minor'] = version[1]

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(5)  # for raw and patch


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_state_clears_on_connection_error(integration_check, pg_instance):
    check = integration_check(pg_instance)
    check.check(pg_instance)
    assert_state_set(check)

    def throw_exception_first_time(*args, **kwargs):
        throw_exception_first_time.counter += 1
        if throw_exception_first_time.counter > 1:
            pass  # avoid throwing exception again
        else:
            raise socket.error

    throw_exception_first_time.counter = 0

    with mock.patch('datadog_checks.postgres.PostgreSql._collect_stats', side_effect=throw_exception_first_time):
        with pytest.raises(socket.error):
            check.check(pg_instance)
    assert_state_clean(check)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_query_timeout(aggregator, integration_check, pg_instance):
    pg_instance['query_timeout'] = 1000
    check = integration_check(pg_instance)
    check._connect()
    cursor = check.db.cursor()
    with pytest.raises(psycopg2.errors.QueryCanceled):
        cursor.execute("select pg_sleep(2000)")


def assert_state_clean(check):
    assert check.instance_metrics is None
    assert check.bgw_metrics is None
    assert check.archiver_metrics is None
    assert check.replication_metrics is None
    assert check.activity_metrics is None


def assert_state_set(check):
    assert check.instance_metrics
    assert check.bgw_metrics
    if POSTGRES_VERSION != '9.3':
        assert check.archiver_metrics
    assert check.replication_metrics
