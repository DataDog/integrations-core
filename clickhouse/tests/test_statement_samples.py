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
    assert 'query_id' in ACTIVE_QUERIES_QUERY
    assert 'query' in ACTIVE_QUERIES_QUERY
    assert 'elapsed' in ACTIVE_QUERIES_QUERY
    assert 'memory_usage' in ACTIVE_QUERIES_QUERY


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
