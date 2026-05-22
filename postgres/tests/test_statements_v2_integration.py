# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import psycopg
import pytest
from psycopg import ClientCursor

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.postgres.statements import PG_STAT_STATEMENTS_METRICS_COLUMNS

from .common import (
    DB_NAME,
    HOST,
    PASSWORD_ADMIN,
    POSTGRES_VERSION,
    USER_ADMIN,
    _get_expected_tags,
)
from .utils import _get_superconn, requires_over_10, requires_over_13, run_one_check

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]

CLOSE_TO_ZERO_INTERVAL = 0.0000001

SAMPLE_QUERIES = [
    ("bob", "bob", "datadog_test", "SELECT city FROM persons WHERE city = %s", "hello"),
    (USER_ADMIN, PASSWORD_ADMIN, "dogs", "SELECT * FROM breed WHERE name = %s", "Labrador"),
]


@pytest.fixture(autouse=True)
def auto_reset_pg_stat_statements(reset_pg_stat_statements):
    pass


@pytest.fixture
def dbm_instance_v2(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.2
    pg_instance['pg_stat_activity_view'] = "datadog.pg_stat_activity()"
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['collect_settings'] = {'enabled': False}
    pg_instance['collect_column_statistics'] = {'enabled': False}
    pg_instance['collect_schemas'] = {'enabled': False}
    pg_instance['query_metrics'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': CLOSE_TO_ZERO_INTERVAL,
        'use_v2': True,
    }
    return pg_instance


# ---------------------------------------------------------------------------
# End-to-end collection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dbstrict,ignore_databases", [(True, []), (False, ['dogs']), (False, [])])
def test_statement_metrics_v2(
    aggregator,
    integration_check,
    dbm_instance_v2,
    dbstrict,
    ignore_databases,
    datadog_agent,
):
    dbm_instance_v2['dbstrict'] = dbstrict
    dbm_instance_v2['ignore_databases'] = ignore_databases
    connections = {}

    def _run_queries():
        for user, password, dbname, query, arg in SAMPLE_QUERIES:
            if dbname not in connections:
                connections[dbname] = psycopg.connect(
                    host=HOST, dbname=dbname, user=user, password=password, autocommit=True, cursor_factory=ClientCursor
                )
            connections[dbname].cursor().execute(query, (arg,))

    check = integration_check(dbm_instance_v2)
    check._connect()

    # First check: seeds DeltaDetector with initial snapshot (no derivatives)
    _run_queries()
    run_one_check(check, cancel=False)

    # Second check: queries run again, DeltaDetector produces derivatives
    _run_queries()
    run_one_check(check, cancel=False)

    def _should_catch_query(dbname):
        if POSTGRES_VERSION.split('.')[0] == "9":
            return False
        if dbstrict and dbname != dbm_instance_v2['dbname'] or dbname in ignore_databases:
            return False
        return True

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) >= 1
    event = events[-1]

    assert event['host'] == 'stubbed.hostname'
    assert event['timestamp'] > 0
    assert event['ddagentversion'] == datadog_agent.get_version()
    assert event['min_collection_interval'] == dbm_instance_v2['query_metrics']['collection_interval']
    expected_dbm_metrics_tags = set(_get_expected_tags(check, dbm_instance_v2, with_host=False))
    assert set(event['tags']) == expected_dbm_metrics_tags
    obfuscated_param = '?' if POSTGRES_VERSION.split('.')[0] == "9" else '$1'

    assert len(aggregator.metrics("postgresql.pg_stat_statements.max")) != 0
    assert len(aggregator.metrics("postgresql.pg_stat_statements.count")) != 0

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")

    for username, _, dbname, query, _ in SAMPLE_QUERIES:
        expected_query = query % obfuscated_param
        query_signature = compute_sql_signature(expected_query)
        matching_rows = [r for r in event['postgres_rows'] if r['query_signature'] == query_signature]
        if not _should_catch_query(dbname):
            assert len(matching_rows) == 0, f"Should not catch query from {dbname}"
            continue
        assert len(matching_rows) == 1, f"Expected exactly 1 row for {query_signature}"
        row = matching_rows[0]
        assert row['calls'] == 1
        assert row['datname'] == dbname
        assert row['rolname'] == username
        assert row['query'] == expected_query
        available_columns = set(row.keys())
        metric_columns = available_columns & PG_STAT_STATEMENTS_METRICS_COLUMNS
        for col in metric_columns:
            assert type(row[col]) in (float, int)

        # FQT events
        fqt_events = [e for e in dbm_samples if e.get('dbm_type') == 'fqt']
        assert len(fqt_events) > 0
        matching = [e for e in fqt_events if e['db']['query_signature'] == query_signature]
        assert len(matching) >= 1
        fqt_event = matching[0]
        assert fqt_event['ddsource'] == "postgres"
        assert fqt_event['db']['statement'] == expected_query
        assert fqt_event['postgres']['datname'] == dbname
        assert fqt_event['postgres']['rolname'] == username

    for conn in connections.values():
        conn.close()


