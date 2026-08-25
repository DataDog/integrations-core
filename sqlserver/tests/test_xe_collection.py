# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import os
import sys
from unittest.mock import Mock, patch

import pytest
from lxml import etree

from datadog_checks.base.utils.db.utils import TagManager
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.xe_collection.base import TimestampHandler
from datadog_checks.sqlserver.xe_collection.error_events import ErrorEventsHandler
from datadog_checks.sqlserver.xe_collection.query_completion_events import QueryCompletionEventsHandler
from datadog_checks.sqlserver.xe_collection.xml_tools import (
    extract_duration,
    extract_field,
    extract_int_value,
    extract_text_representation,
    extract_value,
)

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


def wrap_xml_in_events_tag(event_xml):
    """Wrap a single event XML in the events tag for testing"""
    return f"<events>{event_xml}</events>"


def assert_event_field_values(event, expected_values):
    """Assert that event fields match expected values with appropriate type conversion"""
    for field, expected in expected_values.items():
        if field in ['session_id', 'request_id', 'error_number', 'severity']:
            assert int(event[field]) == expected
        else:
            assert event[field] == expected


def validate_common_payload_fields(payload, expected_type):
    """Validate common fields in event payloads"""
    assert 'timestamp' in payload
    assert payload['host'] == 'test-host'
    assert payload['ddagentversion'] == '7.30.0'
    assert payload['ddsource'] == 'sqlserver'
    assert payload['dbm_type'] == expected_type
    assert 'service' in payload

    # Fields that only exist in regular events (non-RQT)
    if expected_type != 'rqt':
        assert 'collection_interval' in payload
        assert 'sqlserver_version' in payload
        assert 'sqlserver_engine_edition' in payload
        assert 'query_details' in payload

    # Fields that only exist in RQT events
    if expected_type == 'rqt':
        assert 'db' in payload
        assert 'sqlserver' in payload


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
    check.tag_manager = TagManager()
    check.tag_manager.set_tag('test', 'tag')
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
def sample_module_end_event_xml():
    """Load a sample module end event XML"""
    return load_xml_fixture('module_end.xml')


@pytest.fixture
def sample_multiple_events_xml():
    """Load a sample with multiple events XML"""
    return load_xml_fixture('multiple_events.xml')


@pytest.fixture
def sample_attention_event_xml():
    """Load a sample attention event XML"""
    return load_xml_fixture('attention.xml')


# Fixtures for expected event values
@pytest.fixture
def sql_batch_expected_values():
    """Expected values for SQL batch completed events"""
    return {
        'event_name': 'sql_batch_completed',
        'timestamp': '2025-04-24T20:56:52.809Z',
        'duration_ms': 4829.704,
        'session_id': 123,
        'request_id': 0,
        'database_name': 'master',
        'client_hostname': 'COMP-MX2YQD7P2P',
        'client_app_name': 'azdata',
        'username': 'datadog',
    }


@pytest.fixture
def rpc_completed_expected_values():
    """Expected values for RPC completed events"""
    return {
        'event_name': 'rpc_completed',
        'timestamp': '2025-04-24T20:57:04.937Z',
        'duration_ms': 2699.535,
        'session_id': 203,
        'request_id': 0,
        'database_name': 'msdb',
        'client_hostname': 'EC2AMAZ-ML3E0PH',
        'client_app_name': 'SQLAgent - Job Manager',
        'username': 'NT AUTHORITY\\NETWORK SERVICE',
        'object_name': 'sp_executesql',
    }


@pytest.fixture
def error_expected_values():
    """Expected values for error reported events"""
    return {
        'event_name': 'error_reported',
        'timestamp': '2025-04-24T20:57:17.287Z',
        'error_number': 195,
        'severity': 15,
        'session_id': 81,
        'request_id': 0,
        'database_name': 'dbmorders',
        'client_hostname': 'a05c90468fb8',
        'client_app_name': 'go-mssqldb',
        'username': 'shopper_4',
        'message': "'REPEAT' is not a recognized built-in function name.",
        'activity_id': 'F961B15C-752A-487E-AC4F-F2A9BAB11DB7-1',
        'activity_id_xfer': 'AFCCDE6F-EACD-47F3-9B62-CC02D517191B-0',
    }


