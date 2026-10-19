# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import psycopg
import pytest
from psycopg import ClientCursor

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.postgres.statements import PG_STAT_STATEMENTS_METRICS_COLUMNS
from datadog_checks.postgres.statements_v2 import PostgresStatementMetricsV2, pgss_key
from datadog_checks.postgres.util import DDIGNORE_COMMENT

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
        'incremental_query_metrics': True,
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

    # First check: seeds the counter baseline with an initial snapshot (no derivatives)
    _run_queries()
    run_one_check(check, cancel=False)

    # Second check: queries run again, so diffing against the baseline produces derivatives
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
                check.run()

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


@requires_over_10
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
    pg_instance['query_metrics'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.2,
        'incremental_query_metrics': True,
    }

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


@requires_over_10
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
    for stat in ("hits", "misses", "fetched", "ignored", "failed", "dropped"):
        aggregator.assert_metric(
            "dd.postgres.statement_metrics.lookup.{}".format(stat),
            tags=expected_tags + debug_tags,
            hostname='stubbed.hostname',
        )

    conn.close()


# ---------------------------------------------------------------------------
# pgss not loaded (ObjectNotInPrerequisiteState) — error path
# ---------------------------------------------------------------------------


@requires_over_10
def test_statement_metrics_pgss_not_loaded_v2(aggregator, integration_check, dbm_instance_v2):
    check = integration_check(dbm_instance_v2)

    with mock.patch(
        'datadog_checks.postgres.statements_v2.PostgresStatementMetricsV2._get_pg_stat_statements_columns',
        side_effect=psycopg.errors.ObjectNotInPrerequisiteState('pg_stat_statements must be loaded'),
    ):
        run_one_check(check)

    expected_tags = _get_expected_tags(
        check, dbm_instance_v2, with_host=False, with_db=True, agent_hostname='stubbed.hostname'
    ) + ['error:database-ObjectNotInPrerequisiteState-pg_stat_statements_not_loaded']

    aggregator.assert_metric(
        'dd.postgres.statement_metrics.error', value=1.0, count=1, tags=expected_tags, hostname='stubbed.hostname'
    )
    assert len(check.warnings) == 1
    assert check.warnings == [
        "Unable to collect statement metrics because pg_stat_statements extension is not loaded "
        "in database 'datadog_test'. "
        "See https://docs.datadoghq.com/database_monitoring/setup_postgres/troubleshooting#"
        "pg-stat-statements-not-loaded"
        " for more details\ncode=pg-stat-statements-not-loaded dbname=datadog_test host=stubbed.hostname",
    ]


# ---------------------------------------------------------------------------
# FQT TTL cache deduplication
# ---------------------------------------------------------------------------


@requires_over_10
def test_fqt_cache_deduplication_v2(aggregator, integration_check, dbm_instance_v2):
    """FQT events for a given query are emitted exactly once within the TTL window."""
    conn = psycopg.connect(
        host=HOST, dbname=DB_NAME, user="bob", password="bob", autocommit=True, cursor_factory=ClientCursor
    )

    check = integration_check(dbm_instance_v2)
    check._connect()

    # Cycle 1: seeds the counter baseline (no derivatives yet)
    conn.cursor().execute("SELECT city FROM persons WHERE city = %s", ("hello",))
    run_one_check(check, cancel=False)

    # Cycle 2: derivatives produced → FQT event emitted and cached
    conn.cursor().execute("SELECT city FROM persons WHERE city = %s", ("hello",))
    run_one_check(check, cancel=False)

    # Cycle 3: same query → FQT cache hit, event must NOT be re-emitted
    conn.cursor().execute("SELECT city FROM persons WHERE city = %s", ("hello",))
    run_one_check(check, cancel=False)

    conn.close()

    expected_query = "SELECT city FROM persons WHERE city = $1"
    query_signature = compute_sql_signature(expected_query)

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    fqt_events = [e for e in dbm_samples if e.get('dbm_type') == 'fqt']
    matching = [e for e in fqt_events if e['db']['query_signature'] == query_signature]

    assert len(matching) == 1, (
        f"Expected exactly 1 FQT event across 3 cycles but got {len(matching)}; TTL cache deduplication may be broken"
    )


