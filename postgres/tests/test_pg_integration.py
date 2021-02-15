# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import socket
import time

import mock
import psycopg2
import pytest
from semver import VersionInfo

from datadog_checks.base.utils.db.statement_samples import statement_samples_client
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

STATEMENT_METRICS = [
    'postgresql.queries.count',
    'postgresql.queries.time',
    'postgresql.queries.rows',
    'postgresql.queries.shared_blks_hit',
    'postgresql.queries.shared_blks_read',
    'postgresql.queries.shared_blks_dirtied',
    'postgresql.queries.shared_blks_written',
    'postgresql.queries.local_blks_hit',
    'postgresql.queries.local_blks_read',
    'postgresql.queries.local_blks_dirtied',
    'postgresql.queries.local_blks_written',
    'postgresql.queries.temp_blks_read',
    'postgresql.queries.temp_blks_written',
]

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_common_metrics(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT)]
    check_bgw_metrics(aggregator, expected_tags)

    expected_tags += ['db:{}'.format(DB_NAME)]
    check_common_metrics(aggregator, expected_tags=expected_tags)


def test_common_metrics_without_size(aggregator, integration_check, pg_instance):
    pg_instance['collect_database_size_metrics'] = False
    check = integration_check(pg_instance)
    check.check(pg_instance)
    assert 'postgresql.database_size' not in aggregator.metric_names


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


def test_connections_metrics(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT)]
    for name in CONNECTION_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)
    expected_tags += ['db:datadog_test']
    aggregator.assert_metric('postgresql.connections', count=1, tags=expected_tags)


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


def test_activity_metrics(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT), 'db:datadog_test']
    for name in ACTIVITY_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)


@requires_over_10
def test_wrong_version(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    # Enforce to cache wrong version
    check._version = VersionInfo(*[9, 6, 0])

    check.check(pg_instance)
    assert_state_clean(check)

    check.check(pg_instance)
    assert_state_set(check)


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


def test_query_timeout(aggregator, integration_check, pg_instance):
    pg_instance['query_timeout'] = 1000
    check = integration_check(pg_instance)
    check._connect()
    cursor = check.db.cursor()
    with pytest.raises(psycopg2.errors.QueryCanceled):
        cursor.execute("select pg_sleep(2000)")


def test_config_tags_is_unchanged_between_checks(integration_check, pg_instance):
    pg_instance['tag_replication_role'] = True
    check = integration_check(pg_instance)

    expected_tags = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT), 'db:datadog_test']

    for _ in range(3):
        check.check(pg_instance)
        assert check._config.tags == expected_tags


def test_statement_metrics(aggregator, integration_check, pg_instance):
    pg_instance['deep_database_monitoring'] = True
    # The query signature should match the query and consistency of this tag has product impact. Do not change
    # the query signature for this test unless you know what you're doing.
    QUERY = 'select * from pg_stat_activity'
    QUERY_SIGNATURE = '7cde606dbf8eaa17'

    check = integration_check(pg_instance)
    check._connect()
    cursor = check.db.cursor()

    # Execute the query once to begin tracking it. Execute again between checks to track the difference.
    # This should result in a count of 1
    cursor.execute(QUERY)
    check.check(pg_instance)
    cursor.execute(QUERY)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + [
        'server:{}'.format(HOST),
        'port:{}'.format(PORT),
        'db:datadog_test',
        'user:datadog',
        'query:{}'.format(QUERY),
        'query_signature:{}'.format(QUERY_SIGNATURE),
        'resource_hash:{}'.format(QUERY_SIGNATURE),
    ]

    for name in STATEMENT_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)


@pytest.fixture
def bob_conn():
    conn = psycopg2.connect(host=HOST, dbname=DB_NAME, user="bob", password="bob")
    yield conn
    conn.close()


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['deep_database_monitoring'] = True
    pg_instance['min_collection_interval'] = 1
    pg_instance['pg_stat_activity_view'] = "datadog.pg_stat_activity()"
    pg_instance['statement_samples'] = {'enabled': True, 'run_sync': True, 'collections_per_second': 1}
    return pg_instance


