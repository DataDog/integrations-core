# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.completed_query_samples import ClickhouseCompletedQuerySamples

pytestmark = pytest.mark.unit


@pytest.fixture
def instance_with_dbm():
    """Return a ClickHouse instance configuration with DBM and completed query samples enabled"""
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'completed_query_samples': {
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


def test_completed_query_samples_initialization(check_with_dbm):
    """Test that completed query samples are properly initialized when DBM is enabled"""
    assert check_with_dbm.completed_query_samples is not None
    assert isinstance(check_with_dbm.completed_query_samples, ClickhouseCompletedQuerySamples)
    assert check_with_dbm.completed_query_samples._config.enabled is True
    assert check_with_dbm.completed_query_samples._config.collection_interval == 10
    assert check_with_dbm.completed_query_samples._config.samples_per_hour_per_query == 15


def test_completed_query_samples_disabled():
    """Test that completed query samples are not initialized when disabled"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'completed_query_samples': {
            'enabled': False,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    assert check.completed_query_samples is None


def test_dbm_disabled_no_completed_query_samples():
    """Test that completed query samples are not initialized when DBM is disabled"""
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
    assert check.completed_query_samples is None


def test_normalize_query(check_with_dbm):
    """Test query obfuscation and normalization for completed queries"""
    completed_query_samples = check_with_dbm.completed_query_samples

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

    normalized_row = completed_query_samples._normalize_query(row)

    # Verify that statement and query_signature are set
    assert normalized_row['statement'] is not None
    assert normalized_row['query_signature'] is not None

    # Verify metadata was collected
    assert 'dd_tables' in normalized_row
    assert 'dd_commands' in normalized_row
    assert 'dd_comments' in normalized_row


def test_create_batched_payload_query_details(check_with_dbm):
    """Test that batched payload creates correct query_details structure"""
    completed_query_samples = check_with_dbm.completed_query_samples
    completed_query_samples._tags_no_db = ['test:clickhouse']

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
            'peak_memory_usage': 6291456,
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

    with mock.patch('datadog_checks.clickhouse.completed_query_samples.datadog_agent') as mock_agent:
        mock_agent.get_version.return_value = '7.64.0'
        payload = completed_query_samples._create_batched_payload(rows)

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

    # Verify metadata is included
    assert query_details['metadata']['tables'] == ['users']
    assert query_details['metadata']['commands'] == ['SELECT']


def test_create_batched_payload_structure(check_with_dbm):
    """Test creation of batched query completion payload structure"""
    completed_query_samples = check_with_dbm.completed_query_samples
    completed_query_samples._tags_no_db = ['test:clickhouse', 'server:localhost']

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

    with mock.patch('datadog_checks.clickhouse.completed_query_samples.datadog_agent') as mock_agent:
        mock_agent.get_version.return_value = '7.64.0'
        payload = completed_query_samples._create_batched_payload(rows)

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


def test_rate_limiting(check_with_dbm):
    """Test that query sample rate limiting works correctly"""
    completed_query_samples = check_with_dbm.completed_query_samples

    query_cache_key = ('test-signature-123', 'default', 'default_user')

    # First acquisition should succeed
    assert completed_query_samples._seen_samples_ratelimiter.acquire(query_cache_key) is True

    # Immediate re-acquisition should fail due to rate limiting
    assert completed_query_samples._seen_samples_ratelimiter.acquire(query_cache_key) is False


def test_completed_queries_query_format():
    """Test that the completed queries query is properly formatted"""
    from datadog_checks.clickhouse.completed_query_samples import COMPLETED_QUERIES_QUERY

    # Verify query uses placeholder for table (supports both local and cluster-wide queries)
    assert '{query_log_table}' in COMPLETED_QUERIES_QUERY

    # Verify it filters for completed queries only (QueryFinish type)
    assert "type = 'QueryFinish'" in COMPLETED_QUERIES_QUERY

    # Verify it uses checkpoint-based filtering
    assert 'last_checkpoint_microseconds' in COMPLETED_QUERIES_QUERY
    assert 'current_checkpoint_microseconds' in COMPLETED_QUERIES_QUERY

    # Verify key fields are selected
    assert 'query_id' in COMPLETED_QUERIES_QUERY
    assert 'query' in COMPLETED_QUERIES_QUERY
    assert 'query_duration_ms' in COMPLETED_QUERIES_QUERY
    assert 'read_rows' in COMPLETED_QUERIES_QUERY
    assert 'read_bytes' in COMPLETED_QUERIES_QUERY
    assert 'written_rows' in COMPLETED_QUERIES_QUERY
    assert 'written_bytes' in COMPLETED_QUERIES_QUERY
    assert 'memory_usage' in COMPLETED_QUERIES_QUERY
    assert 'peak_memory_usage' in COMPLETED_QUERIES_QUERY
    assert 'event_time_microseconds' in COMPLETED_QUERIES_QUERY
    assert 'query_start_time_microseconds' in COMPLETED_QUERIES_QUERY


def test_normalize_query_with_obfuscation(check_with_dbm):
    """Test that query normalization properly obfuscates and extracts metadata"""
    completed_query_samples = check_with_dbm.completed_query_samples

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

    normalized_row = completed_query_samples._normalize_query(row)

    # Should return a normalized row
    assert normalized_row is not None

    # Verify the row was properly normalized
    assert 'statement' in normalized_row
    assert 'query_signature' in normalized_row
    assert normalized_row['statement'] is not None
    assert normalized_row['query_signature'] is not None


@mock.patch('datadog_checks.clickhouse.completed_query_samples.datadog_agent')
def test_checkpoint_persistence(mock_agent, check_with_dbm):
    """Test checkpoint save and load functionality"""
    completed_query_samples = check_with_dbm.completed_query_samples

    # Test saving checkpoint
    test_checkpoint = 1234567890123456
    completed_query_samples._save_checkpoint(test_checkpoint)

    # Mock persistent cache
    check_with_dbm.read_persistent_cache = mock.MagicMock(return_value=str(test_checkpoint))

    # Load checkpoint
    loaded_checkpoint = completed_query_samples._load_checkpoint()

    assert loaded_checkpoint == test_checkpoint


def test_default_config_values():
    """Test that default configuration values are applied correctly"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'completed_query_samples': {
            'enabled': True,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Verify defaults are applied
    assert check.completed_query_samples._config.collection_interval == 10
    assert check.completed_query_samples._config.samples_per_hour_per_query == 15
    assert check.completed_query_samples._config.seen_samples_cache_maxsize == 10000
    assert check.completed_query_samples._config.max_samples_per_collection == 1000
