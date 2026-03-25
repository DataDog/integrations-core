# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.query_errors import ClickhouseQueryErrors

pytestmark = pytest.mark.unit


@pytest.fixture
def instance_with_dbm():
    """Return a ClickHouse instance configuration with DBM and query errors enabled"""
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_errors': {
            'enabled': True,
            'collection_interval': 10,
            'samples_per_hour_per_query': 60,
            'seen_samples_cache_maxsize': 10000,
            'max_samples_per_collection': 1000,
            'run_sync': False,
        },
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check_with_dbm(instance_with_dbm):
    """Return a ClickHouse check instance with DBM enabled"""
    return ClickhouseCheck('clickhouse', {}, [instance_with_dbm])


def test_query_errors_initialization(check_with_dbm):
    """Test that query errors are properly initialized when DBM is enabled"""
    assert check_with_dbm.query_errors is not None
    assert isinstance(check_with_dbm.query_errors, ClickhouseQueryErrors)
    assert check_with_dbm.query_errors._config.enabled is True
    assert check_with_dbm.query_errors._config.collection_interval == 10
    assert check_with_dbm.query_errors._config.samples_per_hour_per_query == 60


def test_query_errors_disabled():
    """Test that query errors are not initialized when disabled"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_errors': {
            'enabled': False,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    assert check.query_errors is None


def test_dbm_disabled_no_query_errors():
    """Test that query errors are not initialized when DBM is disabled"""
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
    assert check.query_errors is None


def test_normalize_query(check_with_dbm):
    """Test query obfuscation and normalization for error rows"""
    query_errors = check_with_dbm.query_errors

    row = {
        'query_id': 'test-error-query-id-123',
        'query': 'SELECT * FROM nonexistent_table WHERE id = 12345',
        'event_time_microseconds': int(time.time() * 1_000_000),
        'query_start_time_microseconds': int(time.time() * 1_000_000) - 100000,
        'query_duration_ms': 0.0,
        'read_rows': 0,
        'read_bytes': 0,
        'written_rows': 0,
        'written_bytes': 0,
        'result_rows': 0,
        'result_bytes': 0,
        'memory_usage': 0,
        'user': 'default',
        'exception': 'Table default.nonexistent_table does not exist. (UNKNOWN_TABLE)',
        'exception_code': 60,
        'stack_trace': 'DB::Exception::Exception at 0x...',
    }

    normalized_row = query_errors._normalize_query(row)

    assert normalized_row['statement'] is not None
    assert normalized_row['query_signature'] is not None
    assert 'dd_tables' in normalized_row
    assert 'dd_commands' in normalized_row
    assert 'dd_comments' in normalized_row


def test_create_batched_payload_error_fields(check_with_dbm):
    """Test that batched payload includes exception, exception_code, and stack_trace"""
    query_errors = check_with_dbm.query_errors
    query_errors._tags_no_db = ['test:clickhouse']

    rows = [
        {
            'query_id': 'err-query-id-456',
            'statement': 'SELECT * FROM nonexistent_table WHERE id = ?',
            'query_signature': 'err123def456',
            'query_duration_ms': 0.0,
            'databases': 'default',
            'user': 'default_user',
            'read_rows': 0,
            'read_bytes': 0,
            'written_rows': 0,
            'written_bytes': 0,
            'result_rows': 0,
            'result_bytes': 0,
            'memory_usage': 0,
            'event_time_microseconds': 1746205423150500,
            'query_start_time_microseconds': 1746205423000000,
            'initial_query_id': 'err-query-id-456',
            'query_kind': 'Select',
            'is_initial_query': True,
            'exception': 'Table default.nonexistent_table does not exist. (UNKNOWN_TABLE)',
            'exception_code': 60,
            'stack_trace': 'DB::Exception::Exception at 0x1234...',
            'dd_tables': ['nonexistent_table'],
            'dd_commands': ['SELECT'],
            'dd_comments': [],
        }
    ]

    with mock.patch('datadog_checks.clickhouse.query_errors.datadog_agent') as mock_agent:
        mock_agent.get_version.return_value = '7.64.0'
        payload = query_errors._create_batched_payload(rows)

    assert payload is not None
    assert len(payload['clickhouse_query_errors']) == 1

    query_details = payload['clickhouse_query_errors'][0]['query_details']
    assert query_details['exception'] == 'Table default.nonexistent_table does not exist. (UNKNOWN_TABLE)'
    assert query_details['exception_code'] == 60
    assert query_details['stack_trace'] == 'DB::Exception::Exception at 0x1234...'


def test_create_batched_payload_structure(check_with_dbm):
    """Test that payload uses dbm_type=query_errors and key=clickhouse_query_errors"""
    query_errors = check_with_dbm.query_errors
    query_errors._tags_no_db = ['test:clickhouse', 'server:localhost']

    rows = [
        {
            'statement': 'SELECT * FROM nonexistent_table',
            'query_signature': 'abc123',
            'query_duration_ms': 0.0,
            'databases': 'default',
            'user': 'default',
            'exception': 'Table does not exist.',
            'exception_code': 60,
            'stack_trace': '',
        },
    ]

    with mock.patch('datadog_checks.clickhouse.query_errors.datadog_agent') as mock_agent:
        mock_agent.get_version.return_value = '7.64.0'
        payload = query_errors._create_batched_payload(rows)

    assert payload['ddsource'] == 'clickhouse'
    assert payload['dbm_type'] == 'query_error'
    assert 'clickhouse_query_errors' in payload
    assert 'timestamp' in payload
    assert 'host' in payload
    assert 'database_instance' in payload


def test_query_errors_sql_query_format():
    """Test that the SQL query template uses correct filters for error types."""
    from datadog_checks.clickhouse.query_errors import QUERY_ERRORS_QUERY

    # Structural placeholders (str.replace())
    assert '{checkpoint_filter}' in QUERY_ERRORS_QUERY
    assert '{query_log_table}' in QUERY_ERRORS_QUERY

    # Bound parameters (ClickHouse server-side)
    assert '{min_checkpoint_us:UInt64}' in QUERY_ERRORS_QUERY
    assert '{max_samples:UInt64}' in QUERY_ERRORS_QUERY

    # hostName() for per-node checkpoint tracking
    assert 'hostName() as server_node' in QUERY_ERRORS_QUERY

    # Error type filter (not QueryFinish)
    assert "type IN ('ExceptionBeforeStart', 'ExceptionWhileProcessing')" in QUERY_ERRORS_QUERY

    # Error-specific fields
    assert 'exception' in QUERY_ERRORS_QUERY
    assert 'exception_code' in QUERY_ERRORS_QUERY
    assert 'stack_trace' in QUERY_ERRORS_QUERY

    # Standard query fields
    assert 'query_id' in QUERY_ERRORS_QUERY
    assert 'memory_usage' in QUERY_ERRORS_QUERY
    assert 'event_time_microseconds' in QUERY_ERRORS_QUERY


def test_rate_limiting(check_with_dbm):
    """Test that query error rate limiting works correctly"""
    query_errors = check_with_dbm.query_errors

    query_cache_key = ('error-signature-123', 'default', 'default_user')

    assert query_errors._seen_samples_ratelimiter.acquire(query_cache_key) is True
    assert query_errors._seen_samples_ratelimiter.acquire(query_cache_key) is False


def test_default_config_values():
    """Test that default configuration values are applied correctly for query errors"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_errors': {
            'enabled': True,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    assert check.query_errors._config.collection_interval == 10
    assert check.query_errors._config.samples_per_hour_per_query == 60
    assert check.query_errors._config.seen_samples_cache_maxsize == 10000
    assert check.query_errors._config.max_samples_per_collection == 1000


def test_separate_checkpoint_key(check_with_dbm):
    """Test that query errors use a separate checkpoint cache key from completions"""
    assert check_with_dbm.query_errors.CHECKPOINT_CACHE_KEY == "query_errors_last_checkpoint_microseconds"
    assert check_with_dbm.query_errors.CHECKPOINT_CACHE_KEY != check_with_dbm.query_completions.CHECKPOINT_CACHE_KEY
