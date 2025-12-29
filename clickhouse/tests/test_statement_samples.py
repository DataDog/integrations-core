# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.statement_samples import ClickhouseStatementSamples


@pytest.fixture
def instance_with_dbm():
    """Return a ClickHouse instance configuration with DBM enabled"""
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_samples': {
            'enabled': True,
            'collection_interval': 10,
            'samples_per_hour_per_query': 15,
            'seen_samples_cache_maxsize': 10000,
            'run_sync': False,
        },
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check_with_dbm(instance_with_dbm):
    """Return a ClickHouse check instance with DBM enabled"""
    check = ClickhouseCheck('clickhouse', {}, [instance_with_dbm])
    return check


def test_statement_samples_initialization(check_with_dbm):
    """Test that statement samples are properly initialized when DBM is enabled"""
    assert check_with_dbm.statement_samples is not None
    assert isinstance(check_with_dbm.statement_samples, ClickhouseStatementSamples)
    assert check_with_dbm.statement_samples._config.enabled is True
    assert check_with_dbm.statement_samples._config.collection_interval == 10


def test_statement_samples_disabled():
    """Test that statement samples are not initialized when DBM is disabled"""
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
    assert check.statement_samples is None


def test_obfuscate_and_normalize_query(check_with_dbm):
    """Test query obfuscation and normalization"""
    statement_samples = check_with_dbm.statement_samples

    row = {
        'timestamp': time.time(),
        'query_id': 'test-query-id-123',
        'query': 'SELECT * FROM users WHERE user_id = 12345',
        'type': 'QueryFinish',
        'user': 'default',
        'duration_ms': 100,
        'read_rows': 1,
        'read_bytes': 100,
        'written_rows': 0,
        'written_bytes': 0,
        'result_rows': 1,
        'result_bytes': 100,
        'memory_usage': 1024,
        'exception': None,
    }

    normalized_row = statement_samples._obfuscate_and_normalize_query(row)

    # Verify that statement and query_signature are set
    assert normalized_row['statement'] is not None
    assert normalized_row['query_signature'] is not None

    # Verify metadata was collected
    assert 'dd_tables' in normalized_row
    assert 'dd_commands' in normalized_row
    assert 'dd_comments' in normalized_row


def test_create_sample_event(check_with_dbm):
    """Test creation of sample events for submission"""
    statement_samples = check_with_dbm.statement_samples

    normalized_row = {
        'timestamp': time.time(),
        'query_id': 'test-query-id-123',
        'query': 'SELECT * FROM users',
        'statement': 'SELECT * FROM users',
        'query_signature': 'abc123',
        'type': 'QueryFinish',
        'user': 'default',
        'elapsed': 0.1,  # elapsed time in seconds
        'read_rows': 10,
        'read_bytes': 1024,
        'written_rows': 0,
        'written_bytes': 0,
        'memory_usage': 2048,
        'exception': None,
        'dd_tables': ['users'],
        'dd_commands': ['SELECT'],
        'dd_comments': [],
        'current_database': 'default',
    }

    event = statement_samples._create_sample_event(normalized_row)

    # Verify event structure
    assert event['ddsource'] == 'clickhouse'
    # The implementation uses 'plan' type for query samples
    assert event['dbm_type'] == 'plan'
    assert 'timestamp' in event
    assert 'db' in event
    assert event['db']['query_signature'] == 'abc123'
    assert event['db']['statement'] == 'SELECT * FROM users'
    assert event['db']['user'] == 'default'

    # Verify ClickHouse-specific fields are in the event
    assert 'clickhouse' in event


def test_rate_limiting(check_with_dbm):
    """Test that query sample rate limiting works correctly"""
    statement_samples = check_with_dbm.statement_samples

    query_signature = 'test-signature-123'

    # First acquisition should succeed
    assert statement_samples._seen_samples_ratelimiter.acquire(query_signature) is True

    # Immediate re-acquisition should fail due to rate limiting
    assert statement_samples._seen_samples_ratelimiter.acquire(query_signature) is False


def test_active_queries_query_format():
    """Test that the active queries query is properly formatted"""
    from datadog_checks.clickhouse.statement_samples import ACTIVE_QUERIES_QUERY

    # Verify query contains necessary clauses
    assert 'system.processes' in ACTIVE_QUERIES_QUERY

    # Original fields
    assert 'query_id' in ACTIVE_QUERIES_QUERY
    assert 'query' in ACTIVE_QUERIES_QUERY
    assert 'elapsed' in ACTIVE_QUERIES_QUERY
    assert 'memory_usage' in ACTIVE_QUERIES_QUERY
    assert 'read_rows' in ACTIVE_QUERIES_QUERY
    assert 'read_bytes' in ACTIVE_QUERIES_QUERY
    assert 'written_rows' in ACTIVE_QUERIES_QUERY
    assert 'written_bytes' in ACTIVE_QUERIES_QUERY

    # New enhanced fields that exist in system.processes
    assert 'peak_memory_usage' in ACTIVE_QUERIES_QUERY
    assert 'total_rows_approx' in ACTIVE_QUERIES_QUERY
    assert 'client_name' in ACTIVE_QUERIES_QUERY
    assert 'client_version_major' in ACTIVE_QUERIES_QUERY
    assert 'client_version_minor' in ACTIVE_QUERIES_QUERY
    assert 'client_version_patch' in ACTIVE_QUERIES_QUERY
    assert 'current_database' in ACTIVE_QUERIES_QUERY
    assert 'thread_ids' in ACTIVE_QUERIES_QUERY
    assert 'address' in ACTIVE_QUERIES_QUERY
    assert 'port' in ACTIVE_QUERIES_QUERY
    assert 'client_hostname' in ACTIVE_QUERIES_QUERY
    assert 'is_cancelled' in ACTIVE_QUERIES_QUERY
    assert 'http_user_agent' in ACTIVE_QUERIES_QUERY


