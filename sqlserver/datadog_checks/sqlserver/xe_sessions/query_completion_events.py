# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from lxml import etree

from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.xe_sessions.base import XESessionBase, agent_check_getter


class QueryCompletionEventsHandler(XESessionBase):
    """
    Combined handler for SQL query completion events:
    - sql_batch_completed - SQL batch completion
    - rpc_completed - Remote procedure call completion
    - module_end - Stored procedure, trigger, or function completion

    All events are captured in a single XE session named "datadog_query_completions".
    """

    def __init__(self, check, config):
        super(QueryCompletionEventsHandler, self).__init__(check, config, "datadog_query_completions")

    @tracked_method(agent_check_getter=agent_check_getter)
    def _process_events(self, xml_data):
        """Process all query completion event types from the XML data"""
        try:
            root = etree.fromstring(xml_data.encode('utf-8') if isinstance(xml_data, str) else xml_data)
        except Exception as e:
            self._log.error(f"Error parsing XML data: {e}")
            return []

        events = []

        for event in root.findall('./event')[: self.max_events]:
            try:
                # Determine event type based on name attribute
                event_name = event.get('name', '')

                # Basic common info from event attributes
                timestamp = event.get('timestamp')
                event_data = {"timestamp": timestamp, "event_name": event_name}

                # Process based on event type
                if event_name == 'sql_batch_completed':
                    self._process_batch_event(event, event_data)
                elif event_name == 'rpc_completed':
                    self._process_rpc_event(event, event_data)
                elif event_name == 'module_end':
                    self._process_module_event(event, event_data)
                else:
                    self._log.debug(f"Unknown event type: {event_name}, skipping")
                    continue

                events.append(event_data)
            except Exception as e:
                self._log.error(f"Error processing event {event.get('name', 'unknown')}: {e}")
                continue

        return events

    def _process_batch_event(self, event, event_data):
        """Process sql_batch_completed event"""
        # Define field groups for batch events
        numeric_fields = [
            'cpu_time',
            'page_server_reads',
            'physical_reads',
            'logical_reads',
            'writes',
            'spills',
            'row_count',
        ]
        string_fields = ['batch_text']
        text_fields = ['result']

        # Process data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Handle special case for duration
            if data_name == 'duration':
                self._extract_duration(data, event_data)
            # Handle field based on type
            elif data_name in numeric_fields:
                self._extract_numeric_fields(data, event_data, data_name, numeric_fields)
            elif data_name in string_fields:
                self._extract_string_fields(data, event_data, data_name, string_fields)
            elif data_name in text_fields:
                self._extract_text_fields(data, event_data, data_name, text_fields)
            else:
                event_data[data_name] = self._extract_value(data)

        # Process action elements
        self._process_action_elements(event, event_data)

    def _process_rpc_event(self, event, event_data):
        """Process rpc_completed event"""
        # Define field groups for RPC events
        numeric_fields = [
            'cpu_time',
            'page_server_reads',
            'physical_reads',
            'logical_reads',
            'writes',
            'spills',
            'row_count',
            'object_id',
            'line_number',
        ]
        string_fields = ['statement']
        text_fields = ['result', 'data_stream']

        # Process data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Handle special case for duration
            if data_name == 'duration':
                self._extract_duration(data, event_data)
            # Handle field based on type
            elif data_name in numeric_fields:
                self._extract_numeric_fields(data, event_data, data_name, numeric_fields)
            elif data_name in string_fields:
                self._extract_string_fields(data, event_data, data_name, string_fields)
            elif data_name in text_fields:
                self._extract_text_fields(data, event_data, data_name, text_fields)
            else:
                event_data[data_name] = self._extract_value(data)

        # Process action elements
        self._process_action_elements(event, event_data)

    def _process_module_event(self, event, event_data):
        """Process module_end event (for stored procedures, triggers, functions, etc.)"""
        # Define field groups for module events
        numeric_fields = ['source_database_id', 'object_id', 'row_count', 'line_number', 'offset', 'offset_end']
        string_fields = ['object_name', 'object_type', 'statement']

        # Process data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Handle special case for duration
            if data_name == 'duration':
                self._extract_duration(data, event_data)
            # Handle field based on type
            elif data_name in numeric_fields:
                self._extract_numeric_fields(data, event_data, data_name, numeric_fields)
            elif data_name in string_fields:
                self._extract_string_fields(data, event_data, data_name, string_fields)
            else:
                event_data[data_name] = self._extract_value(data)

        # Process action elements
        self._process_action_elements(event, event_data)

    def _process_action_elements(self, event, event_data):
        """Process common action elements for all event types"""
        for action in event.findall('./action'):
            action_name = action.get('name')
            if action_name:
                # Add activity_id support
                if action_name == 'attach_activity_id':
                    event_data['activity_id'] = self._extract_value(action)
                else:
                    event_data[action_name] = self._extract_value(action)

    def _normalize_event_impl(self, event):
        """
        Implementation of event normalization based on event type.
        """
        event_name = event.get('event_name', '')

        if event_name == 'sql_batch_completed':
            return self._normalize_batch_event(event)
        elif event_name == 'rpc_completed':
            return self._normalize_rpc_event(event)
        elif event_name == 'module_end':
            return self._normalize_module_event(event)
        else:
            # Default basic normalization
            numeric_fields = {
                "duration_ms": 0.0,
                "cpu_time": 0,
                "session_id": 0,
                "request_id": 0,
            }
            string_fields = ["sql_text", "database_name"]
            return self._normalize_event(event, numeric_fields, string_fields)

    # Define normalization field constants to avoid duplication
    _BATCH_NUMERIC_FIELDS = {
        "duration_ms": 0.0,
        "cpu_time": 0,
        "page_server_reads": 0,
        "physical_reads": 0,
        "logical_reads": 0,
        "writes": 0,
        "spills": 0,
        "row_count": 0,
        "session_id": 0,
        "request_id": 0,
    }

    _BATCH_STRING_FIELDS = [
        "result",
        "batch_text",
        "database_name",
        "username",
        "client_app_name",
        "sql_text",
        "activity_id",
        "client_hostname",
    ]

    _RPC_NUMERIC_FIELDS = {
        "duration_ms": 0.0,
        "cpu_time": 0,
        "page_server_reads": 0,
        "physical_reads": 0,
        "logical_reads": 0,
        "writes": 0,
        "spills": 0,
        "row_count": 0,
        "session_id": 0,
        "request_id": 0,
        "object_id": 0,
        "line_number": 0,
    }

    _RPC_STRING_FIELDS = [
        "result",
        "sql_text",
        "statement",
        "database_name",
        "client_hostname",
        "client_app_name",
        "object_name",
        "procedure_name",
        "data_stream",
        "activity_id",
        "username",
        "connection_reset_option",
    ]

    _MODULE_NUMERIC_FIELDS = {
        "duration_ms": 0.0,
        "source_database_id": 0,
        "object_id": 0,
        "row_count": 0,
        "line_number": 0,
        "offset": 0,
        "offset_end": 0,
        "session_id": 0,
        "request_id": 0,
    }

    _MODULE_STRING_FIELDS = [
        "object_name",
        "object_type",
        "statement",
        "sql_text",
        "client_hostname",
        "database_name",
        "client_app_name",
        "activity_id",
        "username",
    ]

    def _normalize_batch_event(self, event):
        """Normalize sql_batch_completed event data"""
        return self._normalize_event(event, self._BATCH_NUMERIC_FIELDS, self._BATCH_STRING_FIELDS)

    def _normalize_rpc_event(self, event):
        """Normalize rpc_completed event data"""
        return self._normalize_event(event, self._RPC_NUMERIC_FIELDS, self._RPC_STRING_FIELDS)

    def _normalize_module_event(self, event):
        """Normalize module_end event data (stored procedures, triggers, etc.)"""
        return self._normalize_event(event, self._MODULE_NUMERIC_FIELDS, self._MODULE_STRING_FIELDS)

    def _get_important_fields(self):
        """Get common important fields for all event types"""
        return [
            'timestamp',
            'event_name',
            'duration_ms',
            'object_name',
            'object_type',
            'statement',
            'sql_text',
            'client_app_name',
            'database_name',
            'activity_id',
        ]

    def _get_sql_fields_to_obfuscate(self, event):
        """
        Get the SQL fields to obfuscate based on the event type.
        Different event types have different SQL fields.

        Args:
            event: The event data dictionary

        Returns:
            List of field names to obfuscate for this event type
        """
        event_name = event.get('event_name', '')

        if event_name == 'sql_batch_completed':
            return ['batch_text', 'sql_text']  # batch_text is the main SQL field for batch events
        elif event_name == 'rpc_completed':
            return ['statement', 'sql_text']  # statement is the main SQL field for RPC events
        elif event_name == 'module_end':
            return ['statement', 'sql_text']  # statement is the main SQL field for module events
        else:
            # Default case - handle any SQL fields
            return ['statement', 'sql_text', 'batch_text']

    def _get_primary_sql_field(self, event):
        """
        Get the primary SQL field based on the event type.
        This is the field that will be used as the main source for query signatures.

        Args:
            event: The event data dictionary

        Returns:
            Name of the primary SQL field for this event type
        """
        event_name = event.get('event_name', '')

        if event_name == 'sql_batch_completed':
            return 'batch_text'
        elif event_name == 'rpc_completed':
            return 'statement'
        elif event_name == 'module_end':
            return 'statement'

        # Default fallback - try fields in priority order
        for field in ['statement', 'sql_text', 'batch_text']:
            if field in event and event[field]:
                return field

        return None
