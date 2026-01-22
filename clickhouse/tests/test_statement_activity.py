# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.statement_activity import ClickhouseStatementActivity

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
        'query_activity': {
            'enabled': True,
            'collection_interval': 10,
            'payload_row_limit': 1000,
            'run_sync': False,
        },
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check_with_dbm(instance_with_dbm):
    """Return a ClickHouse check instance with DBM enabled"""
    check = ClickhouseCheck('clickhouse', {}, [instance_with_dbm])
    return check


def test_statement_activity_initialization(check_with_dbm):
    """Test that statement activity is properly initialized when DBM is enabled"""
    assert check_with_dbm.statement_activity is not None
    assert isinstance(check_with_dbm.statement_activity, ClickhouseStatementActivity)
    assert check_with_dbm.statement_activity._config.enabled is True
    assert check_with_dbm.statement_activity._config.collection_interval == 10
    assert check_with_dbm.statement_activity._config.payload_row_limit == 1000


def test_statement_activity_disabled():
    """Test that statement activity is not initialized when DBM is disabled"""
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
    assert check.statement_activity is None


def test_query_activity_disabled():
    """Test that statement activity is not initialized when query_activity is disabled"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_activity': {
            'enabled': False,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    assert check.statement_activity is None


def test_obfuscate_query(check_with_dbm):
    """Test query obfuscation"""
    activity = check_with_dbm.statement_activity

    row = {
        'query': 'SELECT * FROM users WHERE user_id = 12345',
        'user': 'default',
        'query_id': 'test-query-id-123',
    }

    normalized_row = activity._obfuscate_query(row)

    # Verify that statement and query_signature are set
    assert normalized_row['statement'] is not None
    assert normalized_row['query_signature'] is not None

    # Verify metadata was collected
    assert 'dd_tables' in normalized_row
    assert 'dd_commands' in normalized_row
    assert 'dd_comments' in normalized_row


def test_create_activity_event(check_with_dbm):
    """Test creation of activity event payload"""
    activity = check_with_dbm.statement_activity
    activity._tags_no_db = ['test:clickhouse', 'server:localhost']

    rows = [
        {
            'query_id': 'test-query-id-123',
            'query': 'SELECT * FROM users',
            'statement': 'SELECT * FROM users WHERE ?',
            'query_signature': 'abc123',
            'user': 'default',
            'elapsed': 0.1,
            'read_rows': 10,
            'memory_usage': 2048,
            'current_database': 'default',
        }
    ]

    active_connections = [{'user': 'default', 'query_kind': 'Select', 'current_database': 'default', 'connections': 5}]

    with mock.patch('datadog_checks.clickhouse.statement_activity.datadog_agent') as mock_agent:
        mock_agent.get_version.return_value = '7.64.0'
        event = activity._create_activity_event(rows, active_connections)

    # Verify event structure
    assert event['ddsource'] == 'clickhouse'
    assert event['dbm_type'] == 'activity'
    assert 'timestamp' in event
    assert 'collection_interval' in event
    assert event['collection_interval'] == 10

    # Verify activity payload
    assert 'clickhouse_activity' in event
    assert len(event['clickhouse_activity']) == 1

    # Verify connections payload
    assert 'clickhouse_connections' in event
    assert len(event['clickhouse_connections']) == 1


def test_active_queries_query_format():
    """Test that the active queries query is properly formatted"""
    from datadog_checks.clickhouse.statement_activity import ACTIVE_QUERIES_QUERY

    # Verify query uses placeholder for table (supports both local and cluster-wide queries)
    assert '{processes_table}' in ACTIVE_QUERIES_QUERY

    # Original fields
    assert 'query_id' in ACTIVE_QUERIES_QUERY
    assert 'query' in ACTIVE_QUERIES_QUERY
    assert 'elapsed' in ACTIVE_QUERIES_QUERY
    assert 'memory_usage' in ACTIVE_QUERIES_QUERY
    assert 'read_rows' in ACTIVE_QUERIES_QUERY
    assert 'read_bytes' in ACTIVE_QUERIES_QUERY
    assert 'written_rows' in ACTIVE_QUERIES_QUERY
    assert 'written_bytes' in ACTIVE_QUERIES_QUERY

    # Enhanced fields
    assert 'peak_memory_usage' in ACTIVE_QUERIES_QUERY
    assert 'total_rows_approx' in ACTIVE_QUERIES_QUERY
    assert 'client_name' in ACTIVE_QUERIES_QUERY
    assert 'current_database' in ACTIVE_QUERIES_QUERY
    assert 'thread_ids' in ACTIVE_QUERIES_QUERY
    assert 'is_cancelled' in ACTIVE_QUERIES_QUERY


def test_active_connections_query_format():
    """Test that the active connections query is properly formatted"""
    from datadog_checks.clickhouse.statement_activity import ACTIVE_CONNECTIONS_QUERY

    # Verify query uses placeholder for table
    assert '{processes_table}' in ACTIVE_CONNECTIONS_QUERY

    # Verify aggregation
    assert 'count(*)' in ACTIVE_CONNECTIONS_QUERY
    assert 'GROUP BY' in ACTIVE_CONNECTIONS_QUERY


def test_get_debug_tags(check_with_dbm):
    """Test that debug tags are properly generated"""
    activity = check_with_dbm.statement_activity
    activity._tags_no_db = ['server:localhost', 'port:9000', 'test:clickhouse']
    debug_tags = activity._get_debug_tags()

    assert isinstance(debug_tags, list)
    assert 'server:localhost' in debug_tags


def test_normalize_row_with_all_fields(check_with_dbm):
    """Test that all fields are properly normalized from system.processes"""
    activity = check_with_dbm.statement_activity

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
        1,  # client_version_major
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

    normalized_row = activity._normalize_row(mock_row)

    # Verify original fields
    assert normalized_row['elapsed'] == 1.234
    assert normalized_row['query_id'] == 'abc-123-def'
    assert normalized_row['user'] == 'default'
    assert normalized_row['read_rows'] == 1000
    assert normalized_row['read_bytes'] == 50000
    assert normalized_row['memory_usage'] == 1048576
    assert normalized_row['query_kind'] == 'Select'
    assert normalized_row['is_initial_query'] is True

    # Verify performance fields
    assert normalized_row['peak_memory_usage'] == 2097152
    assert normalized_row['total_rows_approx'] == 1000000

    # Verify client fields
    assert normalized_row['client_name'] == 'python-clickhouse-driver'
    assert normalized_row['client_version_major'] == 1
    assert normalized_row['client_version_minor'] == 2
    assert normalized_row['client_version_patch'] == 4
    assert normalized_row['client_hostname'] == 'app-server-01'
    assert normalized_row['address'] == '192.168.1.100'
    assert normalized_row['port'] == 54321

    # Verify database field
    assert normalized_row['current_database'] == 'analytics'

    # Verify thread fields
    assert normalized_row['thread_ids'] == [123, 124, 125]

    # Verify status fields
    assert normalized_row['is_cancelled'] is False

    # Verify HTTP field
    assert normalized_row['http_user_agent'] == 'python-requests/2.28.0'

    # Verify obfuscation happened
    assert 'statement' in normalized_row
    assert 'query_signature' in normalized_row


def test_create_active_sessions_respects_limit(check_with_dbm):
    """Test that active sessions are limited by payload_row_limit"""
    activity = check_with_dbm.statement_activity
    activity._payload_row_limit = 2

    rows = [
        {'statement': 'SELECT 1', 'query_signature': 'sig1', 'user': 'default'},
        {'statement': 'SELECT 2', 'query_signature': 'sig2', 'user': 'default'},
        {'statement': 'SELECT 3', 'query_signature': 'sig3', 'user': 'default'},
    ]

    sessions = list(activity._create_active_sessions(rows))
    assert len(sessions) == 2


def test_create_active_sessions_filters_null_statements(check_with_dbm):
    """Test that rows without statements are filtered out"""
    activity = check_with_dbm.statement_activity

    rows = [
        {'statement': 'SELECT 1', 'query_signature': 'sig1', 'user': 'default'},
        {'statement': None, 'query_signature': 'sig2', 'user': 'default'},
        {'statement': 'SELECT 3', 'query_signature': 'sig3', 'user': 'default'},
    ]

    sessions = list(activity._create_active_sessions(rows))
    assert len(sessions) == 2


def test_defaults_applied():
    """Test that default config values are applied correctly"""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_activity': {
            'enabled': True,
        },
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Verify defaults are applied
    assert check.statement_activity._config.collection_interval == 1
    assert check.statement_activity._config.payload_row_limit == 1000
    assert check.statement_activity._config.run_sync is False
