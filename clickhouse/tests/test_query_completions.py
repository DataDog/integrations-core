# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.query_completions import DBM_TYPE_FLUSH, ClickhouseQueryCompletions

pytestmark = pytest.mark.unit


@pytest.fixture
def instance_with_dbm():
    """Return a ClickHouse instance configuration with DBM and query completions enabled"""
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_completions': {
            'enabled': True,
            'collection_interval': 10,
            'samples_per_hour_per_query': 15,
            'seen_samples_cache_maxsize': 10000,
            'max_samples_per_collection': 1000,
            'run_sync': False,
        },
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check_with_dbm(instance_with_dbm):
    """Return a ClickHouse check instance with DBM enabled"""
    check = ClickhouseCheck('clickhouse', {}, [instance_with_dbm])
    return check


def test_query_completions_initialization(check_with_dbm):
    """Test that query completions are properly initialized when DBM is enabled"""
    assert check_with_dbm.query_completions is not None
    assert isinstance(check_with_dbm.query_completions, ClickhouseQueryCompletions)
    assert check_with_dbm.query_completions._config.enabled is True
    assert check_with_dbm.query_completions._config.collection_interval == 10
    assert check_with_dbm.query_completions._config.samples_per_hour_per_query == 15


def test_query_completions_disabled():
    """Test that query completions are not initialized when disabled"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_completions': {
            'enabled': False,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    assert check.query_completions is None


def test_dbm_disabled_no_query_completions():
    """Test that query completions are not initialized when DBM is disabled"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': False,
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    assert check.query_completions is None


def test_normalize_query(check_with_dbm):
    """Test query obfuscation and normalization for completed queries"""
    query_completions = check_with_dbm.query_completions

    row = {
        'query_id': 'test-query-id-123',
        'query': 'SELECT * FROM users WHERE user_id = 12345',
        'event_time_microseconds': int(time.time() * 1_000_000),
        'query_start_time_microseconds': int(time.time() * 1_000_000) - 100000,
        'query_duration_ms': 100.5,
        'read_rows': 1000,
        'read_bytes': 102400,
        'written_rows': 0,
        'written_bytes': 0,
        'result_rows': 100,
        'result_bytes': 10240,
        'memory_usage': 5242880,
        'user': 'default',
        'current_database': 'default',
    }

    normalized_row = query_completions._normalize_query(row)

    # Verify that statement and query_signature are set
    assert normalized_row['statement'] is not None
    assert normalized_row['query_signature'] is not None

    # Verify metadata was collected
    assert 'dd_tables' in normalized_row
    assert 'dd_commands' in normalized_row
    assert 'dd_comments' in normalized_row


def test_create_batched_payload_query_details(check_with_dbm):
    """Test that batched payload creates correct query_details structure"""
    query_completions = check_with_dbm.query_completions
    query_completions._tags_no_db = ['test:clickhouse']

    rows = [
        {
            'query_id': 'test-query-id-123',
            'statement': 'SELECT * FROM users WHERE user_id = ?',
            'query_signature': 'abc123def456',
            'query_duration_ms': 150.5,
            'databases': 'default',
            'user': 'default_user',
            'read_rows': 1000,
            'read_bytes': 102400,
            'written_rows': 0,
            'written_bytes': 0,
            'result_rows': 100,
            'result_bytes': 10240,
            'memory_usage': 5242880,
            'cpu_us': 1872000,
            'cpu_wait_us': 35000,
            'event_time_microseconds': 1746205423150500,
            'query_start_time_microseconds': 1746205423000000,
            'initial_query_id': 'test-query-id-123',
            'query_kind': 'Select',
            'is_initial_query': True,
            'dd_tables': ['users'],
            'dd_commands': ['SELECT'],
            'dd_comments': [],
        }
    ]

    with mock.patch('datadog_checks.clickhouse.query_completions.datadog_agent') as mock_agent:
        mock_agent.get_version.return_value = '7.64.0'
        payload = query_completions._create_batched_payload(rows)

    # Verify payload has completions
    assert payload is not None
    assert len(payload['clickhouse_query_completions']) == 1

    # Verify query_details structure
    query_details = payload['clickhouse_query_completions'][0]['query_details']
    assert query_details['statement'] == 'SELECT * FROM users WHERE user_id = ?'
    assert query_details['query_signature'] == 'abc123def456'
    assert query_details['duration_ms'] == 150.5
    assert query_details['database_name'] == 'default'
    assert query_details['username'] == 'default_user'
    assert query_details['query_id'] == 'test-query-id-123'
    assert query_details['read_rows'] == 1000
    assert query_details['memory_usage'] == 5242880
    assert query_details['cpu_us'] == 1872000
    assert query_details['cpu_wait_us'] == 35000

    # Verify metadata is included
    assert query_details['metadata']['tables'] == ['users']
    assert query_details['metadata']['commands'] == ['SELECT']


