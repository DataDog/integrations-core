# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime
import os
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from lxml import etree


from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.sqlserver.xe_collection.base import TimestampHandler, XESessionBase


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
    check.connection = Mock()
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
        'query_completions': {'collection_interval': 10},
        'query_errors': {'collection_interval': 20},
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


# Basic mock implementation of XESessionBase for testing
class MockXESession(XESessionBase):
    """Mock implementation of XESessionBase for testing abstract methods"""

    def _normalize_event_impl(self, event):
        """Implement the abstract method"""
        return self._normalize_event(event)

    def _get_primary_sql_field(self, event):
        """Override to provide a consistent primary field"""
        for field in ['statement', 'sql_text', 'batch_text']:
            if field in event and event[field]:
                return field
        return None

    # Add test event handlers
    def register_test_handlers(self):
        """Register test event handlers for different event types"""
        self.register_event_handler("sql_batch_completed", self._handle_sql_batch)
        self.register_event_handler("rpc_completed", self._handle_rpc)
        self.register_event_handler("error_reported", self._handle_error)

    def _handle_sql_batch(self, event, event_data):
        """Handler for sql_batch_completed events"""
        # Extract common fields
        for data in event.findall('./data'):
            name = data.get('name')
            self._extract_field(data, event_data, name)
        for action in event.findall('./action'):
            name = action.get('name')
            self._extract_field(action, event_data, name)
        return True

    def _handle_rpc(self, event, event_data):
        """Handler for rpc_completed events"""
        # Extract common fields
        for data in event.findall('./data'):
            name = data.get('name')
            self._extract_field(data, event_data, name)
        for action in event.findall('./action'):
            name = action.get('name')
            self._extract_field(action, event_data, name)
        return True

    def _handle_error(self, event, event_data):
        """Handler for error_reported events"""
        # Extract common fields
        for data in event.findall('./data'):
            name = data.get('name')
            self._extract_field(data, event_data, name)
        for action in event.findall('./action'):
            name = action.get('name')
            self._extract_field(action, event_data, name)
        return True