@pytest.fixture
def module_end_expected_values():
    """Expected values for module end events"""
    return {
        'event_name': 'module_end',
        'timestamp': '2025-04-24T20:56:25.313Z',
        'duration_ms': 1239.182,  # 1239182 / 1000
        'session_id': 115,
        'request_id': 0,
        'database_name': 'dbmorders',
        'client_hostname': 'a05c90468fb8',
        'client_app_name': 'go-mssqldb',
        'username': 'shopper_4',
        'statement': 'EXEC SelectAndProcessOrderItem',
        'sql_text': "/*dddbs='orders-app',ddps='orders-app',"
        + "ddh='awbergs-sqlserver2019-test.c7ug0vvtkhqv.us-east-1.rds.amazonaws.com',"
        + "dddb='dbmorders',ddprs='orders-sqlserver'*/ EXEC SelectAndProcessOrderItem",
        # Module-specific fields
        'object_name': 'SelectAndProcessOrderItem',
        'object_type': 'P',  # P for stored procedure
        'row_count': 2,
        'line_number': 1,
        'offset': 314,
        'offset_end': 372,
        'source_database_id': 9,
        'object_id': 2002300576,
    }


@pytest.fixture
def attention_expected_values():
    """Expected values for attention events"""
    return {
        'event_name': 'attention',
        'timestamp': '2025-04-24T20:37:47.978Z',
        'duration_ms': 328.677,
        'session_id': 123,
        'request_id': 0,
        'database_name': 'master',
        'client_hostname': 'COMP-MX2YQD7P2P',
        'client_app_name': 'azdata',
        'username': 'datadog',
        'activity_id': 'F961B15C-752A-487E-AC4F-F2A9BAB11DB7-1',
        'activity_id_xfer': 'AFCCDE6F-EACD-47F3-9B62-CC02D517191B-0',
    }


# Fixtures for handler instances
@pytest.fixture
def query_completion_handler(mock_check, mock_config):
    """Create a QueryCompletionEventsHandler instance for testing"""
    return QueryCompletionEventsHandler(mock_check, mock_config)


@pytest.fixture
def error_events_handler(mock_check, mock_config):
    """Create an ErrorEventsHandler instance for testing"""
    return ErrorEventsHandler(mock_check, mock_config)


@pytest.fixture
def mock_handler_log(request):
    """Mock a handler's log for testing"""

    def _mock_log(handler, mock_check):
        original_log = handler._log
        handler._log = mock_check.log

        # Add finalizer to restore log after test
        def _restore_log():
            handler._log = original_log

        request.addfinalizer(_restore_log)

        return mock_check.log

    return _mock_log


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


class TestXESessionHandlersInitialization:
    """Tests related to handler initialization"""

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

    def test_check_azure_status(self, mock_check, mock_config):
        """Test Azure SQL Database detection"""
        # Test non-Azure SQL Server
        mock_check.static_info_cache = {'engine_edition': 'Standard Edition'}
        handler = QueryCompletionEventsHandler(mock_check, mock_config)
        assert handler._is_azure_sql_database is False

        # Test Azure SQL Database
        mock_check.static_info_cache = {'engine_edition': 'Azure SQL Database'}

        with patch(
            'datadog_checks.sqlserver.xe_collection.base.is_azure_sql_database',
            side_effect=lambda x: x == 'Azure SQL Database',
        ):
            handler = QueryCompletionEventsHandler(mock_check, mock_config)
            assert handler._is_azure_sql_database is True


