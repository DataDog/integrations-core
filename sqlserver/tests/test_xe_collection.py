# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime
import os
import sys
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from lxml import etree

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.xe_collection.base import TimestampHandler
from datadog_checks.sqlserver.xe_collection.error_events import ErrorEventsHandler
from datadog_checks.sqlserver.xe_collection.query_completion_events import QueryCompletionEventsHandler
from datadog_checks.sqlserver.xe_collection.registry import get_xe_session_handlers

CHECK_NAME = 'sqlserver'

# Mock datadog_agent before imports - ensure it's properly patched at module level
datadog_agent_mock = Mock()
datadog_agent_mock.get_version.return_value = '7.30.0'
sys.modules['datadog_agent'] = datadog_agent_mock


# Helper functions
def load_xml_fixture(filename):
    """Load an XML file from the fixtures directory"""
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'xml_xe_events')
    with open(os.path.join(fixtures_dir, filename), 'r') as f:
        return f.read()


# Fixtures for common test objects
@pytest.fixture
def mock_check():
    """Create a mock check with necessary attributes"""
    check = Mock()
    check.log = Mock()

    # Setup connection context manager properly
    conn_mock = Mock()
    cursor_mock = Mock()
    conn_context = Mock()
    conn_context.__enter__ = Mock(return_value=conn_mock)
    conn_context.__exit__ = Mock(return_value=None)
    cursor_context = Mock()
    cursor_context.__enter__ = Mock(return_value=cursor_mock)
    cursor_context.__exit__ = Mock(return_value=None)

    check.connection = Mock()
    check.connection.open_managed_default_connection = Mock(return_value=conn_context)
    check.connection.get_managed_cursor = Mock(return_value=cursor_context)

    # Make debug_stats_kwargs return an empty dictionary for @tracked_method decorator
    check.debug_stats_kwargs.return_value = {}

    check.static_info_cache = {'version': '2019', 'engine_edition': 'Standard Edition'}
    check.resolved_hostname = "test-host"
    check.tags = ["test:tag"]
    check.database_monitoring_query_activity = Mock()
    check.database_monitoring_query_sample = Mock()
    return check


@pytest.fixture
def mock_config():
    """Create a mock configuration"""
    config = Mock()
    config.collect_raw_query_statement = {"enabled": True, "cache_max_size": 100, "samples_per_hour_per_query": 10}
    config.min_collection_interval = 10
    config.obfuscator_options = {'dbms': 'mssql', 'obfuscation_mode': 'replace'}
    config.xe_collection_config = {
        'query_completions': {'collection_interval': 10, 'enabled': True},
        'query_errors': {'collection_interval': 20, 'enabled': True},
    }
    config.cloud_metadata = {}
    config.service = "sqlserver"
    return config


# Fixtures for XML data
@pytest.fixture
def sample_sql_batch_event_xml():
    """Load a sample SQL batch completed event XML"""
    return load_xml_fixture('sql_batch_completed.xml')


@pytest.fixture
def sample_rpc_completed_event_xml():
    """Load a sample RPC completed event XML"""
    return load_xml_fixture('rpc_completed.xml')


@pytest.fixture
def sample_error_event_xml():
    """Load a sample error event XML"""
    return load_xml_fixture('error_reported.xml')


@pytest.fixture
def sample_multiple_events_xml():
    """Load a sample with multiple events XML"""
    return load_xml_fixture('multiple_events.xml')


# Fixtures for handler instances
@pytest.fixture
def query_completion_handler(mock_check, mock_config):
    """Create a QueryCompletionEventsHandler instance for testing"""
    return QueryCompletionEventsHandler(mock_check, mock_config)


@pytest.fixture
def error_events_handler(mock_check, mock_config):
    """Create an ErrorEventsHandler instance for testing"""
    return ErrorEventsHandler(mock_check, mock_config)


