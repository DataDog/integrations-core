# (C) Datadog, Inc. 2025-present
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

    # Verify that query was obfuscated (literal should be replaced)
    assert normalized_row['statement'] is not None
    assert '12345' not in normalized_row['statement']
    assert normalized_row['query_signature'] is not None

    # Verify metadata was collected
    assert 'dd_tables' in normalized_row
    assert 'dd_commands' in normalized_row
    assert 'dd_comments' in normalized_row


def test_normalize_query_log_row(check_with_dbm):
    """Test normalization of query log rows"""
    statement_samples = check_with_dbm.statement_samples

    # Simulate a row from system.query_log
    row = (
        time.time(),  # event_time
        'test-query-id-123',  # query_id
        'SELECT count(*) FROM system.tables',  # query
        'QueryFinish',  # type
        'default',  # user
        50,  # query_duration_ms
        10,  # read_rows
        1024,  # read_bytes
        0,  # written_rows
        0,  # written_bytes
        1,  # result_rows
        8,  # result_bytes
        2048,  # memory_usage
        None,  # exception
    )

    normalized_row = statement_samples._normalize_query_log_row(row)

    # Verify basic fields
    assert normalized_row['query_id'] == 'test-query-id-123'
    assert normalized_row['user'] == 'default'
    assert normalized_row['type'] == 'QueryFinish'
    assert normalized_row['duration_ms'] == 50
    assert normalized_row['read_rows'] == 10
    assert normalized_row['memory_usage'] == 2048

    # Verify obfuscation occurred
    assert normalized_row['statement'] is not None
    assert normalized_row['query_signature'] is not None


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
        'duration_ms': 100,
        'read_rows': 10,
        'read_bytes': 1024,
        'written_rows': 0,
        'written_bytes': 0,
        'result_rows': 10,
        'result_bytes': 1024,
        'memory_usage': 2048,
        'exception': None,
        'dd_tables': ['users'],
        'dd_commands': ['SELECT'],
        'dd_comments': [],
    }

    event = statement_samples._create_sample_event(normalized_row)

    # Verify event structure
    assert event['ddsource'] == 'clickhouse'
    assert event['dbm_type'] == 'sample'
    assert 'timestamp' in event
    assert 'db' in event
    assert event['db']['query_signature'] == 'abc123'
    assert event['db']['statement'] == 'SELECT * FROM users'
    assert event['db']['user'] == 'default'

    # Verify ClickHouse-specific fields
    assert 'clickhouse' in event
    assert event['clickhouse']['query_id'] == 'test-query-id-123'
    assert event['clickhouse']['duration_ms'] == 100
    assert event['clickhouse']['read_rows'] == 10
    assert event['clickhouse']['memory_usage'] == 2048

    # Verify duration is in nanoseconds
    assert event['duration'] == 100 * 1e6


def test_rate_limiting(check_with_dbm):
    """Test that query sample rate limiting works correctly"""
    statement_samples = check_with_dbm.statement_samples

    query_signature = 'test-signature-123'

    # First acquisition should succeed
    assert statement_samples._seen_samples_ratelimiter.acquire(query_signature) is True

    # Immediate re-acquisition should fail due to rate limiting
    assert statement_samples._seen_samples_ratelimiter.acquire(query_signature) is False


def test_query_log_query_format():
    """Test that the query log query is properly formatted"""
    from datadog_checks.clickhouse.statement_samples import QUERY_LOG_QUERY

    # Verify query contains necessary clauses
    assert 'system.query_log' in QUERY_LOG_QUERY
    assert 'event_time' in QUERY_LOG_QUERY
    assert 'query_id' in QUERY_LOG_QUERY
    assert 'query' in QUERY_LOG_QUERY
    assert 'query_duration_ms' in QUERY_LOG_QUERY
    assert 'WHERE' in QUERY_LOG_QUERY
    assert 'LIMIT' in QUERY_LOG_QUERY


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

    # New enhanced fields
    assert 'peak_memory_usage' in ACTIVE_QUERIES_QUERY
    assert 'total_rows_approx' in ACTIVE_QUERIES_QUERY
    assert 'result_rows' in ACTIVE_QUERIES_QUERY
    assert 'result_bytes' in ACTIVE_QUERIES_QUERY
    assert 'query_start_time' in ACTIVE_QUERIES_QUERY
    assert 'query_start_time_microseconds' in ACTIVE_QUERIES_QUERY
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

    # Verify histograms were submitted
    aggregator.assert_metric('dd.clickhouse.test_method.time')
    aggregator.assert_metric('dd.clickhouse.test_method.rows')


def test_get_debug_tags(check_with_dbm):
    """Test that debug tags are properly generated"""
    statement_samples = check_with_dbm.statement_samples
    debug_tags = statement_samples._get_debug_tags()

    # Verify debug tags contain server information
    assert any('server:' in tag for tag in debug_tags)


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
    """Test that all new fields are properly normalized"""
    statement_samples = check_with_dbm.statement_samples

    # Create a mock row with all fields (31 fields total)
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
        2097152,  # peak_memory_usage (NEW)
        1000000,  # total_rows_approx (NEW)
        1000,  # result_rows (NEW)
        45000,  # result_bytes (NEW)
        '2025-11-07 10:05:01',  # query_start_time (NEW)
        '2025-11-07 10:05:01.123456',  # query_start_time_microseconds (NEW)
        'python-clickhouse-driver',  # client_name (NEW)
        0,  # client_version_major (NEW)
        2,  # client_version_minor (NEW)
        4,  # client_version_patch (NEW)
        'analytics',  # current_database (NEW)
        [123, 124, 125],  # thread_ids (NEW)
        '192.168.1.100',  # address (NEW)
        54321,  # port (NEW)
        'app-server-01',  # client_hostname (NEW)
        0,  # is_cancelled (NEW)
        'python-requests/2.28.0',  # http_user_agent (NEW)
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
    assert normalized_row['result_rows'] == 1000
    assert normalized_row['result_bytes'] == 45000

    # Verify new timing fields
    assert normalized_row['query_start_time'] == '2025-11-07 10:05:01'
    assert normalized_row['query_start_time_microseconds'] == '2025-11-07 10:05:01.123456'

    # Verify new client fields
    assert normalized_row['client_name'] == 'python-clickhouse-driver'
    assert normalized_row['client_version_major'] == 0
    assert normalized_row['client_version_minor'] == 2
    assert normalized_row['client_version_patch'] == 4
    assert normalized_row['client_hostname'] == 'app-server-01'
    assert normalized_row['address'] == '192.168.1.100'
    assert normalized_row['port'] == 54321

    # Verify new database field
    assert normalized_row['current_database'] == 'analytics'

    # Verify new thread fields
    assert normalized_row['thread_ids'] == [123, 124, 125]

    # Verify new status fields
    assert normalized_row['is_cancelled'] is False

    # Verify new HTTP field
    assert normalized_row['http_user_agent'] == 'python-requests/2.28.0'

    # Verify obfuscation happened (statement should be set)
    assert 'statement' in normalized_row
    assert 'query_signature' in normalized_row