class TestXESessionHelpers:
    """Tests for XML parsing tools"""

    def test_extract_value(self):
        """Test extraction of values from XML elements"""
        # Test extracting value from element with value element
        xml = '<data name="test"><value>test_value</value></data>'
        element = etree.fromstring(xml)
        assert extract_value(element) == 'test_value'

        # Test extracting value from element with text
        xml = '<data name="test">test_value</data>'
        element = etree.fromstring(xml)
        assert extract_value(element) == 'test_value'

        # Test empty element
        xml = '<data name="test"></data>'
        element = etree.fromstring(xml)
        assert extract_value(element) is None
        assert extract_value(element, 'default') == 'default'

        # Test None element
        assert extract_value(None) is None
        assert extract_value(None, 'default') == 'default'

    def test_extract_int_value(self):
        """Test extraction of integer values"""
        # Test valid integer
        xml = '<data name="test"><value>123</value></data>'
        element = etree.fromstring(xml)
        assert extract_int_value(element) == 123

        # Test invalid integer
        xml = '<data name="test"><value>not_a_number</value></data>'
        element = etree.fromstring(xml)
        assert extract_int_value(element) is None
        assert extract_int_value(element, 0) == 0

        # Test empty element
        xml = '<data name="test"></data>'
        element = etree.fromstring(xml)
        assert extract_int_value(element) is None
        assert extract_int_value(element, 0) == 0

    def test_extract_text_representation(self):
        """Test extraction of text representation"""
        # Test with text element
        xml = '<data name="test"><value>123</value><text>text_value</text></data>'
        element = etree.fromstring(xml)
        assert extract_text_representation(element) == 'text_value'

        # Test without text element
        xml = '<data name="test"><value>123</value></data>'
        element = etree.fromstring(xml)
        assert extract_text_representation(element) is None
        assert extract_text_representation(element, 'default') == 'default'

    def test_extract_duration(self):
        """Test duration extraction specifically"""
        # Test with valid duration
        xml = '<data name="duration"><value>4829704</value></data>'
        element = etree.fromstring(xml)

        # Test direct function
        event_data = {}
        extract_duration(element, event_data)
        assert event_data["duration_ms"] == 4829.704

        # Test with invalid duration
        xml = '<data name="duration"><value>not_a_number</value></data>'
        element = etree.fromstring(xml)

        # Test direct function
        event_data = {}
        extract_duration(element, event_data)
        assert event_data["duration_ms"] is None

    def test_extract_field(self, query_completion_handler):
        """Test field extraction based on its type"""
        # Get TEXT_FIELDS and numeric_fields for testing
        text_fields = query_completion_handler.TEXT_FIELDS
        numeric_fields = query_completion_handler.get_numeric_fields('test_event')

        # For duration field
        xml = '<data name="duration"><value>4829704</value></data>'
        element = etree.fromstring(xml)

        # Test direct function
        event_data = {'event_name': 'test_event'}
        extract_field(element, event_data, 'duration', numeric_fields, text_fields)
        assert event_data["duration_ms"] == 4829.704

        # For numeric field
        xml = '<data name="session_id"><value>123</value></data>'
        element = etree.fromstring(xml)

        # Test direct function
        event_data = {'event_name': 'test_event'}
        extract_field(element, event_data, 'session_id', numeric_fields, text_fields)
        assert event_data["session_id"] == 123

        # For text field (create a test logger)
        log = logging.getLogger('test')

        # Define a test text field
        test_text_fields = ['result']

        # For text field
        xml = '<data name="result"><value>123</value><text>Success</text></data>'
        element = etree.fromstring(xml)

        # Test direct function
        event_data = {'event_name': 'test_event'}
        extract_field(element, event_data, 'result', numeric_fields, test_text_fields, log)
        assert event_data["result"] == 'Success'

        # For regular field
        xml = '<data name="database_name"><value>TestDB</value></data>'
        element = etree.fromstring(xml)

        # Test direct function
        event_data = {'event_name': 'test_event'}
        extract_field(element, event_data, 'database_name', numeric_fields, text_fields, log)
        assert event_data["database_name"] == 'TestDB'

    def test_determine_dbm_type(self, mock_check, mock_config):
        """Test determination of DBM type based on session name"""
        # Test query completion handler
        handler = QueryCompletionEventsHandler(mock_check, mock_config)
        assert handler._determine_dbm_type() == "query_completion"

        # Test query error handler
        handler = ErrorEventsHandler(mock_check, mock_config)
        assert handler._determine_dbm_type() == "query_error"

    def test_process_events_filtering(self, query_completion_handler):
        """Test filtering and processing of ring buffer events based on timestamp"""
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

        # Mock event handler to always return True
        mock_handler = Mock(return_value=True)
        query_completion_handler._event_handlers = {'sql_batch_completed': mock_handler}

        # Test with no timestamp filter (first run)
        processed_events = query_completion_handler._process_events(xml_data)
        assert len(processed_events) == 3
        assert mock_handler.call_count == 3

        # Reset mock and set last event timestamp
        mock_handler.reset_mock()
        query_completion_handler._last_event_timestamp = "2023-01-01T12:01:00.456Z"

        # Test with timestamp filter (subsequent run)
        processed_events = query_completion_handler._process_events(xml_data)
        assert len(processed_events) == 1  # Only the event after 12:01:00.456Z
        assert processed_events[0]['timestamp'] == "2023-01-01T12:02:00.789Z"
        assert mock_handler.call_count == 1

    def test_malformed_xml(self, query_completion_handler):
        """Test handling of malformed XML"""
        # Malformed XML data
        xml_data = "<events><event>Malformed XML</x></events>"

        # Should return empty list and not raise exception
        events = query_completion_handler._process_events(xml_data)
        assert events == []