# ---------------------------------------------------------------------------
# Ignored (/* DDIGNORE */) queries are learned once and never re-fetched
# ---------------------------------------------------------------------------


@requires_over_10
def test_ignored_queries_do_not_cause_lookup_cycles_v2(aggregator, integration_check, dbm_instance_v2):
    """The check's own /* DDIGNORE */ queries run every cycle and would otherwise trigger a query-text
    fetch each time. Once classified as DDIGNORE, a key must be remembered and skipped so it never costs
    another fetch on a later cycle (unless it genuinely vanished from pg_stat_statements in between)."""
    conn = psycopg.connect(
        host=HOST, dbname=DB_NAME, user="bob", password="bob", autocommit=True, cursor_factory=ClientCursor
    )

    check = integration_check(dbm_instance_v2)
    check._connect()

    # First cycle selects and instantiates the V2 collector; capture it before installing the spy.
    conn.cursor().execute("SELECT city FROM persons WHERE city = %s", ("hello",))
    run_one_check(check, cancel=False)
    job = check.statement_metrics
    assert isinstance(job, PostgresStatementMetricsV2)

    # Spy on the text fetch across every cycle, recording which keys were classified as DDIGNORE and
    # which keys vanished from pgss before each fetch (legitimate re-fetches if they later return).
    original_fetch = job._fetch_query_texts
    ddignore_keys_seen: set = set()
    refetched_ddignore: set = set()
    vanished_before_fetch: set = set()

    def _spy(keys):
        # A key already known to be DDIGNORE that is fetched again — and did not vanish in the
        # meantime — means it slipped past the skip and is still costing a lookup every cycle.
        replayed = (set(keys) & ddignore_keys_seen) - vanished_before_fetch
        refetched_ddignore.update(replayed)
        texts = original_fetch(keys)
        for key, text in texts.items():
            if text and text.startswith(DDIGNORE_COMMENT):
                ddignore_keys_seen.add(key)
        return texts

    original_resolve = job._resolve_obfuscations
    previous_live_keys: set = set()

    def _resolve_spy(live_pgss_keys, changed_pgss_keys):
        # Retention is driven by the live key set, so a key that left pgss is whatever was live on
        # the previous cycle but is not live now.
        vanished_before_fetch.update(previous_live_keys - live_pgss_keys)
        previous_live_keys.clear()
        previous_live_keys.update(live_pgss_keys)
        return original_resolve(live_pgss_keys, changed_pgss_keys)

    with (
        mock.patch.object(job, '_fetch_query_texts', side_effect=_spy),
        mock.patch.object(job, '_resolve_obfuscations', side_effect=_resolve_spy),
    ):
        for _ in range(8):
            conn.cursor().execute("SELECT city FROM persons WHERE city = %s", ("hello",))
            run_one_check(check, cancel=False)

    conn.close()

    if not ddignore_keys_seen:
        # Some Postgres versions (e.g. 18) normalize the leading comment out of the stored
        # pg_stat_statements text, so /* DDIGNORE */ queries never reach the fetch path and
        # there is nothing to assert about skipping them here.
        pytest.skip("No /* DDIGNORE */ queries surfaced in pg_stat_statements on this version")
    assert not refetched_ddignore, (
        f"DDIGNORE keys were re-fetched on later cycles instead of being skipped: {sorted(refetched_ddignore)}"
    )


# ---------------------------------------------------------------------------
# Shared fixtures for the collection-cycle tests below
# ---------------------------------------------------------------------------

TEST_QUERY = "SELECT city FROM persons WHERE city = %s"
TEST_QUERY_NORMALIZED = "SELECT city FROM persons WHERE city = $1"


def _test_query_conn():
    return psycopg.connect(
        host=HOST, dbname=DB_NAME, user="bob", password="bob", autocommit=True, cursor_factory=ClientCursor
    )