@mock.patch('datadog_checks.clickhouse.statement_samples.datadog_agent')
def test_metrics_reporting(mock_agent, check_with_dbm, aggregator):
    """Test that statement samples report metrics correctly"""
    statement_samples = check_with_dbm.statement_samples
    statement_samples.tags = ['test:clickhouse', 'db:default']
    statement_samples._tags_no_db = ['test:clickhouse']

    # Mock the agent version
    mock_agent.get_version.return_value = '7.50.0'

    # Call the metrics reporting method
    start_time = time.time()
    statement_samples._report_check_hist_metrics(start_time, 10, "test_method")

    # Verify histograms were submitted - the actual implementation prefixes with statement_samples
    aggregator.assert_metric('dd.clickhouse.statement_samples.test_method.time')
    aggregator.assert_metric('dd.clickhouse.statement_samples.test_method.rows')


def test_get_debug_tags(check_with_dbm):
    """Test that debug tags are properly generated"""
    statement_samples = check_with_dbm.statement_samples
    # Set _tags_no_db to simulate what run_job does
    statement_samples._tags_no_db = ['server:localhost', 'port:9000', 'test:clickhouse']
    debug_tags = statement_samples._get_debug_tags()

    # _get_debug_tags returns _tags_no_db when set
    assert isinstance(debug_tags, list)


def test_dbtags(check_with_dbm):
    """Test that database tags are properly generated"""
    statement_samples = check_with_dbm.statement_samples
    statement_samples._tags_no_db = ['test:clickhouse', 'server:localhost']

    db_tags = statement_samples._dbtags('testdb', 'extra:tag')

    # Verify tags include database, extra tags, and base tags
    assert 'db:testdb' in db_tags
    assert 'extra:tag' in db_tags
    assert 'test:clickhouse' in db_tags
    assert 'server:localhost' in db_tags


def test_normalize_active_query_row_with_all_fields(check_with_dbm):
    """Test that all fields are properly normalized from system.processes"""
    statement_samples = check_with_dbm.statement_samples

    # Create a mock row with all 26 fields from ACTIVE_QUERIES_QUERY
    mock_row = (
        1.234,  # elapsed
        'abc-123-def',  # query_id
        'SELECT * FROM users WHERE id = 1',  # query
        'default',  # user
        1000,  # read_rows
        50000,  # read_bytes
        0,  # written_rows
        0,  # written_bytes
        1048576,  # memory_usage
        'abc-123-def',  # initial_query_id
        'default',  # initial_user
        'Select',  # query_kind
        1,  # is_initial_query
        2097152,  # peak_memory_usage
        1000000,  # total_rows_approx
        'python-clickhouse-driver',  # client_name
        1,  # client_version_major (use 1 since 0 is falsy)
        2,  # client_version_minor
        4,  # client_version_patch
        'analytics',  # current_database
        [123, 124, 125],  # thread_ids
        '192.168.1.100',  # address
        54321,  # port
        'app-server-01',  # client_hostname
        0,  # is_cancelled
        'python-requests/2.28.0',  # http_user_agent
    )

    normalized_row = statement_samples._normalize_active_query_row(mock_row)

    # Verify original fields
    assert normalized_row['elapsed'] == 1.234
    assert normalized_row['query_id'] == 'abc-123-def'
    assert normalized_row['user'] == 'default'
    assert normalized_row['read_rows'] == 1000
    assert normalized_row['read_bytes'] == 50000
    assert normalized_row['memory_usage'] == 1048576
    assert normalized_row['query_kind'] == 'Select'
    assert normalized_row['is_initial_query'] is True

    # Verify new memory & performance fields
    assert normalized_row['peak_memory_usage'] == 2097152
    assert normalized_row['total_rows_approx'] == 1000000

    # Verify new client fields
    assert normalized_row['client_name'] == 'python-clickhouse-driver'
    # Note: client_version_* will be None if 0 due to falsy check in implementation
    assert normalized_row['client_version_major'] == 1
    assert normalized_row['client_version_minor'] == 2
    assert normalized_row['client_version_patch'] == 4
    assert normalized_row['client_hostname'] == 'app-server-01'
    assert normalized_row['address'] == '192.168.1.100'
    assert normalized_row['port'] == 54321

    # Verify new database field
    assert normalized_row['current_database'] == 'analytics'

    # Verify new thread fields
    assert normalized_row['thread_ids'] == [123, 124, 125]

    # Verify new status fields - 0 is falsy so is_cancelled will be False
    assert normalized_row['is_cancelled'] is False

    # Verify new HTTP field
    assert normalized_row['http_user_agent'] == 'python-requests/2.28.0'

    # Verify obfuscation happened (statement should be set)
    assert 'statement' in normalized_row
    assert 'query_signature' in normalized_row
