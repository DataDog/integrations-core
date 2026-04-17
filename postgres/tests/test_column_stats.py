# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob

from .utils import _get_superconn, run_one_check

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.1
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['collect_settings'] = {'enabled': False, 'run_sync': True}
    pg_instance['collect_schemas'] = {'enabled': False}
    pg_instance['collect_column_stats'] = {
        'enabled': True,
        'collection_interval': 36000,
        'max_tables': 100,
    }
    return pg_instance


@pytest.fixture
def nofunc_instance(pg_instance):
    """Instance pointing at dogs_nofunc, which has the datadog schema but no column_stats() function."""
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.1
    pg_instance['dbname'] = 'dogs_nofunc'
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['collect_settings'] = {'enabled': False, 'run_sync': True}
    pg_instance['collect_schemas'] = {'enabled': False}
    pg_instance['collect_column_stats'] = {
        'enabled': True,
        'collection_interval': 36000,
        'max_tables': 100,
    }
    return pg_instance


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.fixture
def check_runner(integration_check, aggregator):
    """Build + initialize a check via check.run(), reset the aggregator, and tear down the metadata job on exit.

    Tests that exercise the collector directly (rather than via run_one_check) use this to avoid
    repeating the check.run() / aggregator.reset() / cancel+future.result() boilerplate.
    """
    checks = []

    def _runner(instance, reset_aggregator=True):
        check = integration_check(instance)
        check.run()
        if reset_aggregator:
            aggregator.reset()
        checks.append(check)
        return check

    yield _runner

    for c in checks:
        c.cancel()
        if c.metadata_samples._job_loop_future is not None:
            c.metadata_samples._job_loop_future.result()


def _analyze_tables(pg_instance):
    """Run ANALYZE on test tables so they appear in the collector's time window."""
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cur:
        cur.execute("ANALYZE persons")
        cur.execute("ANALYZE cities")
        cur.execute("ANALYZE pgtable")
    conn.close()


def _fake_pool_raising(exc):
    """Return a context-managed fake pool connection whose cursor.execute raises exc on the main query.

    SET/RESET statement_timeout calls pass through so RESET cleanup in _collect_for_database still runs.
    """

    @contextmanager
    def get_connection(dbname, **kwargs):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = None

        def execute(sql, *args, **kwargs):
            if 'statement_timeout' in sql:
                return
            raise exc

        cursor.execute.side_effect = execute
        conn = MagicMock()
        conn.cursor.return_value = cursor
        yield conn

    return get_connection


def test_collect_column_stats_happy_path(integration_check, dbm_instance, pg_instance, aggregator):
    """Happy-path smoke test: analyzed tables are collected and emitted with well-formed event + row + column shape."""
    _analyze_tables(pg_instance)
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 0, "Expected at least one column stats event"
    event = events[0]
    assert event['dbm_type'] == 'column_stats'
    assert event['dbms'] == 'postgres'
    assert event['host'] == 'stubbed.hostname'
    assert 'timestamp' in event
    assert 'collection_interval' in event
    assert isinstance(event['column_stats'], list)
    assert len(event['column_stats']) > 0

    # Verify table structure including metadata fields
    table_entry = event['column_stats'][0]
    assert 'schema' in table_entry
    assert 'table' in table_entry
    assert 'columns' in table_entry
    assert 'version' in table_entry
    assert table_entry['version'] == 1
    assert len(table_entry['columns']) > 0
    assert 'last_analyze_age' in table_entry
    assert 'last_autoanalyze_age' in table_entry
    assert 'last_vacuum_age' in table_entry
    assert 'stats_age' in table_entry
    # We just ran ANALYZE, so stats_age should be recent (within 60s)
    assert table_entry['stats_age'] is not None
    assert table_entry['stats_age'] < 60

    # Verify column structure
    col = table_entry['columns'][0]
    assert 'name' in col
    assert 'avg_width' in col
    assert 'n_distinct' in col
    assert 'null_frac' in col

    # Verify we got all 3 analyzed tables
    all_tables = set()
    for evt in events:
        for entry in evt['column_stats']:
            all_tables.add(entry['table'])
    assert 'persons' in all_tables, f"Expected 'persons' in collected tables, got {all_tables}"
    assert 'cities' in all_tables, f"Expected 'cities' in collected tables, got {all_tables}"
    assert 'pgtable' in all_tables, f"Expected 'pgtable' in collected tables, got {all_tables}"


