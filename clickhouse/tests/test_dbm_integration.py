# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from copy import deepcopy
from unittest import mock

import clickhouse_connect
import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob, obfuscate_sql_with_metadata
from datadog_checks.clickhouse import ClickhouseCheck

from .common import CLICKHOUSE_VERSION

# DBM features require ClickHouse 21.8+ for normalized_query_hash, query_kind, etc.
# 21.8 itself is excluded because:
#   - fromUnixTimestamp64Micro() requires explicit Int64 cast (fixed in later versions)
#   - system.processes is missing the query_kind column
# 22.7 is excluded because query_kind column in system.processes is not available in all builds
UNSUPPORTED_DBM_VERSIONS = {'18', '19', '20', '21.8', '22.7'}

SAMPLE_QUERIES = [
    "SELECT count() FROM system.tables WHERE database = 'default'",
    "SELECT name, engine FROM system.databases ORDER BY name",
]

METRICS_COLUMNS = {
    'count',
    'total_time',
    'mean_time',
    'read_rows',
    'read_bytes',
    'written_rows',
    'written_bytes',
    'result_rows',
    'result_bytes',
    'memory_usage',
    'peak_memory_usage',
}


def _is_dbm_supported():
    if CLICKHOUSE_VERSION == 'latest':
        return True
    return CLICKHOUSE_VERSION not in UNSUPPORTED_DBM_VERSIONS


pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures('dd_environment'),
    pytest.mark.skipif(
        not _is_dbm_supported(),
        reason="DBM features require ClickHouse 21.8+ (normalized_query_hash, query_kind, etc.)",
    ),
]


@pytest.fixture
def dbm_instance(instance):
    instance['dbm'] = True
    instance['query_metrics'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 60,
    }
    instance['query_samples'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 1,
    }
    instance['query_completions'] = {'enabled': False}
    return instance


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


def _get_clickhouse_client(instance_config):
    return clickhouse_connect.get_client(
        host=instance_config['server'],
        port=instance_config['port'],
        username=instance_config['username'],
        password=instance_config['password'],
    )


@pytest.mark.parametrize("query", SAMPLE_QUERIES)
def test_statement_metrics(aggregator, dbm_instance, dd_run_check, datadog_agent, query):
    """
    Run a known query against ClickHouse, then verify that:
    1. The metrics pipeline collects it from system.query_log with the correct query_signature
    2. All numeric metric columns are present with correct types
    3. A matching FQT (Full Query Text) event is emitted with the same query_signature
    4. The FQT event has the correct structure and metadata
    """
    check = ClickhouseCheck('clickhouse', {}, [dbm_instance])
    client = _get_clickhouse_client(dbm_instance)

    client.command(query)
    client.command('SYSTEM FLUSH LOGS')

    dd_run_check(check)
    dd_run_check(check)

    expected_obfuscated = obfuscate_sql_with_metadata(query, check.statement_metrics._obfuscate_options)['query']

    # -- Verify dbm-metrics --
    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) > 0, "Expected at least one dbm-metrics event"

    event = events[-1]
    assert event['host'] is not None
    assert event['database_instance'] is not None
    assert event['ddagentversion'] == datadog_agent.get_version()
    assert event['timestamp'] > 0
    assert event['min_collection_interval'] is not None
    assert 'tags' in event

    all_rows = []
    for e in events:
        all_rows.extend(e.get('clickhouse_rows', []))

    matching_rows = [r for r in all_rows if r.get('query') == expected_obfuscated]
    assert len(matching_rows) == 1, (
        f"Expected exactly 1 metrics row for query: {query!r}.\n"
        f"Expected obfuscated query: {expected_obfuscated!r}\n"
        f"Found {len(matching_rows)}.\n"
        f"Available queries: {[r.get('query', '<no query>') for r in all_rows]}"
    )

    row = matching_rows[0]
    query_signature = row['query_signature']
    assert row['count'] > 0
    for col in METRICS_COLUMNS:
        assert col in row, f"Missing metric column {col!r} in metrics row"
        assert type(row[col]) in (float, int), f"Metric column {col!r} has unexpected type {type(row[col])}"

    # -- Verify dbm-samples (FQT) --
    sample_events = aggregator.get_event_platform_events("dbm-samples")
    assert len(sample_events) > 0, "Expected at least one dbm-samples event"

    fqt_events = [e for e in sample_events if e.get('dbm_type') == 'fqt']
    assert len(fqt_events) > 0, "Expected at least one FQT event"

    matching_fqt = [e for e in fqt_events if e['db']['query_signature'] == query_signature]
    assert len(matching_fqt) == 1, (
        f"Expected exactly 1 FQT event with query_signature={query_signature}.\n"
        f"Found {len(matching_fqt)}. Available signatures: {[e['db']['query_signature'] for e in fqt_events]}"
    )

    fqt_event = matching_fqt[0]
    assert fqt_event['ddsource'] == 'clickhouse'
    assert fqt_event['dbm_type'] == 'fqt'
    assert fqt_event['db']['statement'] is not None
    assert 'commands' in fqt_event['db']['metadata']
    assert fqt_event['timestamp'] > 0
    assert fqt_event['host'] is not None
    assert fqt_event['ddagentversion'] == datadog_agent.get_version()