# ---------------------------------------------------------------------------
# Cold start: first cycle returns no derivatives
# ---------------------------------------------------------------------------


def test_cold_start_v2(aggregator, integration_check, dbm_instance_v2):
    conn = psycopg.connect(
        host=HOST, dbname=DB_NAME, user="bob", password="bob", autocommit=True, cursor_factory=ClientCursor
    )
    conn.cursor().execute("SELECT city FROM persons WHERE city = %s", ("hello",))

    check = integration_check(dbm_instance_v2)
    check._connect()
    run_one_check(check, cancel=False)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 0, "First cycle should not emit any metrics (no previous snapshot to diff)"

    conn.cursor().execute("SELECT city FROM persons WHERE city = %s", ("hello",))
    run_one_check(check, cancel=False)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) >= 1, "Second cycle should emit metrics after diffing"

    conn.close()


# ---------------------------------------------------------------------------
# Duplicate pgss rows (different queryids, same query_signature) are merged
# ---------------------------------------------------------------------------


@requires_over_10
def test_statement_metrics_with_duplicates_v2(aggregator, integration_check, dbm_instance_v2, datadog_agent):
    query = 'select * from pg_stat_activity where application_name = ANY(%s);'
    query_signature = 'a478c1e7aaac3ff2'
    normalized_query = 'select * from pg_stat_activity where application_name = ANY(array [ ? ])'

    def obfuscate_sql(query, options=None):
        if 'select * from pg_stat_activity where application_name' in query:
            return normalized_query
        return query

    check = integration_check(dbm_instance_v2)
    check._connect()

    with check.db() as conn:
        with conn.cursor() as cursor:
            with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
                mock_agent.side_effect = obfuscate_sql
                cursor.execute(query, (['app1', 'app2'],))
                cursor.execute(query, (['app1', 'app2', 'app3'],))
                check.check(dbm_instance_v2)

                cursor.execute(query, (['app1', 'app2'],))
                cursor.execute(query, (['app1', 'app2', 'app3'],))
                run_one_check(check)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 1
    event = events[0]

    matching = [e for e in event['postgres_rows'] if e['query_signature'] == query_signature]
    assert len(matching) == 1
    row = matching[0]
    assert row['calls'] == 2


# ---------------------------------------------------------------------------
# Database errors: pgss not created / generic error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "error,metric_columns,expected_error_tag,expected_warnings",
    [
        (
            psycopg.errors.DatabaseError('connection reset'),
            [],
            'error:database-DatabaseError',
            [
                "Unable to collect statement metrics because of an error running queries in database 'datadog_test'. "
                'See https://docs.datadoghq.com/database_monitoring/troubleshooting for help: connection reset\n'
                'dbname=datadog_test host=stubbed.hostname',
            ],
        ),
        (
            None,
            [],
            'error:database-missing_pg_stat_statements_required_columns',
            [
                'Unable to collect statement metrics because required fields are unavailable: calls, dbid, queryid, '
                'userid.\ndbname=datadog_test host=stubbed.hostname',
            ],
        ),
    ],
)
def test_statement_metrics_database_errors_v2(
    aggregator, integration_check, dbm_instance_v2, error, metric_columns, expected_error_tag, expected_warnings
):
    check = integration_check(dbm_instance_v2)

    with mock.patch(
        'datadog_checks.postgres.statements_v2.PostgresStatementMetricsV2._get_pg_stat_statements_columns',
        return_value=metric_columns,
        side_effect=error,
    ):
        run_one_check(check)

    expected_tags = _get_expected_tags(
        check, dbm_instance_v2, with_host=False, with_db=True, agent_hostname='stubbed.hostname'
    ) + [expected_error_tag]

    aggregator.assert_metric(
        'dd.postgres.statement_metrics.error', value=1.0, count=1, tags=expected_tags, hostname='stubbed.hostname'
    )
    assert check.warnings == expected_warnings


def test_statement_metrics_pgss_not_created_v2(aggregator, integration_check, dbm_instance_v2):
    check = integration_check(dbm_instance_v2)

    superconn = _get_superconn(dbm_instance_v2)
    with superconn.cursor() as cur:
        cur.execute("DROP EXTENSION pg_stat_statements CASCADE;")

        run_one_check(check)

        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements SCHEMA public;")

    expected_tags = _get_expected_tags(
        check, dbm_instance_v2, with_host=False, with_db=True, agent_hostname='stubbed.hostname'
    ) + ['error:database-UndefinedTable-pg_stat_statements_not_created']

    aggregator.assert_metric(
        'dd.postgres.statement_metrics.error', value=1.0, count=1, tags=expected_tags, hostname='stubbed.hostname'
    )

    assert check.warnings == [
        'Unable to collect statement metrics because pg_stat_statements is not '
        "created in database 'datadog_test'. See https://docs.datadoghq.com/database_monitoring/"
        'setup_postgres/troubleshooting#pg-stat-statements-not-created'
        ' for more details\ncode=pg-stat-statements-not-created dbname=datadog_test host=stubbed.hostname',
    ]