def _emitted_calls(aggregator, query_signature):
    """Every `calls` value emitted for one query signature across all collected payloads."""
    return [
        row['calls']
        for event in aggregator.get_event_platform_events("dbm-metrics")
        for row in event['postgres_rows']
        if row['query_signature'] == query_signature
    ]


def _run_cycle(check, conn):
    """Advance the test query's counters by one execution, then collect over them."""
    conn.cursor().execute(TEST_QUERY, ("hello",))
    run_one_check(check, cancel=False)


# ---------------------------------------------------------------------------
# Counter resets are re-baselined instead of emitting bogus deltas
# ---------------------------------------------------------------------------


@requires_over_10
def test_counter_reset_between_cycles_v2(aggregator, integration_check, dbm_instance_v2):
    """pg_stat_statements counters are cumulative, so a reset makes the next snapshot lower than the
    previous one. That row must be dropped and re-baselined, since diffing against the stale higher
    baseline would report a negative call count."""
    conn = _test_query_conn()
    check = integration_check(dbm_instance_v2)
    check._connect()

    query_signature = compute_sql_signature(TEST_QUERY_NORMALIZED)

    _run_cycle(check, conn)  # seeds the baseline
    _run_cycle(check, conn)  # first interval with a baseline to diff against
    assert _emitted_calls(aggregator, query_signature) == [1], "one execution per cycle should report calls=1"

    aggregator.reset()
    with _get_superconn(dbm_instance_v2) as superconn:
        with superconn.cursor() as cur:
            cur.execute("SELECT pg_stat_statements_reset();")

    _run_cycle(check, conn)
    assert _emitted_calls(aggregator, query_signature) == [], (
        "the cycle spanning a counter reset must drop the row rather than emit a bogus delta"
    )

    _run_cycle(check, conn)
    assert _emitted_calls(aggregator, query_signature) == [1], (
        "collection must recover from the post-reset baseline on the following cycle"
    )

    conn.close()


# ---------------------------------------------------------------------------
# Steady-state cache hit rate
# ---------------------------------------------------------------------------


@requires_over_10
def test_cache_hit_rate_stable_across_cycles_v2(aggregator, integration_check, dbm_instance_v2):
    """Once a statement's text is cached, later cycles must serve it from the cache rather than
    re-fetching it from Postgres. If live entries are dropped prematurely the emitted metrics stay
    correct, so only the hit rate reveals that every cycle is re-fetching and re-obfuscating.

    A new (queryid, dbid, userid) can still appear after warmup — autovacuum, or a check query
    whose first snapshot landed on the last warmup cycle — and that costs one miss. The bug this
    catches is re-fetching a key that is already known and still live.
    """
    conn = _test_query_conn()
    check = integration_check(dbm_instance_v2)
    check._connect()

    # First cycle selects and instantiates the V2 collector; capture it before installing the spy.
    _run_cycle(check, conn)
    job = check.statement_metrics
    assert isinstance(job, PostgresStatementMetricsV2)

    original_fetch = job._fetch_query_texts
    fetched_keys: set = set()
    refetched_while_live: set = set()
    vanished_before_fetch: set = set()
    measuring = False

    def _fetch_spy(keys):
        if measuring:
            # A key we already fetched that is fetched again — and did not leave pg_stat_statements
            # in between — means the cache dropped a live entry.
            refetched_while_live.update((set(keys) & fetched_keys) - vanished_before_fetch)
        texts = original_fetch(keys)
        fetched_keys.update(texts.keys())
        return texts

    original_resolve = job._resolve_obfuscations
    previous_live_keys: set = set()

    def _resolve_spy(live_pgss_keys, changed_pgss_keys):
        vanished_before_fetch.update(previous_live_keys - live_pgss_keys)
        previous_live_keys.clear()
        previous_live_keys.update(live_pgss_keys)
        return original_resolve(live_pgss_keys, changed_pgss_keys)

    steady_state_cycles = 3
    with (
        mock.patch.object(job, '_fetch_query_texts', side_effect=_fetch_spy),
        mock.patch.object(job, '_resolve_obfuscations', side_effect=_resolve_spy),
    ):
        # Recurring check statements trickle into pg_stat_statements over the next few cycles.
        for _ in range(5):
            _run_cycle(check, conn)

        aggregator.reset()
        measuring = True
        for _ in range(steady_state_cycles):
            _run_cycle(check, conn)

    conn.close()

    hits = [m.value for m in aggregator.metrics("dd.postgres.statement_metrics.lookup.hits")]

    assert len(hits) == steady_state_cycles, f"expected one hits gauge per cycle, got {hits}"
    assert all(hit > 0 for hit in hits), f"steady-state cycles served nothing from cache: hits={hits}"
    assert not refetched_while_live, f"cached keys were re-fetched while still live: {sorted(refetched_while_live)}"