def test_statement_metrics_with_metadata(aggregator, dbm_instance, dd_run_check, datadog_agent):
    """
    Verify that query metadata (tables, commands) is correctly extracted and present
    in both metrics rows and FQT events.
    """
    check = ClickhouseCheck('clickhouse', {}, [dbm_instance])
    client = _get_clickhouse_client(dbm_instance)

    query = "SELECT name, engine FROM system.databases ORDER BY name"
    client.command(query)
    client.command('SYSTEM FLUSH LOGS')

    expected_obfuscated = obfuscate_sql_with_metadata(query, check.statement_metrics._obfuscate_options)['query']

    def obfuscate_sql(q, options=None):
        if 'system.databases' in q:
            return json.dumps(
                {'query': expected_obfuscated, 'metadata': {'commands': ['SELECT'], 'tables': ['databases']}}
            )
        return json.dumps({'query': q, 'metadata': {}})

    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = obfuscate_sql
        dd_run_check(check)
        dd_run_check(check)

    # Verify metadata in metrics row
    events = aggregator.get_event_platform_events("dbm-metrics")
    all_rows = []
    for e in events:
        all_rows.extend(e.get('clickhouse_rows', []))

    matching = [r for r in all_rows if r.get('query') == expected_obfuscated]
    assert len(matching) >= 1
    row = matching[0]
    query_signature = row['query_signature']
    assert row.get('dd_commands') == ['SELECT']
    assert row.get('dd_tables')

    # Verify metadata in FQT event
    sample_events = aggregator.get_event_platform_events("dbm-samples")
    fqt_events = [e for e in sample_events if e.get('dbm_type') == 'fqt']
    matching_fqt = [e for e in fqt_events if e['db']['query_signature'] == query_signature]
    assert len(matching_fqt) >= 1
    assert matching_fqt[0]['db']['metadata']['commands'] == ['SELECT']


def test_statement_metrics_disabled(instance):
    """Statement metrics are not initialized when query_metrics is disabled."""
    instance_config = deepcopy(instance)
    instance_config['dbm'] = True
    instance_config['query_metrics'] = {'enabled': False}
    check = ClickhouseCheck('clickhouse', {}, [instance_config])
    assert check.statement_metrics is None


def test_statement_metrics_dbm_off(instance):
    """Statement metrics are not initialized when DBM is disabled."""
    instance_config = deepcopy(instance)
    instance_config['dbm'] = False
    check = ClickhouseCheck('clickhouse', {}, [instance_config])
    assert check.statement_metrics is None


