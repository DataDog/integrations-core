# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.statements import ClickhouseStatementMetrics, _row_key

pytestmark = pytest.mark.unit


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
        'query_metrics': {
            'enabled': True,
            'collection_interval': 10,
            'run_sync': False,
        },
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check_with_dbm(instance_with_dbm):
    """Return a ClickHouse check instance with DBM enabled"""
    check = ClickhouseCheck('clickhouse', {}, [instance_with_dbm])
    return check


def test_statement_metrics_initialization(check_with_dbm):
    """Test that statement metrics is properly initialized when DBM is enabled"""
    assert check_with_dbm.statement_metrics is not None
    assert isinstance(check_with_dbm.statement_metrics, ClickhouseStatementMetrics)
    assert check_with_dbm.statement_metrics._config.enabled is True
    assert check_with_dbm.statement_metrics._config.collection_interval == 10


def test_statement_metrics_disabled_when_dbm_off():
    """Test that statement metrics is not initialized when DBM is disabled"""
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
    assert check.statement_metrics is None


def test_statement_metrics_disabled_when_query_metrics_disabled():
    """Test that statement metrics is not initialized when query_metrics is disabled"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_metrics': {
            'enabled': False,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    assert check.statement_metrics is None


def test_defaults_applied():
    """Test that default config values are applied correctly"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_metrics': {
            'enabled': True,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Verify defaults are applied
    assert check.statement_metrics._config.collection_interval == 10
    assert check.statement_metrics._config.run_sync is False


def test_normalize_queries(check_with_dbm):
    """Test query normalization and obfuscation"""
    metrics = check_with_dbm.statement_metrics

    rows = [
        {
            'normalized_query_hash': '12345',
            'query': 'SELECT * FROM users WHERE user_id = 12345',
            'user': 'default',
            'query_type': 'Select',
            'exception_code': '',
            'databases': 'default',
            'dd_tables': ['users'],
            'count': 10,
            'total_time': 1000.0,
            'mean_time': 100.0,
            'p50_time': 90.0,
            'p90_time': 150.0,
            'p95_time': 180.0,
            'p99_time': 200.0,
            'result_rows': 100,
            'read_rows': 1000,
            'read_bytes': 50000,
            'written_rows': 0,
            'written_bytes': 0,
            'result_bytes': 5000,
            'memory_usage': 1000000,
            'peak_memory_usage': 1500000,
        }
    ]

    normalized_rows = metrics._normalize_queries(rows)

    assert len(normalized_rows) == 1
    row = normalized_rows[0]

    # Verify normalization happened - query and query_signature should be set
    assert row['query'] is not None
    assert row['query_signature'] is not None
    # Query signature should be a hex string
    assert len(row['query_signature']) > 0

    # Verify dd_tables is preserved (ClickHouse native tables take precedence)
    assert row['dd_tables'] == ['users']

    # Verify metadata was extracted
    assert 'dd_commands' in row
    assert 'dd_comments' in row

    # Verify other fields are preserved
    assert row['count'] == 10
    assert row['total_time'] == 1000.0


def test_row_key():
    """Test that _row_key generates unique keys based on query_signature, user, and databases"""
    row1 = {
        'query_signature': 'abc123',
        'user': 'default',
        'databases': 'mydb',
    }
    row2 = {
        'query_signature': 'abc123',
        'user': 'admin',
        'databases': 'mydb',
    }
    row3 = {
        'query_signature': 'xyz789',
        'user': 'default',
        'databases': 'mydb',
    }

    key1 = _row_key(row1)
    key2 = _row_key(row2)
    key3 = _row_key(row3)

    # Different users should produce different keys
    assert key1 != key2
    # Different query signatures should produce different keys
    assert key1 != key3
    # Same inputs should produce same key
    assert key1 == _row_key(row1)