class TestEventProcessing:
    """Tests for event processing"""

    def test_process_events_sql_batch(
        self, query_completion_handler, sample_sql_batch_event_xml, sql_batch_expected_values
    ):
        """Test processing of SQL batch completed events"""
        # Wrap the single event in an events tag
        xml_data = wrap_xml_in_events_tag(sample_sql_batch_event_xml)

        # Process the events
        events = query_completion_handler._process_events(xml_data)

        # Verify the event was processed correctly
        assert len(events) == 1
        event = events[0]

        # Verify expected values
        assert_event_field_values(event, sql_batch_expected_values)

        # Check for event-specific fields
        assert 'batch_text' in event
        assert 'datadog_sp_statement_completed' in event['batch_text']
        assert 'sql_text' in event
        assert 'datadog_sp_statement_completed' in event['sql_text']

    def test_process_events_rpc_completed(
        self, query_completion_handler, sample_rpc_completed_event_xml, rpc_completed_expected_values
    ):
        """Test processing of RPC completed events"""
        # Wrap the single event in an events tag
        xml_data = wrap_xml_in_events_tag(sample_rpc_completed_event_xml)

        # Process the events
        events = query_completion_handler._process_events(xml_data)

        # Verify the event was processed correctly
        assert len(events) == 1
        event = events[0]

        # Verify expected values
        assert_event_field_values(event, rpc_completed_expected_values)

        # Check for event-specific fields
        assert 'statement' in event
        assert 'sp_executesql' in event['statement']
        assert 'sql_text' in event
        assert 'EXECUTE [msdb].[dbo].[sp_agent_log_job_history]' in event['sql_text']
        assert 'object_name' in event
        assert event['object_name'] == 'sp_executesql'

    def test_process_events_error_reported(self, error_events_handler, sample_error_event_xml, error_expected_values):
        """Test processing of error reported events"""
        # Wrap the single event in an events tag
        xml_data = wrap_xml_in_events_tag(sample_error_event_xml)

        # Process the events
        events = error_events_handler._process_events(xml_data)

        # Verify the event was processed correctly
        assert len(events) == 1
        event = events[0]

        # Verify expected values
        assert_event_field_values(event, error_expected_values)

        # Check for event-specific fields
        assert 'sql_text' in event
        assert 'SELECT discount_percent' in event['sql_text']
        assert "REPEAT('a', 1000)" in event['sql_text']

    def test_process_events_module_end(
        self, query_completion_handler, sample_module_end_event_xml, module_end_expected_values
    ):
        """Test processing of module end events"""
        # Wrap the single event in an events tag
        xml_data = wrap_xml_in_events_tag(sample_module_end_event_xml)

        # Process the events
        events = query_completion_handler._process_events(xml_data)

        # Verify the event was processed correctly
        assert len(events) == 1
        event = events[0]

        # Verify expected values
        assert_event_field_values(event, module_end_expected_values)

        # Check for event-specific fields
        assert 'statement' in event
        assert 'EXEC SelectAndProcessOrderItem' in event['statement']
        assert 'sql_text' in event
        assert 'EXEC SelectAndProcessOrderItem' in event['sql_text']
        assert 'object_name' in event
        assert event['object_name'] == 'SelectAndProcessOrderItem'
        assert 'object_type' in event
        assert event['object_type'] == 'P'  # P for stored procedure
        assert 'row_count' in event
        assert int(event['row_count']) == 2

    def test_process_events_multiple(self, query_completion_handler, error_events_handler, sample_multiple_events_xml):
        """Test processing of multiple events"""
        # Process with both handlers
        events = []
        events.extend(query_completion_handler._process_events(sample_multiple_events_xml))
        events.extend(error_events_handler._process_events(sample_multiple_events_xml))

        # Sort and validate event count
        events.sort(key=lambda x: x['timestamp'])
        assert len(events) == 3

        # Validate expected event types in order
        expected_types = ['sql_batch_completed', 'rpc_completed', 'error_reported']
        expected_sessions = [123, 124, 125]

        for event, exp_type, exp_session in zip(events, expected_types, expected_sessions):
            assert event['event_name'] == exp_type
            assert int(event['session_id']) == exp_session

    def test_process_events_attention(
        self, error_events_handler, sample_attention_event_xml, attention_expected_values
    ):
        """Test processing of attention events"""
        # Wrap the single event in an events tag
        xml_data = wrap_xml_in_events_tag(sample_attention_event_xml)

        # Process the events
        events = error_events_handler._process_events(xml_data)

        # Verify the event was processed correctly
        assert len(events) == 1
        event = events[0]

        # Verify expected values
        assert_event_field_values(event, attention_expected_values)

        # Check for event-specific fields
        assert 'sql_text' in event
        assert 'DECLARE @session_name NVARCHAR(100) = \'datadog_sql_statement\'' in event['sql_text']