def test_collect_column_stats_include_filter(integration_check, dbm_instance, pg_instance, aggregator):
    """include_tables restricts the result set to tables whose name matches the regex."""
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['include_tables'] = ['persons']
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 0
    for event in events:
        for table_entry in event['column_stats']:
            assert 'persons' in table_entry['table'], f"Expected only 'persons' tables but got '{table_entry['table']}'"


def test_collect_column_stats_exclude_filter(integration_check, dbm_instance, pg_instance, aggregator):
    """exclude_tables removes matching tables from the result set while allowing others through."""
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['exclude_tables'] = ['persons', 'pgtable', 'cities']
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    # personsdup* tables exist but are not manually analyzed; depending on autovacuum they may or
    # may not appear in pg_stats. The contract we check is: no excluded table appears anywhere.
    for event in events:
        for table_entry in event['column_stats']:
            assert table_entry['table'] not in ('persons', 'pgtable', 'cities'), (
                f"Excluded table '{table_entry['table']}' should not have been collected"
            )


def test_collect_column_stats_max_tables(integration_check, dbm_instance, pg_instance, aggregator):
    """max_tables caps the number of collected tables at the configured limit."""
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['max_tables'] = 1
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    total_tables = sum(len(e['column_stats']) for e in events)
    assert total_tables == 1, f"Expected exactly 1 table with max_tables=1, got {total_tables}"


def test_collect_column_stats_disabled(integration_check, dbm_instance, aggregator):
    """collect_column_stats.enabled=False suppresses collection entirely."""
    dbm_instance['collect_column_stats']['enabled'] = False
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) == 0, "Expected no events when column stats collection is disabled"


def test_collect_column_stats_function_not_found(integration_check, nofunc_instance, aggregator):
    """Test that missing datadog.column_stats() emits a health WARNING and no column stats."""
    check = integration_check(nofunc_instance)
    run_one_check(check)

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) == 0, "Expected no column stats events when function doesn't exist"

    health_events = aggregator.get_event_platform_events("dbm-health")
    function_not_found_events = [e for e in health_events if e['name'] == 'column_stats_function_not_found']
    assert len(function_not_found_events) == 1
    assert function_not_found_events[0]['status'] == 'warning'


def test_collect_column_stats_function_not_found_logs_once(integration_check, nofunc_instance, aggregator):
    """Test that repeated failures only emit a single health WARNING."""
    nofunc_instance['collect_column_stats']['collection_interval'] = 0.1
    check = integration_check(nofunc_instance)
    run_one_check(check)
    run_one_check(check)
    run_one_check(check)

    health_events = aggregator.get_event_platform_events("dbm-health")
    function_not_found_events = [e for e in health_events if e['name'] == 'column_stats_function_not_found']
    assert len(function_not_found_events) == 1, (
        f"Expected exactly 1 health event but got {len(function_not_found_events)}"
    )


def test_collect_column_stats_recovery(check_runner, dbm_instance, pg_instance, aggregator):
    """Recovery from a prior function_not_found state emits an OK health event and clears the error set."""
    _analyze_tables(pg_instance)
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector
    collector._function_not_found_dbs.add('datadog_test')

    # Call collector directly — the function exists, so it succeeds and triggers recovery
    collector.collect_column_stats([])

    health_events = aggregator.get_event_platform_events("dbm-health")
    ok_events = [e for e in health_events if e['name'] == 'column_stats_function_not_found' and e['status'] == 'ok']
    assert len(ok_events) == 1, f"Expected OK health event after recovery, got {health_events}"
    assert 'datadog_test' not in collector._function_not_found_dbs, "Expected datadog_test removed from error set"


def test_collect_column_stats_collection_interval_in_event(integration_check, dbm_instance, pg_instance, aggregator):
    """Test that the configured collection_interval appears in the emitted event."""
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['collection_interval'] = 7200
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 0, "Expected at least one column stats event"
    assert events[0]['collection_interval'] == 7200