def test_create_batched_payload_structure(check_with_dbm):
    """Test creation of batched query completion payload structure"""
    query_completions = check_with_dbm.query_completions
    query_completions._tags_no_db = ['test:clickhouse', 'server:localhost']

    rows = [
        {
            'statement': 'SELECT * FROM users',
            'query_signature': 'abc123',
            'query_duration_ms': 100.0,
            'databases': 'default',
            'user': 'default',
        },
        {
            'statement': 'INSERT INTO events VALUES (?)',
            'query_signature': 'xyz789',
            'query_duration_ms': 250.0,
            'databases': 'analytics',
            'user': 'analytics_user',
        },
    ]

    with mock.patch('datadog_checks.clickhouse.query_completions.datadog_agent') as mock_agent:
        mock_agent.get_version.return_value = '7.64.0'
        payload = query_completions._create_batched_payload(rows)

    # Verify payload structure
    assert payload['ddsource'] == 'clickhouse'
    assert payload['dbm_type'] == 'query_completion'
    assert 'timestamp' in payload
    assert 'host' in payload
    assert 'database_instance' in payload

    # Verify query completions array
    assert len(payload['clickhouse_query_completions']) == 2
    assert payload['clickhouse_query_completions'][0]['query_details']['statement'] == 'SELECT * FROM users'
    assert payload['clickhouse_query_completions'][1]['query_details']['statement'] == 'INSERT INTO events VALUES (?)'


@pytest.mark.parametrize('service', [None, 'test-clickhouse-service'])
def test_create_batched_payload_service_field(check_with_dbm, service):
    """The completions payload carries the configured service, or None when unset."""
    check_with_dbm._config = check_with_dbm._config.model_copy(update={'service': service})

    rows = [
        {
            'statement': 'SELECT * FROM users',
            'query_signature': 'abc123',
            'query_duration_ms': 100.0,
            'databases': 'default',
            'user': 'default',
        },
    ]

    with mock.patch('datadog_checks.clickhouse.query_completions.datadog_agent') as mock_agent:
        mock_agent.get_version.return_value = '7.64.0'
        payload = check_with_dbm.query_completions._create_batched_payload(rows)

    assert payload['service'] == service


def test_rate_limiting(check_with_dbm):
    """Test that query sample rate limiting works correctly"""
    query_completions = check_with_dbm.query_completions

    query_cache_key = ('test-signature-123', 'default', 'default_user')

    # First acquisition should succeed
    assert query_completions._seen_samples_ratelimiter.acquire(query_cache_key) is True

    # Immediate re-acquisition should fail due to rate limiting
    assert query_completions._seen_samples_ratelimiter.acquire(query_cache_key) is False


def test_completed_queries_query_format():
    """Test that the query template uses server-side parameter binding for data values."""
    from datadog_checks.clickhouse.query_completions import COMPLETED_QUERIES_QUERY

    # Structural placeholders (str.replace())
    assert '{checkpoint_filter}' in COMPLETED_QUERIES_QUERY
    assert '{query_log_table}' in COMPLETED_QUERIES_QUERY

    # Bound parameters (ClickHouse server-side)
    assert '{min_checkpoint_us:UInt64}' in COMPLETED_QUERIES_QUERY
    assert '{max_samples:UInt64}' in COMPLETED_QUERIES_QUERY

    # hostName() is always included for per-node checkpoint tracking
    assert 'hostName() as server_node' in COMPLETED_QUERIES_QUERY

    # Filters
    assert "type = 'QueryFinish'" in COMPLETED_QUERIES_QUERY
    assert 'event_time_microseconds <= now64(6)' in COMPLETED_QUERIES_QUERY

    # Key fields
    assert 'query_id' in COMPLETED_QUERIES_QUERY
    assert 'query_duration_ms' in COMPLETED_QUERIES_QUERY
    assert 'read_rows' in COMPLETED_QUERIES_QUERY
    assert 'read_bytes' in COMPLETED_QUERIES_QUERY
    assert 'written_rows' in COMPLETED_QUERIES_QUERY
    assert 'written_bytes' in COMPLETED_QUERIES_QUERY
    assert 'memory_usage' in COMPLETED_QUERIES_QUERY
    assert 'event_time_microseconds' in COMPLETED_QUERIES_QUERY
    assert 'query_start_time_microseconds' in COMPLETED_QUERIES_QUERY

    # CPU fields read from the ProfileEvents map
    assert "ProfileEvents['OSCPUVirtualTimeMicroseconds']" in COMPLETED_QUERIES_QUERY
    assert "ProfileEvents['OSCPUWaitMicroseconds']" in COMPLETED_QUERIES_QUERY


