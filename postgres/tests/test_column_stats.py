# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures.thread import ThreadPoolExecutor

import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob

from .common import HOST, PORT
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
        'run_sync': True,
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

    # Verify table structure
    table_entry = event['column_stats'][0]
    assert 'schema' in table_entry
    assert 'table' in table_entry
    assert 'columns' in table_entry
    assert 'version' in table_entry
    assert table_entry['version'] == 1
    assert len(table_entry['columns']) > 0

    # Verify column structure
    col = table_entry['columns'][0]
    assert 'name' in col
    assert 'avg_width' in col
    assert 'n_distinct' in col
    assert 'null_frac' in col


def test_collect_column_stats_include_filter(integration_check, dbm_instance, pg_instance, aggregator):
    _analyze_tables(pg_instance)
    dbm_instance['collect_column_stats']['include_tables'] = ['persons']
    check = integration_check(dbm_instance)
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) > 0
    for event in events:
        for table_entry in event['column_stats']:
            assert 'persons' in table_entry['table'], (
                f"Expected only 'persons' tables but got '{table_entry['table']}'"
            )


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


def test_collect_column_stats_function_not_found(integration_check, pg_instance, aggregator):
    """Test that the collector handles missing datadog.column_stats() gracefully."""
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.1
    pg_instance['dbname'] = 'dogs_noschema'
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['collect_settings'] = {'enabled': False}
    pg_instance['collect_schemas'] = {'enabled': False}
    pg_instance['collect_column_stats'] = {
        'enabled': True,
        'collection_interval': 36000,
        'max_tables': 100,
        'run_sync': True,
    }
    check = integration_check(pg_instance)
    # Should not raise an exception
    run_one_check(check)
    events = aggregator.get_event_platform_events("dbm-column-stats")
    assert len(events) == 0, "Expected no events when function doesn't exist"


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
    dbm_instance['collect_column_stats']['include_tables'] = ['p.*']
    dbm_instance['collect_column_stats']['exclude_tables'] = ['pgtable']
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
    """Test that minimal config (just enabled + run_sync) uses correct defaults."""
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
        'run_sync': True,
    }
    check = integration_check(pg_instance)
    run_one_check(check)
    collector = check.column_stats
    # Verify defaults
    assert collector.collection_interval == 14400
    assert collector.max_tables == 500
    assert collector.include_tables == []
    assert collector.exclude_tables == []
