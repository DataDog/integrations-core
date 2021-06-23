# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket
import time
from concurrent.futures.thread import ThreadPoolExecutor

import mock
import psycopg2
import pytest
from semver import VersionInfo

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.serialization import json
from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.statement_samples import DBExplainSetupState, PostgresStatementSamples
from datadog_checks.postgres.statements import PG_STAT_STATEMENTS_METRICS_COLUMNS
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

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]

SAMPLE_QUERIES = [
    # (username, password, dbname, query, arg)
    ("bob", "bob", "datadog_test", "SELECT city FROM persons WHERE city = %s", "hello"),
    (
        "bob",
        "bob",
        "datadog_test",
        "SELECT hello_how_is_it_going_this_is_a_very_long_table_alias_name.personid, "
        "hello_how_is_it_going_this_is_a_very_long_table_alias_name.lastname "
        "FROM persons hello_how_is_it_going_this_is_a_very_long_table_alias_name JOIN persons B "
        "ON hello_how_is_it_going_this_is_a_very_long_table_alias_name.personid = B.personid WHERE B.city = %s",
        "hello",
    ),
    ("dd_admin", "dd_admin", "dogs", "SELECT * FROM breed WHERE name = %s", "Labrador"),
]


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    PostgresStatementSamples.executor.shutdown(wait=True)
    PostgresStatementSamples.executor = ThreadPoolExecutor()


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
    aggregator.assert_metric('postgresql.db.count', value=4, count=1)


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


@pytest.mark.parametrize("dbstrict", [True, False])
@pytest.mark.parametrize("pg_stat_statements_view", ["pg_stat_statements", "datadog.pg_stat_statements()"])
def test_statement_metrics(aggregator, integration_check, dbm_instance, dbstrict, pg_stat_statements_view):
    dbm_instance['dbstrict'] = dbstrict
    dbm_instance['pg_stat_statements_view'] = pg_stat_statements_view
    # don't need samples for this test
    dbm_instance['statement_samples'] = {'enabled': False}
    connections = {}

    def _run_queries():
        for user, password, dbname, query, arg in SAMPLE_QUERIES:
            if dbname not in connections:
                connections[dbname] = psycopg2.connect(host=HOST, dbname=dbname, user=user, password=password)
            connections[dbname].cursor().execute(query, (arg,))

    check = integration_check(dbm_instance)
    check._connect()

    _run_queries()
    check.check(dbm_instance)
    _run_queries()
    check.check(dbm_instance)

    def _should_catch_query(dbname):
        # we can always catch it if the query originals in the same DB
        # when dbstrict=True we expect to only capture those queries for the initial database to which the
        # agent is connecting
        if POSTGRES_VERSION.split('.')[0] == "9" and pg_stat_statements_view == "pg_stat_statements":
            # cannot catch any queries from other users
            # only can see own queries
            return False
        if dbstrict and dbname != dbm_instance['dbname']:
            return False
        return True

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 1
    event = events[0]

    assert event['host'] == 'stubbed.hostname'
    assert event['timestamp'] > 0
    assert event['min_collection_interval'] == dbm_instance['min_collection_interval']
    expected_dbm_metrics_tags = {'foo:bar', 'server:{}'.format(HOST), 'port:{}'.format(PORT)}
    assert set(event['tags']) == expected_dbm_metrics_tags
    obfuscated_param = '?' if POSTGRES_VERSION.split('.')[0] == "9" else '$1'

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")

    for username, _, dbname, query, _ in SAMPLE_QUERIES:
        expected_query = query % obfuscated_param
        query_signature = compute_sql_signature(expected_query)
        matching_rows = [r for r in event['postgres_rows'] if r['query_signature'] == query_signature]
        if not _should_catch_query(dbname):
            assert len(matching_rows) == 0
            continue

        # metrics
        assert len(matching_rows) == 1
        row = matching_rows[0]
        assert row['calls'] == 1
        assert row['datname'] == dbname
        assert row['rolname'] == username
        assert row['query'] == expected_query[0:200], "query should be truncated when sending to metrics"
        available_columns = set(row.keys())
        metric_columns = available_columns & PG_STAT_STATEMENTS_METRICS_COLUMNS
        for col in metric_columns:
            assert type(row[col]) in (float, int)

        # full query text
        fqt_events = [e for e in dbm_samples if e.get('dbm_type') == 'fqt']
        assert len(fqt_events) > 0
        matching = [e for e in fqt_events if e['db']['query_signature'] == query_signature]
        assert len(matching) == 1
        fqt_event = matching[0]
        assert fqt_event['ddsource'] == "postgres"
        assert fqt_event['db']['statement'] == expected_query
        assert fqt_event['postgres']['datname'] == dbname
        assert fqt_event['postgres']['rolname'] == username
        assert fqt_event['timestamp'] > 0
        assert fqt_event['host'] == 'stubbed.hostname'
        assert set(fqt_event['ddtags'].split(',')) == expected_dbm_metrics_tags | {
            "db:" + fqt_event['postgres']['datname'],
            "rolname:" + fqt_event['postgres']['rolname'],
        }

    for conn in connections.values():
        conn.close()