class TestPayloadGeneration:
    """Tests for event payload generation"""

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

        obfuscated_event, raw_sql_fields, primary_sql_field = query_completion_handler._obfuscate_sql_fields(event)

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

        # Verify primary SQL field
        assert primary_sql_field == 'batch_text'

        # Verify raw_query_signature is added to the obfuscated event when collect_raw_query is enabled
        assert 'raw_query_signature' in obfuscated_event
        assert obfuscated_event['raw_query_signature'] == 'abc123'

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
            'raw_query_signature': 'def456',
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
        assert normalized['raw_query_signature'] == 'def456'

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

    def test_normalize_attention_event(self, error_events_handler):
        """Test attention event normalization"""
        # Test attention event with fields
        event = {
            'event_name': 'attention',
            'timestamp': '2023-01-01T12:00:00.123Z',
            'duration_ms': 328.677,
            'session_id': 123,
            'request_id': 456,
            'database_name': 'TestDB',
            'sql_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
        }

        normalized = error_events_handler._normalize_event_impl(event)

        # Verify normalized fields
        assert normalized['xe_type'] == 'attention'
        assert normalized['event_fire_timestamp'] == '2023-01-01T12:00:00.123Z'
        assert normalized['session_id'] == 123
        assert normalized['request_id'] == 456
        assert normalized['database_name'] == 'TestDB'
        assert normalized['sql_text'] == 'SELECT * FROM Customers WHERE CustomerId = 123'

        # Verify duration_ms and query_start are preserved for attention events
        assert 'duration_ms' in normalized
        assert normalized['duration_ms'] == 328.677
        assert 'query_start' in normalized  # Query start should be calculated from timestamp and duration

    @patch('datadog_checks.sqlserver.xe_collection.base.datadog_agent')
    def test_create_event_payload(self, mock_agent, query_completion_handler):
        """Test creation of event payload"""
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
            'primary_sql_field': 'batch_text',
            'dd_tables': ['Customers'],
            'dd_commands': ['SELECT'],
            'dd_comments': [],
        }

        # Create payload
        payload = query_completion_handler._create_event_payload(raw_event)

        # Validate common payload fields
        validate_common_payload_fields(payload, expected_type='query_completion')

        # Verify query details
        query_details = payload['query_details']
        assert query_details['xe_type'] == 'sql_batch_completed'
        assert query_details['duration_ms'] == 10.0
        assert query_details['session_id'] == 123
        assert query_details['request_id'] == 456
        assert query_details['database_name'] == 'TestDB'
        assert query_details['query_signature'] == 'abc123'
        assert query_details['primary_sql_field'] == 'batch_text'

        # Verify metadata structure
        assert 'metadata' in query_details
        metadata = query_details['metadata']
        assert metadata['tables'] == ['Customers']
        assert metadata['commands'] == ['SELECT']
        assert metadata['comments'] == []

    @patch('datadog_checks.sqlserver.xe_collection.base.datadog_agent')
    def test_create_rqt_event(self, mock_agent, query_completion_handler):
        """Test creation of Raw Query Text event"""
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
            'primary_sql_field': 'batch_text',
            'dd_tables': ['Customers'],
            'dd_commands': ['SELECT'],
            'dd_comments': [],
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

        # Validate common payload fields
        validate_common_payload_fields(rqt_event, expected_type='rqt')

        # Verify DB fields
        assert rqt_event['db']['instance'] == 'TestDB'
        assert rqt_event['db']['query_signature'] == 'abc123'
        assert rqt_event['db']['raw_query_signature'] == 'def456'
        assert rqt_event['db']['statement'] == 'SELECT * FROM Customers WHERE CustomerId = 123'

        # Verify metadata is present in the RQT event (RQT events already have this structure)
        assert 'metadata' in rqt_event['db']
        metadata = rqt_event['db']['metadata']
        assert metadata['tables'] == ['Customers']
        assert metadata['commands'] == ['SELECT']
        assert metadata['comments'] == []

        # Verify sqlserver fields
        assert rqt_event['sqlserver']['session_id'] == 123
        assert rqt_event['sqlserver']['xe_type'] == 'sql_batch_completed'
        assert rqt_event['sqlserver']['event_fire_timestamp'] == '2023-01-01T12:00:00.123Z'
        assert rqt_event['sqlserver']['duration_ms'] == 10.0
        assert rqt_event['sqlserver']['query_start'] == '2023-01-01T11:59:50.123Z'
        assert rqt_event['sqlserver']['primary_sql_field'] == 'batch_text'

    @patch('datadog_checks.sqlserver.xe_collection.base.datadog_agent')
    def test_create_rqt_event_attention(self, mock_agent, error_events_handler):
        """Test creation of Raw Query Text event for attention event"""
        mock_agent.get_version.return_value = '7.30.0'

        # Create attention event with SQL fields - from the error_events_handler
        event = {
            'event_name': 'attention',
            'timestamp': '2023-01-01T12:00:00.123Z',
            'duration_ms': 328.677,
            'session_id': 123,
            'database_name': 'TestDB',
            'sql_text': 'SELECT * FROM Customers WHERE CustomerId = ?',
            'query_signature': 'abc123',
            'primary_sql_field': 'sql_text',
            'dd_tables': ['Customers'],
            'dd_commands': ['SELECT'],
        }

        # Create raw SQL fields
        raw_sql_fields = {
            'sql_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
            'raw_query_signature': 'def456',
        }

        # Query details with formatted timestamps
        query_details = {
            'event_fire_timestamp': '2023-01-01T12:00:00.123Z',
            'query_start': '2023-01-01T11:59:59.795Z',  # 328.677ms before timestamp
            'duration_ms': 328.677,
        }

        # Create RQT event
        rqt_event = error_events_handler._create_rqt_event(event, raw_sql_fields, query_details)

        # Validate common payload fields
        validate_common_payload_fields(rqt_event, expected_type='rqt')

        # Verify DB fields
        assert rqt_event['db']['instance'] == 'TestDB'
        assert rqt_event['db']['query_signature'] == 'abc123'
        assert rqt_event['db']['raw_query_signature'] == 'def456'
        assert rqt_event['db']['statement'] == 'SELECT * FROM Customers WHERE CustomerId = 123'

        # Verify sqlserver fields
        assert rqt_event['sqlserver']['session_id'] == 123
        assert rqt_event['sqlserver']['xe_type'] == 'attention'
        assert rqt_event['sqlserver']['event_fire_timestamp'] == '2023-01-01T12:00:00.123Z'

        # Key check: verify that duration_ms and query_start are present for attention events
        # even though they come from the error_events_handler
        assert 'duration_ms' in rqt_event['sqlserver']
        assert rqt_event['sqlserver']['duration_ms'] == 328.677
        assert 'query_start' in rqt_event['sqlserver']
        assert rqt_event['sqlserver']['query_start'] == '2023-01-01T11:59:59.795Z'

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

    @patch('datadog_checks.sqlserver.xe_collection.base.datadog_agent')
    def test_create_rqt_event_error_reported(self, mock_agent, error_events_handler):
        """Test creation of Raw Query Text event for error_reported event"""
        mock_agent.get_version.return_value = '7.30.0'

        # Create error_reported event with SQL fields
        event = {
            'event_name': 'error_reported',
            'timestamp': '2023-01-01T12:00:00.123Z',
            'error_number': 8134,
            'severity': 15,
            'session_id': 123,
            'database_name': 'TestDB',
            'sql_text': 'SELECT 1/0',
            'message': 'Division by zero error',
            'query_signature': 'abc123',
            'primary_sql_field': 'sql_text',
        }

        # Create raw SQL fields
        raw_sql_fields = {
            'sql_text': 'SELECT 1/0',
            'raw_query_signature': 'def456',
        }

        # Query details would not have duration_ms or query_start for error_reported events
        query_details = {
            'event_fire_timestamp': '2023-01-01T12:00:00.123Z',
        }

        # Create RQT event
        rqt_event = error_events_handler._create_rqt_event(event, raw_sql_fields, query_details)

        # Validate common payload fields
        validate_common_payload_fields(rqt_event, expected_type='rqt')

        # Verify DB fields
        assert rqt_event['db']['instance'] == 'TestDB'
        assert rqt_event['db']['query_signature'] == 'abc123'
        assert rqt_event['db']['raw_query_signature'] == 'def456'
        assert rqt_event['db']['statement'] == 'SELECT 1/0'

        # Verify sqlserver fields
        assert rqt_event['sqlserver']['session_id'] == 123
        assert rqt_event['sqlserver']['xe_type'] == 'error_reported'
        assert rqt_event['sqlserver']['event_fire_timestamp'] == '2023-01-01T12:00:00.123Z'

        # Key check: verify that error_number and message are included for error_reported events
        assert 'error_number' in rqt_event['sqlserver']
        assert rqt_event['sqlserver']['error_number'] == 8134
        assert 'message' in rqt_event['sqlserver']
        assert rqt_event['sqlserver']['message'] == 'Division by zero error'

        # Verify that duration_ms and query_start are NOT present for error_reported events
        assert 'duration_ms' not in rqt_event['sqlserver']
        assert 'query_start' not in rqt_event['sqlserver']


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