def test_rows_to_fqt_events(check_with_dbm):
    """Test FQT (Full Query Text) event generation"""
    metrics = check_with_dbm.statement_metrics
    metrics._tags = ['test:clickhouse']
    metrics._tags_no_db = ['test:clickhouse']

    rows = [
        {
            'query_signature': 'sig123',
            'query': 'SELECT * FROM users',
            'user': 'default',
            'databases': 'mydb',
            'dd_tables': ['users'],
            'dd_commands': ['SELECT'],
            'dd_comments': None,
            'normalized_query_hash': 'hash123',
        }
    ]

    events = list(metrics._rows_to_fqt_events(rows))

    assert len(events) == 1
    event = events[0]

    # Verify event structure
    assert event['dbm_type'] == 'fqt'
    assert event['ddsource'] == 'clickhouse'
    assert event['host'] == check_with_dbm.reported_hostname
    assert event['database_instance'] == check_with_dbm.database_identifier

    # Verify db section
    assert event['db']['query_signature'] == 'sig123'
    assert event['db']['statement'] == 'SELECT * FROM users'
    assert event['db']['instance'] == 'mydb'
    assert event['db']['metadata']['tables'] == ['users']
    assert event['db']['metadata']['commands'] == ['SELECT']

    # Verify clickhouse section
    assert event['clickhouse']['user'] == 'default'
    assert event['clickhouse']['normalized_query_hash'] == 'hash123'


def test_fqt_events_caching(check_with_dbm):
    """Test that FQT events are cached and not re-emitted for the same query"""
    metrics = check_with_dbm.statement_metrics
    metrics._tags = ['test:clickhouse']
    metrics._tags_no_db = ['test:clickhouse']

    rows = [
        {
            'query_signature': 'sig123',
            'query': 'SELECT * FROM users',
            'user': 'default',
            'databases': 'mydb',
            'dd_tables': ['users'],
            'dd_commands': ['SELECT'],
            'dd_comments': None,
            'normalized_query_hash': 'hash123',
        }
    ]

    # First call should emit the event
    events1 = list(metrics._rows_to_fqt_events(rows))
    assert len(events1) == 1

    # Second call with same row should NOT emit (cached)
    events2 = list(metrics._rows_to_fqt_events(rows))
    assert len(events2) == 0


def test_get_internal_user_filter(check_with_dbm):
    """Test internal user filter generation"""
    metrics = check_with_dbm.statement_metrics

    filter_str = metrics._get_internal_user_filter()

    # Should always filter out users ending with '-internal'
    assert "user NOT LIKE '%-internal'" in filter_str
    assert filter_str.startswith("AND ")


def test_get_query_metrics_payloads_single_payload(check_with_dbm):
    """Test payload generation with small data (single payload)"""
    metrics = check_with_dbm.statement_metrics

    payload_wrapper = {
        'host': 'localhost',
        'database_instance': 'localhost:9000:default',
        'timestamp': 1234567890000,
        'min_collection_interval': 10,
        'tags': ['test:clickhouse'],
        'ddagentversion': '7.0.0',
        'clickhouse_version': '24.1.0',
    }

    rows = [
        {
            'query_signature': 'sig1',
            'query': 'SELECT 1',
            'count': 10,
            'total_time': 100.0,
        },
        {
            'query_signature': 'sig2',
            'query': 'SELECT 2',
            'count': 20,
            'total_time': 200.0,
        },
    ]

    payloads = metrics._get_query_metrics_payloads(payload_wrapper, rows)

    # Should produce a single payload for small data
    assert len(payloads) == 1

    import json

    payload_data = json.loads(payloads[0])
    assert payload_data['host'] == 'localhost'
    assert len(payload_data['clickhouse_rows']) == 2