class TestXESessionBase:
    """Tests for the XESessionBase class"""

    def test_initialization(self, mock_check, mock_config):
        """Test initialization with different session types"""
        # Test initialization with query completions session
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")
        assert session.session_name == "datadog_query_completions"
        assert session.collection_interval == 10
        assert session._enabled is True

        # Test initialization with query errors session
        session = MockXESession(mock_check, mock_config, "datadog_query_errors")
        assert session.session_name == "datadog_query_errors"
        assert session.collection_interval == 20
        assert session._enabled is True

        # Test initialization with unknown session type
        session = MockXESession(mock_check, mock_config, "unknown_session")
        assert session.session_name == "unknown_session"
        # Should use default interval since it's not in the config
        assert session.collection_interval == 10
        assert session._enabled is True

    def test_session_exists(self, mock_check, mock_config):
        """Test session existence checking"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

        # Mock cursor and result
        cursor_mock = MagicMock()
        mock_check.connection.get_managed_cursor.return_value.__enter__.return_value = cursor_mock

        # Test when session exists
        cursor_mock.fetchone.return_value = [1]  # Session exists
        assert session.session_exists() is True

        # Test when session does not exist
        cursor_mock.fetchone.return_value = None  # No session
        assert session.session_exists() is False

    def test_extract_value(self, mock_check, mock_config):
        """Test extraction of values from XML elements"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

        # Test extracting value from element with value element
        xml = '<data name="test"><value>test_value</value></data>'
        element = etree.fromstring(xml)
        assert session._extract_value(element) == 'test_value'

        # Test extracting value from element with text
        xml = '<data name="test">test_value</data>'
        element = etree.fromstring(xml)
        assert session._extract_value(element) == 'test_value'

        # Test empty element
        xml = '<data name="test"></data>'
        element = etree.fromstring(xml)
        assert session._extract_value(element) == None
        assert session._extract_value(element, 'default') == 'default'

        # Test None element
        assert session._extract_value(None) == None
        assert session._extract_value(None, 'default') == 'default'

    def test_extract_int_value(self, mock_check, mock_config):
        """Test extraction of integer values"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

        # Test valid integer
        xml = '<data name="test"><value>123</value></data>'
        element = etree.fromstring(xml)
        assert session._extract_int_value(element) == 123

        # Test invalid integer
        xml = '<data name="test"><value>not_a_number</value></data>'
        element = etree.fromstring(xml)
        assert session._extract_int_value(element) == None
        assert session._extract_int_value(element, 0) == 0

        # Test empty element
        xml = '<data name="test"></data>'
        element = etree.fromstring(xml)
        assert session._extract_int_value(element) == None
        assert session._extract_int_value(element, 0) == 0

    def test_extract_text_representation(self, mock_check, mock_config):
        """Test extraction of text representation"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

        # Test with text element
        xml = '<data name="test"><value>123</value><text>text_value</text></data>'
        element = etree.fromstring(xml)
        assert session._extract_text_representation(element) == 'text_value'

        # Test without text element
        xml = '<data name="test"><value>123</value></data>'
        element = etree.fromstring(xml)
        assert session._extract_text_representation(element) == None
        assert session._extract_text_representation(element, 'default') == 'default'

    def test_process_events_sql_batch(self, mock_check, mock_config, sample_sql_batch_event_xml):
        """Test processing of SQL batch completed events"""
        # Create session and register handlers
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")
        session.register_test_handlers()

        # Wrap the single event in an events tag
        xml_data = f"<events>{sample_sql_batch_event_xml}</events>"

        # Process the events
        events = session._process_events(xml_data)

        # Verify the event was processed correctly
        assert len(events) == 1
        event = events[0]
        assert event['event_name'] == 'sql_batch_completed'
        assert event['timestamp'] == '2025-04-24T20:56:52.809Z'
        assert event['duration_ms'] == 4.829704  # 4829704 / 1000000 (microseconds to milliseconds)
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

    def test_process_events_rpc_completed(self, mock_check, mock_config, sample_rpc_completed_event_xml):
        """Test processing of RPC completed events"""
        # Create session and register handlers
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")
        session.register_test_handlers()

        # Wrap the single event in an events tag
        xml_data = f"<events>{sample_rpc_completed_event_xml}</events>"

        # Process the events
        events = session._process_events(xml_data)

        # Verify the event was processed correctly
        assert len(events) == 1
        event = events[0]
        assert event['event_name'] == 'rpc_completed'
        assert event['timestamp'] == '2025-04-24T20:57:04.937Z'
        assert event['duration_ms'] == 2.699535  # 2699535 / 1000000 (microseconds to milliseconds)
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

    def test_process_events_error_reported(self, mock_check, mock_config, sample_error_event_xml):
        """Test processing of error reported events"""
        # Create session and register handlers
        session = MockXESession(mock_check, mock_config, "datadog_query_errors")
        session.register_test_handlers()

        # Wrap the single event in an events tag
        xml_data = f"<events>{sample_error_event_xml}</events>"

        # Process the events
        events = session._process_events(xml_data)

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

    def test_process_events_multiple(self, mock_check, mock_config, sample_multiple_events_xml):
        """Test processing of multiple events"""
        # Create session and register handlers
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")
        session.register_test_handlers()

        # Process the events
        events = session._process_events(sample_multiple_events_xml)

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

        # Check third event (error_reported)
        assert events[2]['event_name'] == 'error_reported'
        assert events[2]['timestamp'] == '2023-01-01T12:02:00.789Z'
        assert events[2]['error_number'] == 8134
        assert events[2]['session_id'] == 125

    @patch('datadog_checks.sqlserver.xe_collection.base.obfuscate_sql_with_metadata')
    @patch('datadog_checks.sqlserver.xe_collection.base.compute_sql_signature')
    def test_obfuscate_sql_fields(self, mock_compute_signature, mock_obfuscate, mock_check, mock_config):
        """Test SQL field obfuscation and signature creation"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

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

        obfuscated_event, raw_sql_fields = session._obfuscate_sql_fields(event)

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

    def test_normalize_event(self, mock_check, mock_config):
        """Test event normalization"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

        # Test event with all fields
        event = {
            'event_name': 'sql_batch_completed',
            'timestamp': '2023-01-01T12:00:00.123Z',
            'duration': 10000,  # microseconds
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

        normalized = session._normalize_event_impl(event)

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

    def test_determine_dbm_type(self, mock_check, mock_config):
        """Test determination of DBM type based on session name"""
        # Test query completion sessions
        for session_name in ["datadog_query_completions", "datadog_sql_statement", "datadog_sp_statement"]:
            session = MockXESession(mock_check, mock_config, session_name)
            assert session._determine_dbm_type() == "query_completion"

        # Test query error session
        session = MockXESession(mock_check, mock_config, "datadog_query_errors")
        assert session._determine_dbm_type() == "query_error"

        # Test unknown session
        session = MockXESession(mock_check, mock_config, "unknown_session")
        assert session._determine_dbm_type() == "query_completion"  # Default

    @patch('time.time')
    @patch('datadog_agent.get_version')
    def test_create_event_payload(self, mock_get_version, mock_time, mock_check, mock_config):
        """Test creation of event payload"""
        mock_time.return_value = 1609459200  # 2021-01-01 00:00:00
        mock_get_version.return_value = "7.30.0"

        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

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
        payload = session._create_event_payload(raw_event)

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

    @patch('time.time')
    def test_create_rqt_event(self, mock_time, mock_check, mock_config):
        """Test creation of Raw Query Text event"""
        mock_time.return_value = 1609459200  # 2021-01-01 00:00:00

        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

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
        rqt_event = session._create_rqt_event(event, raw_sql_fields, query_details)

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
    def test_filter_ring_buffer_events(self, mock_time, mock_check, mock_config):
        """Test filtering of ring buffer events based on timestamp"""
        mock_time.return_value = 1609459200  # 2021-01-01 00:00:00

        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

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
        filtered_events = session._filter_ring_buffer_events(xml_data)
        assert len(filtered_events) == 3

        # Set last event timestamp
        session._last_event_timestamp = "2023-01-01T12:01:00.456Z"

        # Test with timestamp filter (subsequent run)
        filtered_events = session._filter_ring_buffer_events(xml_data)
        assert len(filtered_events) == 1  # Only the event after 12:01:00.456Z
        assert "2023-01-01T12:02:00.789Z" in filtered_events[0]

    def test_create_rqt_event_disabled(self, mock_check, mock_config):
        """Test RQT event creation when disabled"""
        # Disable raw query collection
        mock_config.collect_raw_query_statement["enabled"] = False

        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

        event = {
            'event_name': 'sql_batch_completed',
            'timestamp': '2023-01-01T12:00:00.123Z',
            'query_signature': 'abc123'  # Add query_signature to avoid assertion failure
        }

        raw_sql_fields = {
            'batch_text': 'SELECT * FROM Customers WHERE CustomerId = 123',
            'raw_query_signature': 'def456',
        }

        query_details = {
            'event_fire_timestamp': '2023-01-01T12:00:00.123Z',
        }

        # Should return None when disabled
        assert session._create_rqt_event(event, raw_sql_fields, query_details) is None

    def test_create_rqt_event_missing_signature(self, mock_check, mock_config):
        """Test RQT event creation with missing query signature"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

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
        assert session._create_rqt_event(event, raw_sql_fields, query_details) is None

    def test_malformed_xml(self, mock_check, mock_config):
        """Test handling of malformed XML"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")
        session.register_test_handlers()

        # Malformed XML data
        xml_data = "<events><event>Malformed XML</x></events>"

        # Should return empty list and not raise exception
        events = session._process_events(xml_data)
        assert events == []

    @patch('time.time')
    @patch('datadog_checks.sqlserver.xe_collection.base.json')
    def test_run_job_success(self, mock_json, mock_time, mock_check, mock_config, sample_multiple_events_xml):
        """Test successful run_job execution"""
        mock_time.return_value = 1609459200  # 2021-01-01 00:00:00

        session = MockXESession(mock_check, mock_config, "datadog_query_completions")
        session.register_test_handlers()

        # Mock session_exists
        with patch.object(session, 'session_exists', return_value=True):
            # Mock ring buffer query
            with patch.object(session, '_query_ring_buffer', return_value=(sample_multiple_events_xml, 0.1, 0.1)):
                # Run the job
                session.run_job()

                # Ensure the last event timestamp was updated
                assert session._last_event_timestamp == "2023-01-01T12:02:00.789Z"

    def test_run_job_no_session(self, mock_check, mock_config):
        """Test run_job when session doesn't exist"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

        # Mock session_exists to return False
        with patch.object(session, 'session_exists', return_value=False):
            # Run the job - should just log a warning and return
            session.run_job()
            mock_check.log.warning.assert_called_once()

    def test_run_job_no_data(self, mock_check, mock_config):
        """Test run_job when no data is returned"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

        # Mock session_exists to return True
        with patch.object(session, 'session_exists', return_value=True):
            # Mock query_ring_buffer to return None
            with patch.object(session, '_query_ring_buffer', return_value=(None, 0.1, 0.1)):
                # Run the job - should log a debug message and return
                session.run_job()
                mock_check.log.debug.assert_called()

    def test_run_job_processing_error(self, mock_check, mock_config):
        """Test run_job with processing error"""
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")

        # Mock session_exists to return True
        with patch.object(session, 'session_exists', return_value=True):
            # Mock query_ring_buffer to return XML
            with patch.object(session, '_query_ring_buffer', return_value=("<events>test</events>", 0.1, 0.1)):
                # Mock process_events to raise an exception
                with patch.object(session, '_process_events', side_effect=Exception("Test error")):
                    # Run the job - should catch exception and log error
                    session.run_job()
                    mock_check.log.error.assert_called()

    def test_check_azure_status(self, mock_check, mock_config):
        """Test Azure SQL Database detection"""
        # Test non-Azure SQL Server
        mock_check.static_info_cache = {'engine_edition': 'Standard Edition'}
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")
        assert session._is_azure_sql_database is False

        # Test Azure SQL Database
        mock_check.static_info_cache = {'engine_edition': 'Azure SQL Database'}
        session = MockXESession(mock_check, mock_config, "datadog_query_completions")
        assert session._is_azure_sql_database is True