# ---------------------------------------------------------------------------
# Retention on a cycle that produced no derivative rows
# ---------------------------------------------------------------------------


@requires_over_10
def test_retention_drops_keys_that_left_pgss_v2(aggregator, integration_check, dbm_instance_v2):
    """Cache entries for statements that left pg_stat_statements must be dropped even on a cycle
    where nothing advanced. Retention that only runs when there is output to emit leaves those
    entries in place on a quiet instance, spending the cache on statements that no longer exist.
    """
    conn = _test_query_conn()
    check = integration_check(dbm_instance_v2)
    check._connect()

    _run_cycle(check, conn)
    job = check.statement_metrics
    assert isinstance(job, PostgresStatementMetricsV2)

    # Capture the snapshot of the cycle that populates the cache so it can be replayed below.
    captured_snapshot: list = []
    original_snapshot = job._load_lightweight_snapshot

    def _capture():
        rows = original_snapshot()
        captured_snapshot[:] = rows
        return rows

    with mock.patch.object(job, '_load_lightweight_snapshot', side_effect=_capture):
        _run_cycle(check, conn)

    # The reported row carries the statement's queryid, and the snapshot row it came from completes
    # the pgss key, so the key under test is derived from what the collector emitted.
    query_signature = compute_sql_signature(TEST_QUERY_NORMALIZED)
    reported = [
        row
        for event in aggregator.get_event_platform_events("dbm-metrics")
        for row in event['postgres_rows']
        if row['query_signature'] == query_signature
    ]
    assert reported, "the test query should be reported before it is removed from the snapshot"
    departed = [row for row in captured_snapshot if row['queryid'] == reported[0]['queryid']]
    assert len(departed) == 1, f"expected one snapshot row for the reported statement, got {departed}"
    departed_key = pgss_key(departed[0])

    # Replaying the same snapshot leaves every counter unchanged, so the cycle produces no
    # derivative rows; dropping one row makes that key absent from the table while the rest of the
    # snapshot stays live.
    quiet_snapshot = [row for row in captured_snapshot if pgss_key(row) != departed_key]

    aggregator.reset()
    with mock.patch.object(job, '_load_lightweight_snapshot', return_value=quiet_snapshot):
        run_one_check(check, cancel=False)

    assert _emitted_calls(aggregator, query_signature) == [], "the replayed snapshot should report nothing"
    dropped = [m.value for m in aggregator.metrics("dd.postgres.statement_metrics.lookup.dropped")]
    assert sum(dropped) >= 1, f"retention did not run on a cycle that produced no derivative rows: {dropped}"

    # The statement is back in the table. One cycle re-establishes its counter baseline and the next
    # sees it advance, at which point its text has to be read from Postgres again -- which only
    # happens if retention discarded the cached result rather than merely counting it.
    fetched_keys: set = set()
    original_fetch = job._fetch_query_texts

    def _fetch_spy(keys):
        fetched_keys.update(keys)
        return original_fetch(keys)

    with mock.patch.object(job, '_fetch_query_texts', side_effect=_fetch_spy):
        _run_cycle(check, conn)
        _run_cycle(check, conn)

    conn.close()

    assert departed_key in fetched_keys, (
        "a key dropped by retention must be re-fetched once its statement returns, but its text was "
        "served from the cache"
    )