def test_collection_interval_custom():
    """Test that custom collection interval is applied"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_metrics': {
            'enabled': True,
            'collection_interval': 30,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    assert check.statement_metrics._config.collection_interval == 30
    assert check.statement_metrics._metrics_collection_interval == 30.0


def test_full_statement_text_cache_config():
    """Test that full statement text cache is configured correctly"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_metrics': {
            'enabled': True,
            'full_statement_text_cache_max_size': 5000,
            'full_statement_text_samples_per_hour_per_query': 2,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Check cache maxsize
    assert check.statement_metrics._full_statement_text_cache.maxsize == 5000


def test_single_endpoint_mode_affects_table_reference(check_with_dbm):
    """Test that single_endpoint_mode affects system table references"""
    # Default mode should use system.query_log
    table_ref = check_with_dbm.get_system_table('query_log')
    assert table_ref == 'system.query_log'


def test_single_endpoint_mode_cluster_query():
    """Test that single_endpoint_mode uses clusterAllReplicas"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'single_endpoint_mode': True,
        'query_metrics': {
            'enabled': True,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Single endpoint mode should use clusterAllReplicas
    table_ref = check.get_system_table('query_log')
    assert "clusterAllReplicas('default', system.query_log)" == table_ref


def test_normalize_queries_handles_obfuscation_failure(check_with_dbm):
    """Test that _normalize_queries gracefully handles obfuscation failures"""
    metrics = check_with_dbm.statement_metrics

    rows = [
        {
            'normalized_query_hash': '12345',
            'query': 'INVALID SQL {{{{',  # Malformed query that may fail obfuscation
            'user': 'default',
            'query_type': 'Select',
            'exception_code': '',
            'databases': 'default',
            'dd_tables': [],
            'count': 1,
            'total_time': 10.0,
            'mean_time': 10.0,
            'p50_time': 10.0,
            'p90_time': 10.0,
            'p95_time': 10.0,
            'p99_time': 10.0,
            'result_rows': 0,
            'read_rows': 0,
            'read_bytes': 0,
            'written_rows': 0,
            'written_bytes': 0,
            'result_bytes': 0,
            'memory_usage': 0,
            'peak_memory_usage': 0,
        },
        {
            'normalized_query_hash': '67890',
            'query': 'SELECT 1',  # Valid query
            'user': 'default',
            'query_type': 'Select',
            'exception_code': '',
            'databases': 'default',
            'dd_tables': [],
            'count': 1,
            'total_time': 5.0,
            'mean_time': 5.0,
            'p50_time': 5.0,
            'p90_time': 5.0,
            'p95_time': 5.0,
            'p99_time': 5.0,
            'result_rows': 1,
            'read_rows': 0,
            'read_bytes': 0,
            'written_rows': 0,
            'written_bytes': 0,
            'result_bytes': 0,
            'memory_usage': 0,
            'peak_memory_usage': 0,
        },
    ]

    # Should not raise an exception, and should return at least the valid query
    normalized_rows = metrics._normalize_queries(rows)

    # The valid query should be included
    assert any(row['query'] is not None for row in normalized_rows)


def test_metrics_row_with_empty_values(check_with_dbm):
    """Test handling of rows with empty/null values"""
    metrics = check_with_dbm.statement_metrics

    rows = [
        {
            'normalized_query_hash': '12345',
            'query': 'SELECT 1',
            'user': '',  # Empty user
            'query_type': None,  # Null type
            'exception_code': None,
            'databases': '',  # Empty database
            'dd_tables': None,  # Null tables
            'count': 0,  # Zero count
            'total_time': 0.0,
            'mean_time': 0.0,
            'p50_time': 0.0,
            'p90_time': 0.0,
            'p95_time': 0.0,
            'p99_time': 0.0,
            'result_rows': 0,
            'read_rows': 0,
            'read_bytes': 0,
            'written_rows': 0,
            'written_bytes': 0,
            'result_bytes': 0,
            'memory_usage': 0,
            'peak_memory_usage': 0,
        }
    ]

    # Should not raise an exception
    normalized_rows = metrics._normalize_queries(rows)

    # Should still produce output
    assert len(normalized_rows) == 1