def test_collect_column_stats_include_and_exclude(integration_check, dbm_instance, pg_instance, aggregator):
    """When both include and exclude match, exclude takes precedence."""
    _analyze_tables(pg_instance)
    # Include all tables starting with 'p', but exclude 'pgtable'
    dbm_instance['collect_column_stats']['include_tables'] = ['^p.*']
    dbm_instance['collect_column_stats']['exclude_tables'] = ['^pgtable$']
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 0, "Expected events for analyzed tables starting with 'p' (e.g. 'persons')"
    for event in events:
        for table_entry in event['column_stats']:
            assert table_entry['table'] != 'pgtable', "pgtable should be excluded"
            assert table_entry['table'].startswith('p'), (
                f"Expected only tables starting with 'p' but got '{table_entry['table']}'"
            )


def test_collect_column_stats_default_config(integration_check, pg_instance, aggregator):
    """Test that minimal config (just enabled) uses correct defaults."""
    _analyze_tables(pg_instance)
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.1
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['collect_settings'] = {'enabled': False, 'run_sync': True}
    pg_instance['collect_schemas'] = {'enabled': False}
    pg_instance['collect_column_stats'] = {
        'enabled': True,
    }
    check = integration_check(pg_instance)
    run_one_check(check)
    collector = check.metadata_samples._column_stats_collector
    # Verify defaults
    assert collector._config.collection_interval == 14400
    assert collector._config.max_tables == 500
    assert collector._config.include_tables == []
    assert collector._config.exclude_tables == []


def test_collect_column_stats_no_health_event_on_success(integration_check, dbm_instance, pg_instance, aggregator):
    """Test that a successful collection does not emit any column stats health events."""
    _analyze_tables(pg_instance)
    check = integration_check(dbm_instance)
    run_one_check(check)

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 0, "Expected column stats events"

    health_events = aggregator.get_event_platform_events("dbm-health")
    column_stats_health = [
        e
        for e in health_events
        if e['name'] in ('column_stats_function_not_found', 'column_stats_insufficient_privilege')
    ]
    assert len(column_stats_health) == 0, f"Expected no column stats health events, got {column_stats_health}"


def test_collect_column_stats_respects_interval(integration_check, dbm_instance, pg_instance, aggregator):
    """Test that the second run within the collection interval does not emit a new event."""
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['collection_interval'] = 36000
    check = integration_check(dbm_instance)

    run_one_check(check)
    first_count = len(aggregator.get_event_platform_events("dbm-column-stats"))
    assert first_count > 0, "Expected at least one event on first run"

    run_one_check(check)
    second_count = len(aggregator.get_event_platform_events("dbm-column-stats"))
    assert second_count == first_count, (
        f"Expected no new events on second run (interval not elapsed), got {second_count - first_count} new"
    )


@patch('datadog_checks.postgres.column_stats.PAYLOAD_MAX_COLUMNS', 5)
def test_collect_column_stats_payload_chunking(integration_check, dbm_instance, pg_instance, aggregator):
    """Test that large collections are split into multiple payloads."""
    _analyze_tables(pg_instance)
    check = integration_check(dbm_instance)
    run_one_check(check)

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 1, f"Expected multiple payloads with low chunk threshold, got {len(events)}"

    # Every event should have valid structure
    for event in events:
        assert event['dbm_type'] == 'column_stats'
        assert isinstance(event['column_stats'], list)
        assert len(event['column_stats']) > 0

    # All 3 tables should appear across the payloads
    all_tables = set()
    for event in events:
        for entry in event['column_stats']:
            all_tables.add(entry['table'])
    assert 'persons' in all_tables
    assert 'cities' in all_tables
    assert 'pgtable' in all_tables


def test_collect_column_stats_multi_database(check_runner, dbm_instance, pg_instance, aggregator):
    """When autodiscovery returns multiple databases, the collector visits each and emits rows tagged by db."""
    from .common import PASSWORD_ADMIN, USER_ADMIN
    from .utils import _get_conn

    _analyze_tables(pg_instance)
    # Analyze tables in dogs database
    dogs_conn = _get_conn(pg_instance, dbname='dogs', user=USER_ADMIN, password=PASSWORD_ADMIN)
    with dogs_conn.cursor() as cur:
        cur.execute("ANALYZE breed")
        cur.execute("ANALYZE kennel")
    dogs_conn.close()

    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector
    collector._get_databases = lambda: ['datadog_test', 'dogs']
    collector.collect_column_stats([])

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 0, "Expected column stats events"

    dbs_seen = set()
    for event in events:
        for entry in event['column_stats']:
            dbs_seen.add(entry['db'])
    assert 'datadog_test' in dbs_seen, f"Expected datadog_test in collected dbs, got {dbs_seen}"
    assert 'dogs' in dbs_seen, f"Expected dogs in collected dbs, got {dbs_seen}"