class TestTimestampHandler:
    """Tests for the TimestampHandler utility class"""

    def test_format_for_output_valid_timestamps(self):
        """Test timestamp formatting with valid inputs"""
        # Test with UTC Z suffix
        assert TimestampHandler.format_for_output("2023-01-01T12:00:00.123Z") == "2023-01-01T12:00:00.123Z"

        # Test with timezone offset
        assert TimestampHandler.format_for_output("2023-01-01T12:00:00.123+00:00") == "2023-01-01T12:00:00.123Z"

        # Test with more microsecond precision
        assert TimestampHandler.format_for_output("2023-01-01T12:00:00.123456Z") == "2023-01-01T12:00:00.123Z"

    def test_format_for_output_edge_cases(self):
        """Test timestamp formatting with edge cases"""
        # Test with empty input
        assert TimestampHandler.format_for_output("") == ""

        # Test with None input
        assert TimestampHandler.format_for_output(None) == ""

        # Test with invalid format
        assert TimestampHandler.format_for_output("invalid-date") == "invalid-date"

    def test_calculate_start_time_valid_inputs(self):
        """Test calculation of start time from end time and duration"""
        # Test with 1 second duration
        assert TimestampHandler.calculate_start_time("2023-01-01T12:00:01.000Z", 1000) == "2023-01-01T12:00:00.000Z"

        # Test with fractional milliseconds
        assert TimestampHandler.calculate_start_time("2023-01-01T12:00:00.500Z", 500) == "2023-01-01T12:00:00.000Z"

        # Test with timezone offset
        assert (
            TimestampHandler.calculate_start_time("2023-01-01T12:00:00.000+00:00", 1000) == "2023-01-01T11:59:59.000Z"
        )

    def test_calculate_start_time_edge_cases(self):
        """Test start time calculation with edge cases"""
        # Test with empty timestamp
        assert TimestampHandler.calculate_start_time("", 1000) == ""

        # Test with None timestamp
        assert TimestampHandler.calculate_start_time(None, 1000) == ""

        # Test with None duration
        assert TimestampHandler.calculate_start_time("2023-01-01T12:00:00.000Z", None) == ""

        # Test with zero duration
        assert TimestampHandler.calculate_start_time("2023-01-01T12:00:00.000Z", 0) == "2023-01-01T12:00:00.000Z"

        # Test with invalid timestamp
        assert TimestampHandler.calculate_start_time("invalid-date", 1000) == ""


