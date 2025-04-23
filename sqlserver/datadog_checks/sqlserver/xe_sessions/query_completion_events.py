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
        # Process data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Handle special case for duration (conversion to milliseconds)
            if data_name == 'duration':
                duration_value = self._extract_int_value(data)
                if duration_value is not None:
                    event_data["duration_ms"] = duration_value / 1000
                else:
                    event_data["duration_ms"] = None
            # Handle special case for batch_text vs SQL field name
            elif data_name == 'batch_text':
                event_data["batch_text"] = self._extract_value(data)
            # Handle special cases with text representations
            elif data_name in ['result']:
                # Try to get text representation first
                text_value = self._extract_text_representation(data)
                if text_value is not None:
                    event_data[data_name] = text_value
                else:
                    event_data[data_name] = self._extract_value(data)
            # Handle numeric fields
            elif data_name in [
                'cpu_time',
                'page_server_reads',
                'physical_reads',
                'logical_reads',
                'writes',
                'spills',
                'row_count',
            ]:
                event_data[data_name] = self._extract_int_value(data)
            # Handle all other fields
            else:
                event_data[data_name] = self._extract_value(data)

        # Process action elements
        self._process_action_elements(event, event_data)

    def _process_rpc_event(self, event, event_data):
        """Process rpc_completed event"""
        # Process data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Handle special case for duration (conversion to milliseconds)
            if data_name == 'duration':
                duration_value = self._extract_int_value(data)
                if duration_value is not None:
                    event_data["duration_ms"] = duration_value / 1000
                else:
                    event_data["duration_ms"] = None
            # Capture statement field directly
            elif data_name == 'statement':
                event_data["statement"] = self._extract_value(data)
            # Handle special cases with text representations
            elif data_name in ['result', 'data_stream']:
                # Try to get text representation first
                text_value = self._extract_text_representation(data)
                if text_value is not None:
                    event_data[data_name] = text_value
                else:
                    event_data[data_name] = self._extract_value(data)
            # Handle numeric fields
            elif data_name in [
                'cpu_time',
                'page_server_reads',
                'physical_reads',
                'logical_reads',
                'writes',
                'spills',
                'row_count',
                'object_id',
                'line_number',
            ]:
                event_data[data_name] = self._extract_int_value(data)
            # Handle all other fields
            else:
                event_data[data_name] = self._extract_value(data)

        # Process action elements
        self._process_action_elements(event, event_data)

    def _process_module_event(self, event, event_data):
        """Process module_end event (for stored procedures, triggers, functions, etc.)"""
        # Process data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Handle special case for duration (conversion to milliseconds)
            if data_name == 'duration':
                duration_value = self._extract_int_value(data)
                if duration_value is not None:
                    # Note: module_end event duration is already in microseconds
                    event_data["duration_ms"] = duration_value / 1000
                else:
                    event_data["duration_ms"] = None
            # Handle string fields
            elif data_name in ['object_name', 'object_type', 'statement']:
                event_data[data_name] = self._extract_value(data)
            # Handle numeric fields
            elif data_name in [
                'source_database_id',
                'object_id',
                'row_count',
                'line_number',
                'offset',
                'offset_end',
            ]:
                event_data[data_name] = self._extract_int_value(data)
            # Handle all other fields
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

    def _normalize_batch_event(self, event):
        """Normalize sql_batch_completed event data"""
        numeric_fields = {
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

        string_fields = ["result", "batch_text", "database_name", "client_app_name", "sql_text", "activity_id"]

        return self._normalize_event(event, numeric_fields, string_fields)

    def _normalize_rpc_event(self, event):
        """Normalize rpc_completed event data"""
        numeric_fields = {
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

        string_fields = [
            "result",
            "sql_text",
            "statement",
            "database_name",
            "client_app_name",
            "object_name",
            "procedure_name",
            "data_stream",
            "activity_id",
            "username",
            "connection_reset_option",
        ]

        return self._normalize_event(event, numeric_fields, string_fields)

    def _normalize_module_event(self, event):
        """Normalize module_end event data (stored procedures, triggers, etc.)"""
        numeric_fields = {
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

        string_fields = [
            "object_name",
            "object_type",
            "statement",
            "sql_text",
            "database_name",
            "client_app_name",
            "activity_id",
            "username",
        ]

        return self._normalize_event(event, numeric_fields, string_fields)

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