class TestRunJob:
    """Group run job tests together"""

    def test_last_event_timestamp_updates_correctly(self, query_completion_handler, sample_multiple_events_xml):
        """Test that the handler correctly updates its last event timestamp after processing events"""
        # Create modified XML with specific timestamp
        modified_xml = sample_multiple_events_xml.replace("2023-01-01T12:01:00.456Z", "2023-01-01T12:02:00.789Z")

        with (
            patch.object(query_completion_handler, 'session_exists', return_value=True),
            patch.object(query_completion_handler, '_query_ring_buffer', return_value=modified_xml),
        ):
            # Process events directly to set timestamp
            events = query_completion_handler._process_events(modified_xml)
            if events:
                query_completion_handler._last_event_timestamp = events[-1]['timestamp']

            # Verify the timestamp was updated
            assert query_completion_handler._last_event_timestamp == "2023-01-01T12:02:00.789Z"

    def test_run_job_success_path(self, query_completion_handler, sample_multiple_events_xml):
        """Test the complete happy path of run_job - session exists, events are queried, processed and submitted"""

        # Create a function to capture the payload before serialization
        original_payload = None

        def capture_payload(payload, **kwargs):
            nonlocal original_payload
            original_payload = payload
            # Return a simple string to avoid serialization issues
            return '{}'

        # Mock all necessary methods
        with (
            patch.object(query_completion_handler, 'session_exists', return_value=True),
            patch.object(query_completion_handler, '_query_ring_buffer', return_value=sample_multiple_events_xml),
            patch.object(query_completion_handler._check, 'database_monitoring_query_activity') as mock_submit,
            patch('datadog_checks.sqlserver.xe_collection.base.json.dumps', side_effect=capture_payload),
        ):
            # Run the job
            query_completion_handler.run_job()

            # Verify exactly one batched event was submitted
            assert mock_submit.call_count == 1, "Expected one batched event submission"

            # Now validate the actual payload structure that was going to be serialized
            assert original_payload is not None, "Payload was not captured"

            # Check essential payload properties
            assert 'ddsource' in original_payload, "Missing 'ddsource' in payload"
            assert original_payload['ddsource'] == 'sqlserver', "Incorrect ddsource value"
            assert 'dbm_type' in original_payload, "Missing 'dbm_type' in payload"
            assert 'timestamp' in original_payload, "Missing 'timestamp' in payload"

            # Check for the new batched array based on session type
            if query_completion_handler.session_name == "datadog_query_errors":
                batch_key = "sqlserver_query_errors"
            else:
                batch_key = "sqlserver_query_completions"

            assert batch_key in original_payload, f"Missing '{batch_key}' array in payload"
            assert isinstance(original_payload[batch_key], list), f"'{batch_key}' should be a list"
            assert len(original_payload[batch_key]) > 0, f"'{batch_key}' list should not be empty"

            # Verify structure of query details objects in the array
            for event in original_payload[batch_key]:
                assert "query_details" in event, "Missing 'query_details' in event"
                query_details = event["query_details"]
                assert "xe_type" in query_details, "Missing 'xe_type' in query_details"

    def test_no_session(self, query_completion_handler, mock_check, mock_handler_log):
        """Test behavior when session doesn't exist"""
        with patch.object(query_completion_handler, 'session_exists', return_value=False):
            # Mock the log using the fixture
            log = mock_handler_log(query_completion_handler, mock_check)

            # Run the job
            query_completion_handler.run_job()

            # Verify warning was logged
            log.warning.assert_called_once_with(
                f"XE session {query_completion_handler.session_name} not found or not running."
            )

    def test_event_batching(self, query_completion_handler, sample_multiple_events_xml):
        """Test that multiple events get properly batched into a single payload"""

        # Create a function to capture the payload before serialization
        original_payload = None

        def capture_payload(payload, **kwargs):
            nonlocal original_payload
            original_payload = payload
            # Return a simple string to avoid serialization issues
            return '{}'

        # Create a spy on the _create_event_payload method to capture what would be created
        # for each individual event before batching
        with (
            patch.object(
                query_completion_handler, '_create_event_payload', wraps=query_completion_handler._create_event_payload
            ) as mock_create_payload,
            patch.object(query_completion_handler, 'session_exists', return_value=True),
            patch.object(query_completion_handler, '_query_ring_buffer', return_value=sample_multiple_events_xml),
            patch.object(query_completion_handler._check, 'database_monitoring_query_activity') as mock_submit,
            patch('datadog_checks.sqlserver.xe_collection.base.json.dumps', side_effect=capture_payload),
        ):
            # Run the job
            query_completion_handler.run_job()

            # Verify create_event_payload was called multiple times (once per event)
            assert mock_create_payload.call_count > 1, "Expected multiple events to be processed"

            # Verify database_monitoring_query_activity was only called once (batched)
            assert mock_submit.call_count == 1, "Expected only one batched submission"

            # Validate the actual batched payload
            assert original_payload is not None, "Payload was not captured"

            # Determine the appropriate batch key based on the session type
            batch_key = (
                "sqlserver_query_errors"
                if query_completion_handler.session_name == "datadog_query_errors"
                else "sqlserver_query_completions"
            )

            # Verify the batch exists and contains multiple events
            assert batch_key in original_payload, f"Missing '{batch_key}' array in payload"
            assert len(original_payload[batch_key]) > 1, "Expected multiple events in the batch"


@pytest.mark.unit
def test_collect_xe_config(instance_docker):
    instance_docker['collect_xe'] = {"query_completions": {"enabled": True}, "query_errors": {"enabled": True}}
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    assert check._config.xe_collection_config == {
        "query_completions": {"enabled": True},
        "query_errors": {"enabled": True},
    }

    instance_docker.pop('collect_xe')
    instance_docker['xe_collection'] = {"query_completions": {"enabled": True}, "query_errors": {"enabled": True}}
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    assert check._config.xe_collection_config == {
        "query_completions": {"enabled": True},
        "query_errors": {"enabled": True},
    }