def test_statement_metrics_with_duplicates(aggregator, integration_check, pg_instance, datadog_agent):
    pg_instance['deep_database_monitoring'] = True

    # The query signature matches the normalized query returned by the mock agent and would need to be
    # updated if the normalized query is updated
    query = 'select * from pg_stat_activity where application_name = ANY(%s);'
    query_signature = 'a478c1e7aaac3ff2'
    normalized_query = 'select * from pg_stat_activity where application_name = ANY(array [ ? ])'

    def obfuscate_sql(query):
        if query.startswith('select * from pg_stat_activity where application_name'):
            return normalized_query
        return query

    check = integration_check(pg_instance)
    check._connect()
    cursor = check.db.cursor()

    # Execute the query once to begin tracking it. Execute again between checks to track the difference.
    # This should result in a single metric for that query_signature having a value of 2
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = obfuscate_sql
        cursor.execute(query, (['app1', 'app2'],))
        cursor.execute(query, (['app1', 'app2', 'app3'],))
        check.check(pg_instance)
        cursor.execute(query, (['app1', 'app2'],))
        cursor.execute(query, (['app1', 'app2', 'app3'],))
        check.check(pg_instance)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 1
    event = events[0]

    matching = [e for e in event['postgres_rows'] if e['query_signature'] == query_signature]
    assert len(matching) == 1
    row = matching[0]
    assert row['calls'] == 2


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


@pytest.mark.parametrize(
    "dbname,expected_explain_setup_state",
    [
        ("datadog_test", DBExplainSetupState.ok),
        ("dogs", DBExplainSetupState.ok),
        ("dogs_noschema", DBExplainSetupState.invalid_schema),
        ("dogs_nofunc", DBExplainSetupState.failed_function),
    ],
)
def test_get_db_explain_setup_state(integration_check, dbm_instance, dbname, expected_explain_setup_state):
    check = integration_check(dbm_instance)
    check._connect()
    assert check.statement_samples._get_db_explain_setup_state(dbname) == expected_explain_setup_state


@pytest.mark.parametrize("pg_stat_activity_view", ["pg_stat_activity", "datadog.pg_stat_activity()"])
@pytest.mark.parametrize(
    "user,password,dbname,query,arg,expected_error_tag",
    [
        ("bob", "bob", "datadog_test", "SELECT city FROM persons WHERE city = %s", "hello", None),
        ("dd_admin", "dd_admin", "dogs", "SELECT * FROM breed WHERE name = %s", "Labrador", None),
        (
            "dd_admin",
            "dd_admin",
            "dogs_noschema",
            "SELECT * FROM kennel WHERE id = %s",
            123,
            "error:explain-{}".format(DBExplainSetupState.invalid_schema),
        ),
        (
            "dd_admin",
            "dd_admin",
            "dogs_nofunc",
            "SELECT * FROM kennel WHERE id = %s",
            123,
            "error:explain-{}".format(DBExplainSetupState.failed_function),
        ),
    ],
)
def test_statement_samples_collect(
    aggregator,
    integration_check,
    dbm_instance,
    pg_stat_activity_view,
    user,
    password,
    dbname,
    query,
    arg,
    expected_error_tag,
):
    dbm_instance['pg_stat_activity_view'] = pg_stat_activity_view
    check = integration_check(dbm_instance)
    check._connect()

    tags = dbm_instance['tags'] + [
        'server:{}'.format(HOST),
        'port:{}'.format(PORT),
        'db:{}'.format(dbname),
    ]

    conn = psycopg2.connect(host=HOST, dbname=dbname, user=user, password=password)
    # we are able to see the full query (including the raw parameters) in pg_stat_activity because psycopg2 uses
    # the simple query protocol, sending the whole query as a plain string to postgres.
    # if a client is using the extended query protocol with prepare then the query would appear as
    # leave connection open until after the check has run to ensure we're able to see the query in
    # pg_stat_activity
    try:
        conn.cursor().execute(query, (arg,))
        check.check(dbm_instance)
        dbm_samples = aggregator.get_event_platform_events("dbm-samples")

        expected_query = query % ('\'' + arg + '\'' if isinstance(arg, str) else arg)
        matching = [e for e in dbm_samples if e['db']['statement'] == expected_query]

        if POSTGRES_VERSION.split('.')[0] == "9" and pg_stat_activity_view == "pg_stat_activity":
            # pg_monitor role exists only in version 10+
            assert len(matching) == 0, "did not expect to catch any events"
            return

        assert len(matching) == 1, "missing captured event"
        event = matching[0]

        if expected_error_tag:
            assert event['db']['plan']['definition'] is None, "did not expect to collect an execution plan"
            aggregator.assert_metric("dd.postgres.statement_samples.error", tags=tags + [expected_error_tag])
        else:
            assert set(event['ddtags'].split(',')) == set(tags)
            assert event['db']['plan']['definition'] is not None, "missing execution plan"
            assert 'Plan' in json.loads(event['db']['plan']['definition']), "invalid json execution plan"
            # we expect to get a duration because the connections are in "idle" state
            assert event['duration']

    finally:
        conn.close()