def test_query_samples_collected(aggregator, instance, dd_run_check):
    """Query samples (activity snapshots) are collected when DBM is enabled."""
    instance_config = deepcopy(instance)
    instance_config['dbm'] = True
    instance_config['query_samples'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 1,
    }

    check = ClickhouseCheck('clickhouse', {}, [instance_config])
    dd_run_check(check)
    time.sleep(2)
    dd_run_check(check)

    samples_events = aggregator.get_event_platform_events("dbm-activity")
    assert len(samples_events) > 0, "Expected at least one dbm-activity event"


def test_query_samples_disabled(instance):
    """Query samples are not initialized when DBM is disabled."""
    instance_config = deepcopy(instance)
    instance_config['dbm'] = False
    check = ClickhouseCheck('clickhouse', {}, [instance_config])
    assert check.statement_samples is None


def test_dbm_properties(instance):
    """Required DBM properties are correctly set on the check."""
    instance_config = deepcopy(instance)
    instance_config['dbm'] = True
    instance_config['query_samples'] = {'enabled': True}

    check = ClickhouseCheck('clickhouse', {}, [instance_config])
    assert check.reported_hostname is not None
    assert check.database_identifier is not None
    assert check._config.server in check.reported_hostname
    assert str(check._config.port) in check.database_identifier


def test_samples_event_structure(instance):
    """Activity event structure is correct."""
    instance_config = deepcopy(instance)
    instance_config['dbm'] = True
    instance_config['query_samples'] = {'enabled': True}

    check = ClickhouseCheck('clickhouse', {}, [instance_config])
    samples = check.statement_samples
    samples._tags_no_db = ['test:clickhouse', 'server:localhost']

    rows = [
        {
            'elapsed': 0.1,
            'query_id': 'test-query-id',
            'query': 'SELECT * FROM system.tables',
            'statement': 'SELECT * FROM system.tables',
            'query_signature': 'test-signature',
            'user': 'datadog',
            'read_rows': 10,
            'memory_usage': 2048,
            'current_database': 'default',
        }
    ]
    active_connections = [{'user': 'default', 'query_kind': 'Select', 'current_database': 'default', 'connections': 1}]

    with mock.patch('datadog_checks.clickhouse.statement_samples.datadog_agent') as mock_agent:
        mock_agent.get_version.return_value = '7.64.0'
        event = samples._create_samples_event(rows, active_connections)

    assert event['ddsource'] == 'clickhouse'
    assert event['dbm_type'] == 'activity'
    assert 'host' in event
    assert 'database_instance' in event
    assert 'timestamp' in event
    assert 'clickhouse_activity' in event
    assert 'clickhouse_connections' in event


def test_query_completions_data(aggregator, instance, dd_run_check, datadog_agent):
    """
    Run a known query, then verify the completions pipeline collects it:
    1. A dbm-activity event with dbm_type='query_completion' is emitted
    2. The payload contains a completion record matching the known query
    3. Key fields (query_signature, duration_ms, username, read_rows,
       event_time_microseconds) are populated
    """
    instance_config = deepcopy(instance)
    instance_config['dbm'] = True
    instance_config['query_metrics'] = {'enabled': False}
    instance_config['query_samples'] = {'enabled': False}
    instance_config['query_completions'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 10,
    }

    check = ClickhouseCheck('clickhouse', {}, [instance_config])
    client = _get_clickhouse_client(instance_config)

    query = "SELECT name, engine FROM system.databases ORDER BY name"
    client.command(query)
    client.command('SYSTEM FLUSH LOGS')

    dd_run_check(check)
    dd_run_check(check)

    events = aggregator.get_event_platform_events("dbm-activity")
    completion_events = [e for e in events if e.get('dbm_type') == 'query_completion']
    assert len(completion_events) > 0, "Expected at least one query_completion event"

    all_completions = []
    for e in completion_events:
        all_completions.extend(e.get('clickhouse_query_completions', []))

    assert len(all_completions) > 0, "Expected at least one completion record in payload"

    expected_obfuscated = obfuscate_sql_with_metadata(query, check.query_completions._obfuscate_options)['query']
    matching = [c for c in all_completions if c.get('query_details', {}).get('statement') == expected_obfuscated]
    assert len(matching) >= 1, (
        f"Expected at least 1 completion record for query: {query!r}.\n"
        f"Expected obfuscated: {expected_obfuscated!r}\n"
        f"Available statements: {[c.get('query_details', {}).get('statement', '<none>') for c in all_completions]}"
    )

    details = matching[0]['query_details']
    assert details['query_signature'] is not None
    assert details['duration_ms'] >= 0
    assert details['username'] is not None
    assert details['read_rows'] >= 0
    assert details['event_time_microseconds'] > 0