def test_collect_column_stats_multi_database_error_isolation(check_runner, dbm_instance, pg_instance, aggregator):
    """A missing function in one db does not block other dbs; the failed db emits a health warning."""
    _analyze_tables(pg_instance)
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector
    collector._get_databases = lambda: ['datadog_test', 'dogs_nofunc']
    collector.collect_column_stats([])

    # Should still get events from datadog_test
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 0, "Expected column stats events from working database"

    dbs_seen = set()
    for event in events:
        for entry in event['column_stats']:
            dbs_seen.add(entry['db'])
    assert 'datadog_test' in dbs_seen, "Expected datadog_test results despite dogs_nofunc failure"
    assert 'dogs_nofunc' not in dbs_seen, "Should not have results from dogs_nofunc"

    # Should have emitted a health warning for the missing function
    health_events = aggregator.get_event_platform_events("dbm-health")
    function_not_found_events = [e for e in health_events if e['name'] == 'column_stats_function_not_found']
    assert len(function_not_found_events) == 1


def test_collect_column_stats_exclude_all(integration_check, dbm_instance, pg_instance, aggregator):
    """Test that excluding all tables produces no events."""
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['exclude_tables'] = ['.*']
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) == 0, "Expected no events when all tables are excluded"


def test_collect_column_stats_include_nonexistent(integration_check, dbm_instance, pg_instance, aggregator):
    """Test that including only nonexistent tables produces no events."""
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['include_tables'] = ['this_table_does_not_exist']
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) == 0, "Expected no events when no tables match include filter"


def test_collect_column_stats_max_tables_zero(integration_check, dbm_instance, pg_instance, aggregator):
    """Test that max_tables=0 produces no events and no error."""
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['max_tables'] = 0
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) == 0, "Expected no events with max_tables=0"


def test_collect_column_stats_insufficient_privilege(check_runner, dbm_instance, aggregator):
    """InsufficientPrivilege on datadog.column_stats() emits a dedicated health WARNING."""
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector
    exc = psycopg.errors.InsufficientPrivilege("permission denied for function datadog.column_stats")
    with patch.object(check.db_pool, 'get_connection', _fake_pool_raising(exc)):
        collector.collect_column_stats([])

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) == 0, "Expected no events when privileges are insufficient"

    health_events = aggregator.get_event_platform_events("dbm-health")
    priv_events = [e for e in health_events if e['name'] == 'column_stats_insufficient_privilege']
    assert len(priv_events) == 1, f"Expected 1 insufficient-privilege health event, got {health_events}"
    assert priv_events[0]['status'] == 'warning'
    assert 'datadog_test' in collector._insufficient_privilege_dbs


def test_collect_column_stats_insufficient_privilege_logs_once(check_runner, dbm_instance, aggregator):
    """Repeated privilege failures on the same database emit a single health WARNING (dedup)."""
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector
    exc = psycopg.errors.InsufficientPrivilege("permission denied")
    with patch.object(check.db_pool, 'get_connection', _fake_pool_raising(exc)):
        collector.collect_column_stats([])
        collector.collect_column_stats([])
        collector.collect_column_stats([])

    health_events = aggregator.get_event_platform_events("dbm-health")
    priv_events = [e for e in health_events if e['name'] == 'column_stats_insufficient_privilege']
    assert len(priv_events) == 1, f"Expected exactly 1 privilege health event, got {len(priv_events)}"


def test_collect_column_stats_insufficient_privilege_recovery(check_runner, dbm_instance, pg_instance, aggregator):
    """When privileges are restored, the collector emits an OK health event and clears the error set."""
    _analyze_tables(pg_instance)
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector
    collector._insufficient_privilege_dbs.add('datadog_test')

    collector.collect_column_stats([])

    health_events = aggregator.get_event_platform_events("dbm-health")
    ok_events = [e for e in health_events if e['name'] == 'column_stats_insufficient_privilege' and e['status'] == 'ok']
    assert len(ok_events) == 1, f"Expected 1 OK health event after recovery, got {health_events}"
    assert 'datadog_test' not in collector._insufficient_privilege_dbs