# ---------------------------------------------------------------------------
# pgss max warning
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pg_stat_statements_max_threshold,expected_warnings",
    [
        (
            9999,
            [
                'pg_stat_statements.max is set to 10000 which is higher than the supported value of 9999. '
                'This can have a negative impact on database and collection of query metrics performance. '
                'Consider lowering the pg_stat_statements.max value to 9999. Alternatively, you may acknowledge '
                'the potential performance impact by increasing the '
                'query_metrics.pg_stat_statements_max_warning_threshold to equal or greater than 9999 to silence '
                'this warning. See https://docs.datadoghq.com/database_monitoring/setup_postgres/troubleshooting#'
                'high-pg-stat-statements-max-configuration for more details\n'
                'code=high-pg-stat-statements-max-configuration dbname=datadog_test host=stubbed.hostname '
                'threshold=9999.0 value=10000',
            ],
        ),
        (10000, []),
    ],
)
def test_pg_stat_statements_max_warning_v2(
    integration_check, dbm_instance_v2, pg_stat_statements_max_threshold, expected_warnings
):
    dbm_instance_v2['query_metrics']['pg_stat_statements_max_warning_threshold'] = pg_stat_statements_max_threshold
    check = integration_check(dbm_instance_v2)
    check._connect()
    run_one_check(check)

    assert check.warnings == expected_warnings


# ---------------------------------------------------------------------------
# pgss dealloc tracking
# ---------------------------------------------------------------------------


@requires_over_10
def test_pg_stat_statements_dealloc_v2(aggregator, integration_check, pg_instance):
    from .common import PORT_REPLICA2, _get_expected_replication_tags

    pg_instance['dbm'] = True
    pg_instance['port'] = PORT_REPLICA2
    pg_instance['min_collection_interval'] = 1
    pg_instance['pg_stat_activity_view'] = "datadog.pg_stat_activity()"
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.2, 'use_v2': True}

    with _get_superconn(pg_instance) as superconn:
        with superconn.cursor() as cur:
            cur.execute("select pg_stat_statements_reset();")

    check = integration_check(pg_instance)
    run_one_check(check)

    expected_tags = _get_expected_replication_tags(check, pg_instance, with_host=False, db=DB_NAME)
    aggregator.assert_metric("postgresql.pg_stat_statements.max", value=100, tags=expected_tags)
    if float(POSTGRES_VERSION) >= 14.0:
        aggregator.assert_metric("postgresql.pg_stat_statements.dealloc", value=0, tags=expected_tags)
    aggregator.assert_metric("postgresql.pg_stat_statements.count", tags=expected_tags)


# ---------------------------------------------------------------------------
# WAL metrics present in V2 output
# ---------------------------------------------------------------------------


@requires_over_13
def test_wal_metrics_v2(aggregator, integration_check, dbm_instance_v2):
    connections = {}

    def _run_queries():
        for user, password, dbname, query, arg in SAMPLE_QUERIES:
            if dbname not in connections:
                connections[dbname] = psycopg.connect(host=HOST, dbname=dbname, user=user, password=password)
            connections[dbname].cursor().execute(query, (arg,))

    check = integration_check(dbm_instance_v2)
    check._connect()

    _run_queries()
    run_one_check(check, cancel=False)
    _run_queries()
    run_one_check(check)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 1, "should capture exactly one metrics payload"
    event = events[0]

    assert all('wal_bytes' in entry for entry in event['postgres_rows'])
    assert all('wal_fpi' in entry for entry in event['postgres_rows'])

    for conn in connections.values():
        conn.close()


# ---------------------------------------------------------------------------
# Internal telemetry gauges are emitted
# ---------------------------------------------------------------------------


def test_internal_telemetry_gauges_v2(aggregator, integration_check, dbm_instance_v2):
    conn = psycopg.connect(
        host=HOST, dbname=DB_NAME, user="bob", password="bob", autocommit=True, cursor_factory=ClientCursor
    )

    check = integration_check(dbm_instance_v2)
    check._connect()

    conn.cursor().execute("SELECT city FROM persons WHERE city = %s", ("hello",))
    run_one_check(check, cancel=False)

    conn.cursor().execute("SELECT city FROM persons WHERE city = %s", ("hello",))
    run_one_check(check, cancel=False)

    debug_tags = check._get_debug_tags()
    expected_tags = _get_expected_tags(check, dbm_instance_v2, with_host=False, with_db=True)

    aggregator.assert_metric(
        "dd.postgres.statement_metrics.delta.derivative_rows",
        tags=expected_tags + debug_tags,
        hostname='stubbed.hostname',
    )
    aggregator.assert_metric(
        "dd.postgres.statement_metrics.delta.changed_queryids",
        tags=expected_tags + debug_tags,
        hostname='stubbed.hostname',
    )
    aggregator.assert_metric(
        "dd.postgres.statement_metrics.lookup.hits",
        tags=expected_tags + debug_tags,
        hostname='stubbed.hostname',
    )
    aggregator.assert_metric(
        "dd.postgres.statement_metrics.lookup.misses",
        tags=expected_tags + debug_tags,
        hostname='stubbed.hostname',
    )

    conn.close()
