# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures.thread import ThreadPoolExecutor

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
    pg_instance['collect_settings'] = {'enabled': False}
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
    pg_instance['collect_settings'] = {'enabled': False}
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


def _analyze_tables(pg_instance):
    """Run ANALYZE on test tables so they appear in the collector's time window."""
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cur:
        cur.execute("ANALYZE persons")
        cur.execute("ANALYZE cities")
        cur.execute("ANALYZE pgtable")
    conn.close()


def test_collect_column_stats(integration_check, dbm_instance, pg_instance, aggregator):
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
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['exclude_tables'] = ['persons', 'pgtable', 'cities']
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    # Either no events or events with no matching tables
    if len(events) > 0:
        for event in events:
            for table_entry in event['column_stats']:
                assert table_entry['table'] not in ('persons', 'pgtable', 'cities')


def test_collect_column_stats_max_tables(integration_check, dbm_instance, pg_instance, aggregator):
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['max_tables'] = 1
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    if len(events) > 0:
        # With max_tables=1, should have at most 1 table in the stats
        total_tables = sum(len(e['column_stats']) for e in events)
        assert total_tables <= 1, f"Expected at most 1 table but got {total_tables}"


def test_collect_column_stats_disabled(integration_check, dbm_instance, aggregator):
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


def test_collect_column_stats_recovery(integration_check, dbm_instance, pg_instance, aggregator):
    """Test that recovery from function_not_found emits an OK health event."""
    _analyze_tables(pg_instance)
    check = integration_check(dbm_instance)
    # Run check to initialize connections and pool
    check.run()

    try:
        # Simulate prior function-not-found state on the collector
        collector = check.metadata_samples._column_stats_collector
        collector._function_not_found = True
        aggregator.reset()

        # Call collector directly — the function exists, so it succeeds and triggers recovery
        collector.collect_column_stats([])

        health_events = aggregator.get_event_platform_events("dbm-health")
        ok_events = [e for e in health_events if e['name'] == 'column_stats_function_not_found' and e['status'] == 'ok']
        assert len(ok_events) == 1, f"Expected OK health event after recovery, got {health_events}"
        assert not collector._function_not_found, "Expected _function_not_found to be cleared"
    finally:
        check.cancel()
        if check.metadata_samples._job_loop_future is not None:
            check.metadata_samples._job_loop_future.result()


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
    """Test that exclude takes precedence when both include and exclude match."""
    _analyze_tables(pg_instance)
    # Include all tables starting with 'p', but exclude 'pgtable'
    dbm_instance['collect_column_stats']['include_tables'] = ['^p.*']
    dbm_instance['collect_column_stats']['exclude_tables'] = ['^pgtable$']
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
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
    pg_instance['collect_settings'] = {'enabled': False}
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