@pytest.mark.parametrize("dbstrict", [True, False])
def test_statement_samples_dbstrict(aggregator, integration_check, dbm_instance, dbstrict):
    dbm_instance["dbstrict"] = dbstrict
    check = integration_check(dbm_instance)
    check._connect()

    connections = []
    for user, password, dbname, query, arg in SAMPLE_QUERIES:
        conn = psycopg2.connect(host=HOST, dbname=dbname, user=user, password=password)
        conn.cursor().execute(query, (arg,))
        connections.append(conn)

    check.check(dbm_instance)
    dbm_samples = aggregator.get_event_platform_events("dbm-samples")

    for _, _, dbname, query, arg in SAMPLE_QUERIES:
        expected_query = query % ('\'' + arg + '\'' if isinstance(arg, str) else arg)
        matching = [e for e in dbm_samples if e['db']['statement'] == expected_query]
        if not dbstrict or dbname == dbm_instance['dbname']:
            # when dbstrict=True we expect to only capture those queries for the initial database to which the
            # agent is connecting
            assert len(matching) == 1, "missing captured event"
            event = matching[0]
            assert event["db"]["instance"] == dbname
        else:
            assert len(matching) == 0, "did not expect to capture an event"

    for conn in connections:
        conn.close()


def test_statement_samples_rate_limits(aggregator, integration_check, dbm_instance, bob_conn):
    dbm_instance['statement_samples']['run_sync'] = False
    # one collection every two seconds
    dbm_instance['statement_samples']['collections_per_second'] = 0.5
    check = integration_check(dbm_instance)
    check._connect()
    query = "SELECT city FROM persons WHERE city = 'hello'"
    # leave bob's connection open until after the check has run to ensure we're able to see the query in
    # pg_stat_activity
    cursor = bob_conn.cursor()
    for _ in range(5):
        cursor.execute(query)
        check.check(dbm_instance)
        time.sleep(1)
    cursor.close()

    matching = [e for e in aggregator.get_event_platform_events("dbm-samples") if e['db']['statement'] == query]
    assert len(matching) == 1, "should have collected exactly one event due to sample rate limit"

    metrics = aggregator.metrics("dd.postgres.collect_statement_samples.time")
    assert 2 < len(metrics) < 6


def test_statement_samples_collection_loop_inactive_stop(aggregator, integration_check, dbm_instance):
    dbm_instance['statement_samples']['run_sync'] = False
    check = integration_check(dbm_instance)
    check._connect()
    check.check(dbm_instance)
    # make sure there were no unhandled exceptions
    check.statement_samples._collection_loop_future.result()
    aggregator.assert_metric("dd.postgres.statement_samples.collection_loop_inactive_stop")


def test_statement_samples_collection_loop_cancel(aggregator, integration_check, dbm_instance):
    dbm_instance['statement_samples']['run_sync'] = False
    check = integration_check(dbm_instance)
    check._connect()
    check.check(dbm_instance)
    check.cancel()
    # wait for it to stop and make sure it doesn't throw any exceptions
    check.statement_samples._collection_loop_future.result()
    assert not check.statement_samples._collection_loop_future.running(), "thread should be stopped"
    # if the thread doesn't start until after the cancel signal is set then the db connection will never
    # be created in the first place
    assert check.statement_samples._db_pool.get(dbm_instance['dbname']) is None, "db connection should be gone"
    aggregator.assert_metric("dd.postgres.statement_samples.collection_loop_cancel")


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