def test_normalize_query_with_obfuscation(check_with_dbm):
    """Test that query normalization properly obfuscates and extracts metadata"""
    query_completions = check_with_dbm.query_completions

    row = {
        'query_id': 'id-1',
        'query': 'SELECT * FROM users WHERE id = 123',
        'event_time_microseconds': int(time.time() * 1_000_000),
        'query_start_time_microseconds': int(time.time() * 1_000_000) - 100000,
        'query_duration_ms': 50.0,
        'read_rows': 100,
        'read_bytes': 10240,
        'user': 'default',
    }

    normalized_row = query_completions._normalize_query(row)

    # Should return a normalized row
    assert normalized_row is not None

    # Verify the row was properly normalized
    assert 'statement' in normalized_row
    assert 'query_signature' in normalized_row
    assert normalized_row['statement'] is not None
    assert normalized_row['query_signature'] is not None


@mock.patch('datadog_checks.clickhouse.query_completions.datadog_agent')
def test_checkpoint_persistence(mock_agent, check_with_dbm):
    """Test checkpoint save and load functionality"""
    query_completions = check_with_dbm.query_completions

    # Test saving checkpoint
    test_checkpoint = 1234567890123456
    query_completions._save_checkpoint(test_checkpoint)

    # Mock persistent cache
    check_with_dbm.read_persistent_cache = mock.MagicMock(return_value=str(test_checkpoint))

    # Load checkpoint (uses _get_last_checkpoint which reads from persistent cache)
    loaded_checkpoint = check_with_dbm.read_persistent_cache(query_completions.CHECKPOINT_CACHE_KEY)

    assert int(loaded_checkpoint) == test_checkpoint


def test_default_config_values():
    """Test that default configuration values are applied correctly"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_completions': {
            'enabled': True,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Verify defaults are applied
    assert check.query_completions._config.collection_interval == 10
    assert check.query_completions._config.samples_per_hour_per_query == 15
    assert check.query_completions._config.seen_samples_cache_maxsize == 10000
    assert check.query_completions._config.max_samples_per_collection == 1000


# Async insert flush log collection tests
@pytest.fixture
def instance_with_flush():
    """Return a ClickHouse instance configuration with the async insert flush log enabled"""
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'service': 'test-clickhouse-service',
        'query_completions': {'enabled': True, 'collection_interval': 10},
        'async_insert_flushes': {'enabled': True, 'collection_interval': 15, 'max_samples_per_collection': 500},
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check_with_flush(instance_with_flush):
    """Return a ClickHouse check instance with the async insert flush log enabled"""
    check = ClickhouseCheck('clickhouse', {}, [instance_with_flush])
    return check


def test_flush_log_initialization(check_with_flush):
    """Test that flush collection is set up with its own interval and checkpoint when enabled"""
    from datadog_checks.clickhouse.query_completions import FLUSH_CHECKPOINT_CACHE_KEY

    query_completions = check_with_flush.query_completions
    assert query_completions._flush_enabled is True
    assert query_completions._flush_collection_interval == 15
    assert query_completions._flush_max_rows == 500
    assert query_completions._flush_checkpoint is not None
    assert query_completions._flush_checkpoint._cache_key == FLUSH_CHECKPOINT_CACHE_KEY


def test_flush_log_disabled_by_default(check_with_dbm):
    """Test that flush collection is disabled and never runs when there is no flush config"""
    query_completions = check_with_dbm.query_completions
    assert query_completions._flush_enabled is False

    with mock.patch.object(query_completions, '_collect_and_submit_flush') as mock_collect:
        query_completions._collect_flush()
        mock_collect.assert_not_called()


def test_flush_only_enables_job_and_skips_completions():
    """Test that the shared job runs for the flush log when query completions is disabled"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_completions': {'enabled': False, 'collection_interval': 10},
        'async_insert_flushes': {'enabled': True, 'collection_interval': 15},
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    query_completions = check.query_completions

    # The shared job must be enabled so its loop runs and reaches flush collection.
    assert query_completions._enabled is True
    assert query_completions._flush_enabled is True

    # run_job should collect the flush log but skip completed-query collection.
    query_completions._tags = ['test:clickhouse']
    with (
        mock.patch.object(query_completions, '_collect_completed_queries') as mock_completions,
        mock.patch.object(query_completions, '_collect_and_submit_flush') as mock_flush,
    ):
        query_completions.run_job()

    mock_completions.assert_not_called()
    mock_flush.assert_called_once()