def test_query_samples_data(aggregator, instance, dd_run_check):
    """
    Start a long-running query in the background so it appears in system.processes,
    then verify the samples pipeline actually captures active query rows:
    1. A dbm-activity event with dbm_type='activity' is emitted
    2. clickhouse_activity contains at least one row (not empty)
    3. The slow query is present in the captured activity

    This test specifically guards against regressions on versions that lack
    query_kind in system.processes — on those versions the query silently fails
    and clickhouse_activity is empty.
    """
    instance_config = deepcopy(instance)
    instance_config['dbm'] = True
    instance_config['query_metrics'] = {'enabled': False}
    instance_config['query_samples'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 1,
    }
    instance_config['query_completions'] = {'enabled': False}

    check = ClickhouseCheck('clickhouse', {}, [instance_config])
    client = _get_clickhouse_client(instance_config)

    slow_query = "SELECT sleep(2)"
    thread = threading.Thread(target=client.command, args=(slow_query,), daemon=True)
    thread.start()

    time.sleep(1)

    dd_run_check(check)

    thread.join(timeout=5)

    activity_events = aggregator.get_event_platform_events("dbm-activity")
    sample_events = [e for e in activity_events if e.get('dbm_type') == 'activity']
    assert len(sample_events) > 0, "Expected at least one activity event"

    all_activity = []
    for e in sample_events:
        all_activity.extend(e.get('clickhouse_activity', []))

    assert len(all_activity) > 0, (
        "Expected clickhouse_activity to contain active query rows but it was empty. "
        "This likely means the query_kind column is missing in system.processes."
    )

    statements = [row.get('statement', '') for row in all_activity]
    assert any('sleep' in s for s in statements), (
        f"Expected to find the slow 'sleep' query in activity rows.\nCaptured statements: {statements}"
    )


def test_query_errors_data(aggregator, instance, dd_run_check):
    """
    Execute a failing query, then verify the query errors pipeline captures it:
    1. A dbm-activity event with dbm_type='query_error' is emitted
    2. The payload contains an error record for the failing query
    3. Key error fields (exception, exception_code, stack_trace) are populated
    """
    instance_config = deepcopy(instance)
    instance_config['dbm'] = True
    instance_config['query_metrics'] = {'enabled': False}
    instance_config['query_samples'] = {'enabled': False}
    instance_config['query_completions'] = {'enabled': False}
    instance_config['query_errors'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 10,
    }

    check = ClickhouseCheck('clickhouse', {}, [instance_config])
    client = _get_clickhouse_client(instance_config)

    try:
        client.command("SELECT * FROM nonexistent_table_query_error_test")
    except Exception:
        pass  # Expected to fail

    client.command('SYSTEM FLUSH LOGS')

    dd_run_check(check)
    dd_run_check(check)

    events = aggregator.get_event_platform_events("dbm-activity")
    error_events = [e for e in events if e.get('dbm_type') == 'query_error']
    assert len(error_events) > 0, "Expected at least one query_error event"

    all_errors = []
    for e in error_events:
        all_errors.extend(e.get('clickhouse_query_errors', []))

    assert len(all_errors) > 0, "Expected at least one error record in payload"

    details = all_errors[0]['query_details']
    assert details['query_signature'] is not None
    assert 'nonexistent_table_query_error_test' in details['exception']
    assert 'UNKNOWN_TABLE' in details['exception']
    assert details['exception_code'] == 60
    assert 'stack_trace' in details