def test_collect_column_stats_disabled_when_dbm_false(integration_check, pg_instance, aggregator):
    """Column stats should not be collected when dbm=False, even if collect_column_stats.enabled=True."""
    _analyze_tables(pg_instance)
    pg_instance['dbm'] = False
    pg_instance['collect_settings'] = {'enabled': False, 'run_sync': True}
    pg_instance['collect_schemas'] = {'enabled': False}
    pg_instance['collect_column_stats'] = {'enabled': True, 'collection_interval': 36000, 'max_tables': 100}
    check = integration_check(pg_instance)
    run_one_check(check)

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) == 0, "Expected no events when dbm=False"


def test_collect_column_stats_statement_timeout_handled(check_runner, dbm_instance, aggregator):
    """A statement-timeout cancellation is logged and does not raise out of the collector."""
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector
    exc = psycopg.errors.QueryCanceled("canceling statement due to statement timeout")
    with patch.object(check.db_pool, 'get_connection', _fake_pool_raising(exc)):
        collector.collect_column_stats([])

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) == 0, "Expected no events when the query times out"
    # No unhandled exception means the outer handler in _collect_for_database absorbed it.


def test_collect_column_stats_cancel_stops_multi_db_iteration(check_runner, dbm_instance, pg_instance):
    """Setting _cancel_event between databases stops further iteration."""
    _analyze_tables(pg_instance)
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector
    collector._get_databases = lambda: ['datadog_test', 'dogs']

    original = collector._collect_for_database
    calls = []

    def tracking_collect(db_name, tags_no_db):
        calls.append(db_name)
        if db_name == 'datadog_test':
            collector._cancel_event.set()
        return original(db_name, tags_no_db)

    collector._collect_for_database = tracking_collect
    collector.collect_column_stats([])

    assert calls == ['datadog_test'], f"Expected iteration to stop after cancel, got {calls}"


def test_collect_column_stats_event_payload_fields(integration_check, dbm_instance, pg_instance, aggregator):
    """Event payload includes all routing and context fields required by downstream consumers."""
    _analyze_tables(pg_instance)
    dbm_instance['tags'] = ['foo:bar', 'env:test']
    check = integration_check(dbm_instance)
    run_one_check(check)

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 0
    event = events[0]

    for field in (
        'host',
        'database_instance',
        'ddagentversion',
        'dbms',
        'dbms_version',
        'cloud_metadata',
        'dbm_type',
        'collection_interval',
        'tags',
        'timestamp',
        'column_stats',
    ):
        assert field in event, f"Expected '{field}' in event payload, got keys={sorted(event.keys())}"

    assert event['dbms'] == 'postgres'
    assert event['dbm_type'] == 'column_stats'
    assert event['host'] == 'stubbed.hostname'
    assert event['database_instance']
    # tags_no_db must not include a `db:` tag (column_stats aggregates across databases)
    assert not any(t.startswith('db:') for t in event['tags']), (
        f"Expected no db: tag in event tags (tags_no_db), got {event['tags']}"
    )
    assert 'foo:bar' in event['tags']


def _assert_metric_with_tag(aggregator, metric_name, required_tag):
    """Assert at least one emitted sample of metric_name carries required_tag (tag-subset match)."""
    samples = aggregator.metrics(metric_name)
    matches = [s for s in samples if required_tag in s.tags]
    assert matches, (
        f"Expected '{metric_name}' with tag '{required_tag}' — found {len(samples)} sample(s), none matching"
    )


def test_collect_column_stats_metrics_emitted_on_success(integration_check, dbm_instance, pg_instance, aggregator):
    """A successful collection emits the full set of operational metrics tagged status:success."""
    _analyze_tables(pg_instance)
    check = integration_check(dbm_instance)
    run_one_check(check)

    for metric in (
        'dd.postgres.column_stats.time',
        'dd.postgres.column_stats.tables_count',
        'dd.postgres.column_stats.columns_count',
        'dd.postgres.column_stats.payloads_count',
    ):
        _assert_metric_with_tag(aggregator, metric, 'status:success')


def test_collect_column_stats_metrics_emitted_on_error(check_runner, dbm_instance, aggregator):
    """When an unexpected exception escapes the per-database handler, operational metrics are tagged status:error."""
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector
    collector._get_databases = MagicMock(side_effect=RuntimeError("simulated autodiscovery failure"))

    with pytest.raises(RuntimeError):
        collector.collect_column_stats([])

    for metric in (
        'dd.postgres.column_stats.time',
        'dd.postgres.column_stats.tables_count',
        'dd.postgres.column_stats.columns_count',
        'dd.postgres.column_stats.payloads_count',
    ):
        _assert_metric_with_tag(aggregator, metric, 'status:error')