def test_collect_flush_runs_on_its_own_interval(check_with_flush):
    """Test that flush collection runs once per its own interval, not on every query-completions tick"""
    query_completions = check_with_flush.query_completions

    with mock.patch.object(query_completions, '_collect_and_submit_flush') as mock_collect:
        query_completions._collect_flush()  # first tick: runs
        query_completions._collect_flush()  # second tick: should not run
        assert mock_collect.call_count == 1


def test_create_flush_event_structure(check_with_flush):
    """Test creation of the async insert flush event payload structure"""
    query_completions = check_with_flush.query_completions
    query_completions._tags_no_db = ['test:clickhouse']

    records = [
        {'database': 'default', 'table': 'events', 'status': 'Ok', 'rows': 1, 'flush_latency_us': 500000},
        {'database': 'default', 'table': 'events', 'status': 'Ok', 'rows': 2, 'flush_latency_us': 250000},
    ]

    with mock.patch('datadog_checks.clickhouse.query_completions.datadog_agent') as mock_agent:
        mock_agent.get_version.return_value = '7.64.0'
        payload = query_completions._create_flush_event(records)

    assert payload['ddsource'] == 'clickhouse'
    assert payload['dbm_type'] == DBM_TYPE_FLUSH
    assert payload['collection_interval'] == query_completions._flush_collection_interval
    assert 'timestamp' in payload
    assert 'host' in payload
    assert 'database_instance' in payload
    assert payload['service'] == 'test-clickhouse-service'
    assert payload['clickhouse_async_insert_flushes'] == records


def test_flush_log_query_format():
    """Test that the flush query uses server-side binding and reads the fields the event needs"""
    from datadog_checks.clickhouse.query_completions import FLUSH_LOG_QUERY

    # Structural placeholders (str.replace())
    assert '{checkpoint_filter}' in FLUSH_LOG_QUERY
    assert '{async_insert_log_table}' in FLUSH_LOG_QUERY

    # Bound parameters (ClickHouse server-side)
    assert '{max_flush_rows:UInt64}' in FLUSH_LOG_QUERY
    assert '{min_checkpoint_us:UInt64}' in FLUSH_LOG_QUERY

    # hostName() is included for per-node checkpoint tracking
    assert 'hostName() AS server_node' in FLUSH_LOG_QUERY

    # Upper bound so the window never runs past "now"
    assert 'event_time_microseconds <= now64(6)' in FLUSH_LOG_QUERY

    # Date bound so ClickHouse can prune old daily partitions
    assert 'event_date >= toDate(fromUnixTimestamp64Micro({min_checkpoint_us:UInt64}))' in FLUSH_LOG_QUERY

    # Fields used to build flush records
    assert 'database' in FLUSH_LOG_QUERY
    assert 'table' in FLUSH_LOG_QUERY
    assert 'format' in FLUSH_LOG_QUERY
    assert 'status' in FLUSH_LOG_QUERY
    assert 'exception' in FLUSH_LOG_QUERY
    assert 'bytes' in FLUSH_LOG_QUERY
    assert 'rows' in FLUSH_LOG_QUERY
    assert 'query_id' in FLUSH_LOG_QUERY
    assert 'query' in FLUSH_LOG_QUERY
    assert 'event_time_microseconds' in FLUSH_LOG_QUERY
    assert 'flush_time_microseconds' in FLUSH_LOG_QUERY