@pytest.mark.parametrize("pg_stat_activity_view", ["pg_stat_activity", "datadog.pg_stat_activity()"])
def test_statement_samples_collect(integration_check, dbm_instance, bob_conn, pg_stat_activity_view):
    dbm_instance['pg_stat_activity_view'] = pg_stat_activity_view
    check = integration_check(dbm_instance)
    check._connect()
    # clear out any samples kept from previous runs
    statement_samples_client._events = []
    query = "SELECT city FROM persons WHERE city = %s"
    # we are able to see the full query (including the raw parameters) in pg_stat_activity because psycopg2 uses
    # the simple query protocol, sending the whole query as a plain string to postgres.
    # if a client is using the extended query protocol with prepare then the query would appear as
    expected_query = query % "'hello'"
    # leave bob's connection open until after the check has run to ensure we're able to see the query in
    # pg_stat_activity
    cursor = bob_conn.cursor()
    cursor.execute(query, ("hello",))
    check.check(dbm_instance)
    matching = [e for e in statement_samples_client._events if e['db']['statement'] == expected_query]
    if POSTGRES_VERSION.split('.')[0] == "9" and pg_stat_activity_view == "pg_stat_activity":
        # pg_monitor role exists only in version 10+
        assert len(matching) == 0, "did not expect to catch any events"
        return
    assert len(matching) > 0, "should have collected an event"
    event = matching[0]
    assert event['db']['plan']['definition'] is not None, "missing execution plan"
    assert 'Plan' in json.loads(event['db']['plan']['definition']), "invalid json execution plan"
    # we're expected to get a duration because the connection is in "idle" state
    assert event['duration']
    cursor.close()


def test_statement_samples_rate_limits(aggregator, integration_check, dbm_instance, bob_conn):
    dbm_instance['statement_samples']['run_sync'] = False
    # one collection every two seconds
    dbm_instance['statement_samples']['collections_per_second'] = 0.5
    check = integration_check(dbm_instance)
    check._connect()
    # clear out any samples kept from previous runs
    statement_samples_client._events = []
    query = "SELECT city FROM persons WHERE city = 'hello'"
    # leave bob's connection open until after the check has run to ensure we're able to see the query in
    # pg_stat_activity
    cursor = bob_conn.cursor()
    for _ in range(5):
        cursor.execute(query)
        check.check(dbm_instance)
        time.sleep(1)
    cursor.close()

    matching = [e for e in statement_samples_client._events if e['db']['statement'] == query]
    assert len(matching) == 1, "should have collected exactly one event due to sample rate limit"

    metrics = aggregator.metrics("dd.postgres.collect_statement_samples.time")
    assert 2 < len(metrics) < 6


def test_statement_samples_collection_loop_inactive_stop(aggregator, integration_check, dbm_instance):
    dbm_instance['statement_samples']['run_sync'] = False
    check = integration_check(dbm_instance)
    check._connect()
    check.check(dbm_instance)
    while check.statement_samples._collection_loop_future.running():
        time.sleep(0.1)
    # make sure there were no unhandled exceptions
    check.statement_samples._collection_loop_future.result()
    aggregator.assert_metric("dd.postgres.statement_samples.collection_loop_inactive_stop")


def test_statement_samples_invalid_activity_view(aggregator, integration_check, dbm_instance):
    dbm_instance['pg_stat_activity_view'] = "wrong_view"

    # run synchronously, so we expect it to blow up right away
    dbm_instance['statement_samples'] = {'enabled': True, 'run_sync': True}
    check = integration_check(dbm_instance)
    check._connect()
    with pytest.raises(psycopg2.errors.UndefinedTable):
        check.check(dbm_instance)

    # run asynchronously, loop will crash the first time it tries to run as the table doesn't exist
    dbm_instance['statement_samples']['run_sync'] = False
    check = integration_check(dbm_instance)
    check._connect()
    check.check(dbm_instance)
    while check.statement_samples._collection_loop_future.running():
        time.sleep(0.1)
    # make sure there were no unhandled exceptions
    check.statement_samples._collection_loop_future.result()
    aggregator.assert_metric_has_tag_prefix("dd.postgres.statement_samples.error", "error:database-")


@pytest.mark.parametrize(
    "number_key",
    [
        "explained_statements_cache_maxsize",
        "explained_statements_per_hour_per_query",
        "seen_samples_cache_maxsize",
        "collections_per_second",
    ],
)
def test_statement_samples_config_invalid_number(integration_check, pg_instance, number_key):
    pg_instance['statement_samples'] = {
        number_key: "not-a-number",
    }
    with pytest.raises(ValueError):
        integration_check(pg_instance)


def assert_state_clean(check):
    assert check.metrics_cache.instance_metrics is None
    assert check.metrics_cache.bgw_metrics is None
    assert check.metrics_cache.archiver_metrics is None
    assert check.metrics_cache.replication_metrics is None
    assert check.metrics_cache.activity_metrics is None
    assert check._is_aurora is None


def assert_state_set(check):
    assert check.metrics_cache.instance_metrics
    assert check.metrics_cache.bgw_metrics
    if POSTGRES_VERSION != '9.3':
        assert check.metrics_cache.archiver_metrics
    assert check.metrics_cache.replication_metrics
    assert check._is_aurora is False