class TestXESessionHandlers:
    """Tests for the XE session handler implementations"""

    def test_initialization(self, mock_check, mock_config):
        """Test initialization of handlers"""
        # Test QueryCompletionEventsHandler
        handler = QueryCompletionEventsHandler(mock_check, mock_config)
        assert handler.session_name == "datadog_query_completions"
        assert handler.collection_interval == 10
        assert handler._enabled is True

        # Test ErrorEventsHandler
        handler = ErrorEventsHandler(mock_check, mock_config)
        assert handler.session_name == "datadog_query_errors"
        assert handler.collection_interval == 20
        assert handler._enabled is True

    def test_session_exists(self, query_completion_handler, mock_check):
        """Test session existence checking"""
        # Set up cursor mock
        cursor = mock_check.connection.get_managed_cursor.return_value.__enter__.return_value

        # Test when session exists
        cursor.fetchone.return_value = [1]  # Session exists
        assert query_completion_handler.session_exists() is True

        # Test when session does not exist
        cursor.fetchone.return_value = None  # No session
        assert query_completion_handler.session_exists() is False

    def test_extract_value(self, query_completion_handler):
        """Test extraction of values from XML elements"""
        # Test extracting value from element with value element
        xml = '<data name="test"><value>test_value</value></data>'
        element = etree.fromstring(xml)
        assert query_completion_handler._extract_value(element) == 'test_value'

        # Test extracting value from element with text
        xml = '<data name="test">test_value</data>'
        element = etree.fromstring(xml)
        assert query_completion_handler._extract_value(element) == 'test_value'

        # Test empty element
        xml = '<data name="test"></data>'
        element = etree.fromstring(xml)
        assert query_completion_handler._extract_value(element) == None
        assert query_completion_handler._extract_value(element, 'default') == 'default'

        # Test None element
        assert query_completion_handler._extract_value(None) == None
        assert query_completion_handler._extract_value(None, 'default') == 'default'

    def test_extract_int_value(self, query_completion_handler):
        """Test extraction of integer values"""
        # Test valid integer
        xml = '<data name="test"><value>123</value></data>'
        element = etree.fromstring(xml)
        assert query_completion_handler._extract_int_value(element) == 123

        # Test invalid integer
        xml = '<data name="test"><value>not_a_number</value></data>'
        element = etree.fromstring(xml)
        assert query_completion_handler._extract_int_value(element) == None
        assert query_completion_handler._extract_int_value(element, 0) == 0

        # Test empty element
        xml = '<data name="test"></data>'
        element = etree.fromstring(xml)
        assert query_completion_handler._extract_int_value(element) == None
        assert query_completion_handler._extract_int_value(element, 0) == 0

    def test_extract_text_representation(self, query_completion_handler):
        """Test extraction of text representation"""
        # Test with text element
        xml = '<data name="test"><value>123</value><text>text_value</text></data>'
        element = etree.fromstring(xml)
        assert query_completion_handler._extract_text_representation(element) == 'text_value'

        # Test without text element
        xml = '<data name="test"><value>123</value></data>'
        element = etree.fromstring(xml)
        assert query_completion_handler._extract_text_representation(element) == None
        assert query_completion_handler._extract_text_representation(element, 'default') == 'default'

    def test_extract_duration(self, query_completion_handler):
        """Test duration extraction specifically"""
        # Test with valid duration
        xml = '<data name="duration"><value>4829704</value></data>'
        element = etree.fromstring(xml)

        # Directly call the extract_duration method
        event_data = {}
        query_completion_handler._extract_duration(element, event_data)
        # In base.py, division is by 1000, not 1000000
        assert event_data["duration_ms"] == 4829.704

    def test_process_events_sql_batch(self, query_completion_handler, sample_sql_batch_event_xml):
        """Test processing of SQL batch completed events"""
        # Wrap the single event in an events tag
        xml_data = f"<events>{sample_sql_batch_event_xml}</events>"

        # Process the events
        events = query_completion_handler._process_events(xml_data)

        # Verify the event was processed correctly
        assert len(events) == 1
        event = events[0]
        assert event['event_name'] == 'sql_batch_completed'
        assert event['timestamp'] == '2025-04-24T20:56:52.809Z'
        # Microseconds divided by 1000 (to milliseconds)
        assert event['duration_ms'] == 4829.704  # 4829704 / 1000
        assert event['session_id'] == 123
        assert event['request_id'] == 0
        assert event['database_name'] == 'master'
        assert event['client_hostname'] == 'COMP-MX2YQD7P2P'
        assert event['client_app_name'] == 'azdata'
        assert event['username'] == 'datadog'
        assert 'batch_text' in event
        assert 'datadog_sp_statement_completed' in event['batch_text']
        assert 'sql_text' in event
        assert 'datadog_sp_statement_completed' in event['sql_text']

    def test_process_events_rpc_completed(self, query_completion_handler, sample_rpc_completed_event_xml):
        """Test processing of RPC completed events"""
        # Wrap the single event in an events tag
        xml_data = f"<events>{sample_rpc_completed_event_xml}</events>"

        # Process the events
        events = query_completion_handler._process_events(xml_data)

        # Verify the event was processed correctly
        assert len(events) == 1
        event = events[0]
        assert event['event_name'] == 'rpc_completed'
        assert event['timestamp'] == '2025-04-24T20:57:04.937Z'
        # Microseconds divided by 1000 (to milliseconds)
        assert event['duration_ms'] == 2699.535  # 2699535 / 1000
        assert event['session_id'] == 203
        assert event['request_id'] == 0
        assert event['database_name'] == 'msdb'
        assert event['client_hostname'] == 'EC2AMAZ-ML3E0PH'
        assert event['client_app_name'] == 'SQLAgent - Job Manager'
        assert event['username'] == 'NT AUTHORITY\\NETWORK SERVICE'
        assert 'statement' in event
        assert 'sp_executesql' in event['statement']
        assert 'sql_text' in event
        assert 'EXECUTE [msdb].[dbo].[sp_agent_log_job_history]' in event['sql_text']

    def test_process_events_error_reported(self, error_events_handler, sample_error_event_xml):
        """Test processing of error reported events"""
        # Wrap the single event in an events tag
        xml_data = f"<events>{sample_error_event_xml}</events>"

        # Process the events
        events = error_events_handler._process_events(xml_data)

        # Verify the event was processed correctly
        assert len(events) == 1
        event = events[0]
        assert event['event_name'] == 'error_reported'
        assert event['timestamp'] == '2025-04-24T20:57:17.287Z'
        assert event['error_number'] == 195
        assert event['severity'] == 15
        assert event['session_id'] == 81
        assert event['request_id'] == 0
        assert event['database_name'] == 'dbmorders'
        assert event['client_hostname'] == 'a05c90468fb8'
        assert event['client_app_name'] == 'go-mssqldb'
        assert event['username'] == 'shopper_4'
        assert event['message'] == "'REPEAT' is not a recognized built-in function name."
        assert 'sql_text' in event
        assert 'SELECT discount_percent' in event['sql_text']
        assert "REPEAT('a', 1000)" in event['sql_text']

    def test_process_events_multiple(self, query_completion_handler, sample_multiple_events_xml):
        """Test processing of multiple events"""
        # Process the events
        events = query_completion_handler._process_events(sample_multiple_events_xml)

        # Verify all events were processed correctly
        assert len(events) == 3

        # Check first event (sql_batch_completed)
        assert events[0]['event_name'] == 'sql_batch_completed'
        assert events[0]['timestamp'] == '2023-01-01T12:00:00.123Z'
        assert events[0]['duration_ms'] == 10.0
        assert events[0]['session_id'] == 123

        # Check second event (rpc_completed)
        assert events[1]['event_name'] == 'rpc_completed'
        assert events[1]['timestamp'] == '2023-01-01T12:01:00.456Z'
        assert events[1]['duration_ms'] == 5.0
        assert events[1]['session_id'] == 124

        # For error events, we need to convert the value since error_reported is handled by ErrorEventsHandler
        # In a real scenario, these events would be processed by their respective handlers

    @patch('datadog_checks.sqlserver.xe_collection.base.obfuscate_sql_with_metadata')
    @patch('datadog_checks.sqlserver.xe_collection.base.compute_sql_signature')
    def test_obfuscate_sql_fields(self, mock_compute_signature, mock_obfuscate, query_completion_handler):
        """Test SQL field obfuscation and signature creation"""
        # Setup mock obfuscator and signature generator
        mock_obfuscate.return_value = {
            'query': 'SELECT * FROM Customers WHERE CustomerId = ?',
            'metadata': {'commands': ['SELECT'], 'tables': ['Customers'], 'comments': []},
        }
        mock_compute_signature.return_value = 'abc123'

        # Test event with SQL fields
        event = {
            'event_name': 'sql_batch_completed',
            'batch_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
            'sql_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
        }

        obfuscated_event, raw_sql_fields = query_completion_handler._obfuscate_sql_fields(event)

        # Verify obfuscated fields
        assert obfuscated_event['batch_text'] == 'SELECT * FROM Customers WHERE CustomerId = ?'
        assert obfuscated_event['sql_text'] == 'SELECT * FROM Customers WHERE CustomerId = ?'
        assert obfuscated_event['dd_commands'] == ['SELECT']
        assert obfuscated_event['dd_tables'] == ['Customers']
        assert obfuscated_event['query_signature'] == 'abc123'

        # Verify raw SQL fields
        assert raw_sql_fields['batch_text'] == 'SELECT * FROM Customers WHERE CustomerId = 123'
        assert raw_sql_fields['sql_text'] == 'SELECT * FROM Customers WHERE CustomerId = 123'
        assert raw_sql_fields['raw_query_signature'] == 'abc123'

    def test_normalize_event(self, query_completion_handler):
        """Test event normalization"""
        # Test event with all fields
        event = {
            'event_name': 'sql_batch_completed',
            'timestamp': '2023-01-01T12:00:00.123Z',
            'duration_ms': 10.0,  # Already in milliseconds
            'session_id': 123,
            'request_id': 456,
            'database_name': 'TestDB',
            'client_hostname': 'TESTCLIENT',
            'client_app_name': 'TestApp',
            'username': 'TestUser',
            'batch_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
            'sql_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
            'query_signature': 'abc123',
        }

        normalized = query_completion_handler._normalize_event_impl(event)

        # Verify normalized fields
        assert normalized['xe_type'] == 'sql_batch_completed'
        assert normalized['event_fire_timestamp'] == '2023-01-01T12:00:00.123Z'
        assert normalized['duration_ms'] == 10.0
        assert normalized['session_id'] == 123
        assert normalized['request_id'] == 456
        assert normalized['database_name'] == 'TestDB'
        assert normalized['client_hostname'] == 'TESTCLIENT'
        assert normalized['client_app_name'] == 'TestApp'
        assert normalized['username'] == 'TestUser'
        assert normalized['batch_text'] == 'SELECT * FROM Customers WHERE CustomerId = 123'
        assert normalized['sql_text'] == 'SELECT * FROM Customers WHERE CustomerId = 123'
        assert normalized['query_signature'] == 'abc123'

    def test_normalize_error_event(self, error_events_handler):
        """Test error event normalization"""
        # Test error event with fields
        event = {
            'event_name': 'error_reported',
            'timestamp': '2023-01-01T12:00:00.123Z',
            'error_number': 8134,
            'severity': 15,
            'state': 1,
            'session_id': 123,
            'request_id': 456,
            'database_name': 'TestDB',
            'message': 'Division by zero error',
            'sql_text': 'SELECT 1/0',
        }

        normalized = error_events_handler._normalize_event_impl(event)

        # Verify normalized fields
        assert normalized['xe_type'] == 'error_reported'
        assert normalized['event_fire_timestamp'] == '2023-01-01T12:00:00.123Z'
        assert normalized['error_number'] == 8134
        assert normalized['severity'] == 15
        assert normalized['state'] == 1
        assert normalized['session_id'] == 123
        assert normalized['request_id'] == 456
        assert normalized['database_name'] == 'TestDB'
        assert normalized['message'] == 'Division by zero error'
        assert normalized['sql_text'] == 'SELECT 1/0'

        # Verify duration_ms and query_start are removed for error events
        assert 'duration_ms' not in normalized
        assert 'query_start' not in normalized

    def test_determine_dbm_type(self, mock_check, mock_config):
        """Test determination of DBM type based on session name"""
        # Test query completion handler
        handler = QueryCompletionEventsHandler(mock_check, mock_config)
        assert handler._determine_dbm_type() == "query_completion"

        # Test query error handler
        handler = ErrorEventsHandler(mock_check, mock_config)
        assert handler._determine_dbm_type() == "query_error"

    @patch('datadog_checks.sqlserver.xe_collection.base.datadog_agent')
    @patch('time.time')
    def test_create_event_payload(self, mock_time, mock_agent, query_completion_handler):
        """Test creation of event payload"""
        mock_time.return_value = 1609459200  # 2021-01-01 00:00:00
        mock_agent.get_version.return_value = '7.30.0'

        # Create a raw event
        raw_event = {
            'event_name': 'sql_batch_completed',
            'timestamp': '2023-01-01T12:00:00.123Z',
            'duration_ms': 10.0,
            'session_id': 123,
            'request_id': 456,
            'database_name': 'TestDB',
            'batch_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
            'query_signature': 'abc123',
        }

        # Create payload
        payload = query_completion_handler._create_event_payload(raw_event)

        # Verify payload structure
        assert payload['host'] == 'test-host'
        assert payload['ddagentversion'] == '7.30.0'
        assert payload['ddsource'] == 'sqlserver'
        assert payload['dbm_type'] == 'query_completion'
        assert payload['event_source'] == 'datadog_query_completions'
        assert payload['collection_interval'] == 10
        assert payload['ddtags'] == ['test:tag']
        assert payload['timestamp'] == 1609459200 * 1000
        assert payload['sqlserver_version'] == '2019'
        assert payload['sqlserver_engine_edition'] == 'Standard Edition'
        assert payload['service'] == 'sqlserver'

        # Verify query details
        query_details = payload['query_details']
        assert query_details['xe_type'] == 'sql_batch_completed'
        assert query_details['duration_ms'] == 10.0
        assert query_details['session_id'] == 123
        assert query_details['request_id'] == 456
        assert query_details['database_name'] == 'TestDB'
        assert query_details['query_signature'] == 'abc123'

    @patch('datadog_checks.sqlserver.xe_collection.base.datadog_agent')
    @patch('time.time')
    def test_create_rqt_event(self, mock_time, mock_agent, query_completion_handler):
        """Test creation of Raw Query Text event"""
        mock_time.return_value = 1609459200  # 2021-01-01 00:00:00
        mock_agent.get_version.return_value = '7.30.0'

        # Create event with SQL fields
        event = {
            'event_name': 'sql_batch_completed',
            'timestamp': '2023-01-01T12:00:00.123Z',
            'duration_ms': 10.0,
            'session_id': 123,
            'database_name': 'TestDB',
            'batch_text': 'SELECT * FROM Customers WHERE CustomerId = ?',
            'query_signature': 'abc123',
        }

        # Create raw SQL fields
        raw_sql_fields = {
            'batch_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
            'raw_query_signature': 'def456',
        }

        # Query details with formatted timestamps
        query_details = {'event_fire_timestamp': '2023-01-01T12:00:00.123Z', 'query_start': '2023-01-01T11:59:50.123Z'}

        # Create RQT event
        rqt_event = query_completion_handler._create_rqt_event(event, raw_sql_fields, query_details)

        # Verify RQT event structure
        assert rqt_event['timestamp'] == 1609459200 * 1000
        assert rqt_event['host'] == 'test-host'
        assert rqt_event['ddsource'] == 'sqlserver'
        assert rqt_event['dbm_type'] == 'rqt'
        assert rqt_event['event_source'] == 'datadog_query_completions'
        assert rqt_event['ddtags'] == 'test:tag'
        assert rqt_event['service'] == 'sqlserver'

        # Verify DB fields
        assert rqt_event['db']['instance'] == 'TestDB'
        assert rqt_event['db']['query_signature'] == 'abc123'
        assert rqt_event['db']['raw_query_signature'] == 'def456'
        assert rqt_event['db']['statement'] == 'SELECT * FROM Customers WHERE CustomerId = 123'

        # Verify sqlserver fields
        assert rqt_event['sqlserver']['session_id'] == 123
        assert rqt_event['sqlserver']['xe_type'] == 'sql_batch_completed'
        assert rqt_event['sqlserver']['event_fire_timestamp'] == '2023-01-01T12:00:00.123Z'
        assert rqt_event['sqlserver']['duration_ms'] == 10.0
        assert rqt_event['sqlserver']['query_start'] == '2023-01-01T11:59:50.123Z'

    @patch('time.time')
    def test_filter_ring_buffer_events(self, mock_time, query_completion_handler):
        """Test filtering of ring buffer events based on timestamp"""
        mock_time.return_value = 1609459200  # 2021-01-01 00:00:00

        # Create XML with multiple events
        xml_data = """
        <RingBufferTarget>
          <event name="sql_batch_completed" timestamp="2023-01-01T12:00:00.123Z">
            <data name="duration"><value>10000</value></data>
          </event>
          <event name="sql_batch_completed" timestamp="2023-01-01T12:01:00.456Z">
            <data name="duration"><value>5000</value></data>
          </event>
          <event name="sql_batch_completed" timestamp="2023-01-01T12:02:00.789Z">
            <data name="duration"><value>2000</value></data>
          </event>
        </RingBufferTarget>
        """

        # Test with no timestamp filter (first run)
        filtered_events = query_completion_handler._filter_ring_buffer_events(xml_data)
        assert len(filtered_events) == 3

        # Set last event timestamp
        query_completion_handler._last_event_timestamp = "2023-01-01T12:01:00.456Z"

        # Test with timestamp filter (subsequent run)
        filtered_events = query_completion_handler._filter_ring_buffer_events(xml_data)
        assert len(filtered_events) == 1  # Only the event after 12:01:00.456Z
        assert "2023-01-01T12:02:00.789Z" in filtered_events[0]

    def test_create_rqt_event_disabled(self, mock_check, mock_config):
        """Test RQT event creation when disabled"""
        # Disable raw query collection
        mock_config.collect_raw_query_statement["enabled"] = False

        handler = QueryCompletionEventsHandler(mock_check, mock_config)

        event = {
            'event_name': 'sql_batch_completed',
            'timestamp': '2023-01-01T12:00:00.123Z',
            'query_signature': 'abc123',  # Add query_signature to avoid assertion failure
        }

        raw_sql_fields = {
            'batch_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
            'raw_query_signature': 'def456',
        }

        query_details = {
            'event_fire_timestamp': '2023-01-01T12:00:00.123Z',
        }

        # Should return None when disabled
        assert handler._create_rqt_event(event, raw_sql_fields, query_details) is None

    def test_create_rqt_event_missing_signature(self, query_completion_handler):
        """Test RQT event creation with missing query signature"""
        # Event without query signature
        event = {
            'event_name': 'sql_batch_completed',
            'timestamp': '2023-01-01T12:00:00.123Z',
            # No query_signature
        }

        raw_sql_fields = {
            'batch_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
            'raw_query_signature': 'def456',
        }

        query_details = {
            'event_fire_timestamp': '2023-01-01T12:00:00.123Z',
        }

        # Should return None when missing signature
        assert query_completion_handler._create_rqt_event(event, raw_sql_fields, query_details) is None

    def test_malformed_xml(self, query_completion_handler):
        """Test handling of malformed XML"""
        # Malformed XML data
        xml_data = "<events><event>Malformed XML</x></events>"

        # Should return empty list and not raise exception
        events = query_completion_handler._process_events(xml_data)
        assert events == []

    @patch('time.time')
    def test_run_job_success(self, mock_time, query_completion_handler, sample_multiple_events_xml):
        """Test successful run_job execution"""
        mock_time.return_value = 1609459200  # 2021-01-01 00:00:00

        # Mock session_exists
        with patch.object(query_completion_handler, 'session_exists', return_value=True):
            # Mock ring buffer query
            with patch.object(
                query_completion_handler, '_query_ring_buffer', return_value=(sample_multiple_events_xml, 0.1, 0.1)
            ):
                # Run the job
                query_completion_handler.run_job()

                # Ensure the last event timestamp was updated
                assert query_completion_handler._last_event_timestamp == "2023-01-01T12:02:00.789Z"

    def test_run_job_no_session(self, query_completion_handler, mock_check):
        """Test run_job when session doesn't exist"""
        # Mock session_exists to return False
        with patch.object(query_completion_handler, 'session_exists', return_value=False):
            # Need to directly patch the check's log to confirm warning is called
            # Since we're using the real implementation now
            query_completion_handler.run_job()

            # Verify the warning log message directly
            mock_check.log.warning.assert_called_once_with(
                f"XE session {query_completion_handler.session_name} not found or not running"
            )

    def test_run_job_no_data(self, query_completion_handler, mock_check):
        """Test run_job when no data is returned"""
        # Mock session_exists to return True
        with patch.object(query_completion_handler, 'session_exists', return_value=True):
            # Mock query_ring_buffer to return None
            with patch.object(query_completion_handler, '_query_ring_buffer', return_value=(None, 0.1, 0.1)):
                # Run the job - should log a debug message and return
                query_completion_handler.run_job()
                # Verify the debug message
                mock_check.log.debug.assert_called_with(
                    f"No data found for session {query_completion_handler.session_name}"
                )

    def test_check_azure_status(self, mock_check, mock_config):
        """Test Azure SQL Database detection"""
        # Test non-Azure SQL Server
        mock_check.static_info_cache = {'engine_edition': 'Standard Edition'}
        handler = QueryCompletionEventsHandler(mock_check, mock_config)
        assert handler._is_azure_sql_database is False

        # Test Azure SQL Database
        mock_check.static_info_cache = {'engine_edition': 'Azure SQL Database'}
        # We need to create a new handler to trigger the check_azure_status in init
        from datadog_checks.sqlserver.utils import is_azure_sql_database

        with patch(
            'datadog_checks.sqlserver.xe_collection.base.is_azure_sql_database',
            side_effect=lambda x: x == 'Azure SQL Database',
        ):
            handler = QueryCompletionEventsHandler(mock_check, mock_config)
            assert handler._is_azure_sql_database is True


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_xe_session_handlers_creation(init_config, instance_docker_metrics):
    """Test creation of XE session handlers via the SQLServer class"""
    # Enable XE collection
    instance = instance_docker_metrics.copy()
    instance['xe_collection_config'] = {'query_completions': {'enabled': True}, 'query_errors': {'enabled': True}}

    # Create SQLServer check
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance])

    # Instantiate the handlers directly to test
    handlers = []
    handlers.append(QueryCompletionEventsHandler(sqlserver_check, sqlserver_check._config))
    handlers.append(ErrorEventsHandler(sqlserver_check, sqlserver_check._config))

    # Verify that handlers were created with expected properties
    assert len(handlers) == 2
    assert any(h.session_name == 'datadog_query_completions' for h in handlers)
    assert any(h.session_name == 'datadog_query_errors' for h in handlers)