def test_collect_flush_rows(check_with_flush):
    """Test that rows map to flush records, latency clamps to 0 on clock skew, and the node is tracked"""
    query_completions = check_with_flush.query_completions

    # Column order matches FLUSH_LOG_QUERY's SELECT.
    rows = [
        (
            'default',  # database
            'events',  # table
            'Values',  # format
            'Ok',  # status
            '',  # exception
            'node-1',  # server_node
            100,  # bytes
            5,  # rows
            'qid-1',  # query_id
            'INSERT INTO events VALUES',  # query
            1_000_000,  # event_time_microseconds
            1_500_000,  # flush_time_microseconds
        ),
        (
            # flush_time before event_time: cross-node clock skew, latency clamps to 0
            'default',  # database
            'events',  # table
            'Values',  # format
            'Ok',  # status
            '',  # exception
            'node-2',  # server_node
            50,  # bytes
            2,  # rows
            'qid-2',  # query_id
            'INSERT INTO events VALUES',  # query
            2_000_000,  # event_time_microseconds
            1_500_000,  # flush_time_microseconds
        ),
    ]
    obfuscated = {
        'query': 'INSERT INTO events VALUES',
        'query_signature': 'sig-1',
        'dd_tables': ['events'],
        'dd_commands': ['INSERT'],
        'dd_comments': [],
    }

    with (
        mock.patch.object(query_completions._check, 'get_system_table', return_value='system.asynchronous_insert_log'),
        mock.patch.object(
            query_completions._flush_checkpoint, 'build_per_node_checkpoint_filter', return_value=('1=1', 0, {})
        ),
        mock.patch.object(query_completions, '_execute_query', return_value=rows),
        mock.patch.object(query_completions, '_obfuscate_query', return_value=obfuscated),
        mock.patch.object(query_completions._flush_checkpoint, 'track_node_checkpoint') as mock_track,
        mock.patch.object(query_completions._flush_checkpoint, 'set_checkpoint_from_event_time'),
    ):
        records = query_completions._collect_flush_rows()

    assert len(records) == 2
    record = records[0]
    assert record['database'] == 'default'
    assert record['table'] == 'events'
    assert record['status'] == 'Ok'
    assert record['bytes'] == 100
    assert record['rows'] == 5
    assert record['query_id'] == 'qid-1'
    assert record['query_signature'] == 'sig-1'
    assert record['flush_latency_us'] == 500_000  # flush_time - event_time

    # Skewed row: flush_time < event_time (cross-node clock skew) clamps latency to 0
    assert records[1]['flush_latency_us'] == 0

    mock_track.assert_any_call('node-1', 1_000_000)
    mock_track.assert_any_call('node-2', 2_000_000)


def test_flush_advances_checkpoint_on_success(check_with_flush):
    """Test that a successful flush collection advances the checkpoint"""
    query_completions = check_with_flush.query_completions
    query_completions._tags_no_db = ['test:clickhouse']

    with (
        mock.patch.object(query_completions, '_collect_flush_rows', return_value=[{'table': 'events'}]),
        mock.patch.object(query_completions, '_create_flush_event', return_value={'dbm_type': 'async_inserts_flush'}),
        mock.patch.object(query_completions._check, 'database_monitoring_query_activity'),
        mock.patch.object(query_completions._flush_checkpoint, 'reset_pending'),
        mock.patch.object(query_completions._flush_checkpoint, 'advance_checkpoint') as mock_advance,
    ):
        query_completions._collect_and_submit_flush()
        mock_advance.assert_called_once()


def test_flush_does_not_advance_checkpoint_on_error(check_with_flush):
    """Test that a failed load leaves the checkpoint unadvanced so the same window is retried"""
    query_completions = check_with_flush.query_completions

    with (
        mock.patch.object(query_completions, '_collect_flush_rows', side_effect=Exception('load failed')),
        mock.patch.object(query_completions._flush_checkpoint, 'reset_pending'),
        mock.patch.object(query_completions._flush_checkpoint, 'advance_checkpoint') as mock_advance,
    ):
        query_completions._collect_and_submit_flush()
        mock_advance.assert_not_called()


def test_flush_advances_checkpoint_on_empty_window(check_with_flush):
    """Test that an idle window with no rows still advances so the empty range is not rescanned forever"""
    query_completions = check_with_flush.query_completions

    with (
        mock.patch.object(query_completions, '_collect_flush_rows', return_value=[]),
        mock.patch.object(query_completions._flush_checkpoint, 'reset_pending'),
        mock.patch.object(query_completions._flush_checkpoint, 'advance_checkpoint') as mock_advance,
        mock.patch.object(query_completions, '_create_flush_event') as mock_create,
    ):
        query_completions._collect_and_submit_flush()
        mock_advance.assert_called_once()
        mock_create.assert_not_called()