def test_collect_column_stats_special_chars_in_pattern_do_not_crash(
    check_runner, dbm_instance, pg_instance, aggregator
):
    """Filter patterns with regex/SQL-special characters must not raise from the collector.

    Agent config is trusted, but the collector should degrade gracefully (log and move on) rather
    than crash the whole metadata job if a user supplies a malformed pattern.
    """
    _analyze_tables(pg_instance)
    # Single quote would break SQL if unescaped; brackets form a character class.
    dbm_instance['collect_column_stats']['include_tables'] = ["bad'pattern", "[invalid"]
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector

    # Must not raise — the outer per-database except catches query errors and logs them.
    collector.collect_column_stats([])

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert events == [], f"Expected no events for malformed pattern, got {len(events)}"


def test_collect_column_stats_handles_missing_version(check_runner, dbm_instance, pg_instance, aggregator):
    """Collection succeeds when check.version is None (payload_pg_version returns an empty string)."""
    _analyze_tables(pg_instance)
    check = check_runner(dbm_instance)
    check.version = None

    collector = check.metadata_samples._column_stats_collector
    collector.collect_column_stats([])

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 0, "Expected events even when version is unavailable"
    assert events[0]['dbms_version'] == '', (
        f"Expected empty dbms_version when check.version is None, got {events[0]['dbms_version']!r}"
    )


def test_collect_column_stats_uses_autodiscovered_databases(check_runner, dbm_instance):
    """_get_databases returns the autodiscovered set when autodiscovery is active."""
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector

    autodiscovery = MagicMock()
    autodiscovery.get_items.return_value = ['db_one', 'db_two']
    check.autodiscovery = autodiscovery

    assert collector._get_databases() == ['db_one', 'db_two']


def test_collect_column_stats_pre_cancelled_skips_collection(check_runner, dbm_instance, aggregator):
    """If _cancel_event is already set before collection starts, no databases are visited and no events emitted."""
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector
    visited = []
    collector._collect_for_database = lambda db, tags: visited.append(db)

    collector._cancel_event.set()
    try:
        collector.collect_column_stats([])
    finally:
        collector._cancel_event.clear()

    assert visited == [], f"Expected no databases visited when pre-cancelled, got {visited}"
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert events == [], "Expected no events when collection is pre-cancelled"


def test_collect_column_stats_partial_recovery_waits_for_all_dbs(check_runner, dbm_instance, pg_instance, aggregator):
    """Recovery OK event fires only after every failing db has recovered; partial recovery stays silent."""
    _analyze_tables(pg_instance)
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector

    # Seed two dbs into each error set; only recover one of them.
    collector._function_not_found_dbs.update({'datadog_test', 'still_broken_db'})
    collector._insufficient_privilege_dbs.update({'datadog_test', 'still_broken_db'})
    collector._get_databases = lambda: ['datadog_test']

    collector.collect_column_stats([])

    health_events = aggregator.get_event_platform_events("dbm-health")
    ok_events = [
        e
        for e in health_events
        if e['name'] in ('column_stats_function_not_found', 'column_stats_insufficient_privilege')
        and e['status'] == 'ok'
    ]
    assert ok_events == [], f"Expected no OK events while other dbs remain in error, got {ok_events}"
    assert 'datadog_test' not in collector._function_not_found_dbs
    assert 'still_broken_db' in collector._function_not_found_dbs
    assert 'datadog_test' not in collector._insufficient_privilege_dbs
    assert 'still_broken_db' in collector._insufficient_privilege_dbs


def test_collect_column_stats_non_database_error_is_absorbed(check_runner, dbm_instance, aggregator):
    """Non-DatabaseError exceptions from the cursor are logged per-db and do not propagate out of the collector."""
    check = check_runner(dbm_instance)
    collector = check.metadata_samples._column_stats_collector

    # ValueError is not a psycopg DatabaseError, so it exercises the catch-all except Exception branch.
    exc = ValueError("unexpected non-DB failure")
    with patch.object(check.db_pool, 'get_connection', _fake_pool_raising(exc)):
        collector.collect_column_stats([])  # must not raise

    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert events == [], "Expected no events when the cursor raises a non-DatabaseError"
