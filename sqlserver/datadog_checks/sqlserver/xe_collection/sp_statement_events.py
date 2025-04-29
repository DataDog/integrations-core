# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from lxml import etree

from datadog_checks.base.utils.tracking import tracked_method

from .base import XESessionBase, agent_check_getter


class SpStatementEventsHandler(XESessionBase):
    """Handler for Stored Procedure Statement Completed events"""

    def __init__(self, check, config):
        super(SpStatementEventsHandler, self).__init__(check, config, "datadog_sp_statement")

    @tracked_method(agent_check_getter=agent_check_getter)
    def _process_events(self, xml_data):
        """Process stored procedure statement events from the XML data"""
        try:
            root = etree.fromstring(xml_data.encode('utf-8') if isinstance(xml_data, str) else xml_data)
        except Exception as e:
            self._log.error(f"Error parsing XML data: {e}")
            return []

        events = []

        for event in root.findall('./event')[: self.max_events]:
            try:
                # Extract basic info from event attributes
                timestamp = event.get('timestamp')
                event_data = {"timestamp": timestamp}

                # Define field groups for SP statement events
                numeric_fields = [
                    'source_database_id',
                    'object_id',
                    'cpu_time',
                    'page_server_reads',
                    'physical_reads',
                    'logical_reads',
                    'writes',
                    'spills',
                    'row_count',
                    'last_row_count',
                    'nest_level',
                    'line_number',
                    'offset',
                    'offset_end',
                ]
                string_fields = ['object_name', 'statement']
                text_fields = ['object_type']

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
                    # Handle all other fields
                    else:
                        event_data[data_name] = self._extract_value(data)

                # Process action elements
                for action in event.findall('./action'):
                    action_name = action.get('name')
                    if action_name:
                        # Add activity_id support
                        if action_name == 'attach_activity_id':
                            event_data['activity_id'] = self._extract_value(action)
                        else:
                            event_data[action_name] = self._extract_value(action)

                events.append(event_data)
            except Exception as e:
                self._log.error(f"Error processing SP statement event: {e}")
                continue

        return events

    def _normalize_event_impl(self, event):
        """
        Implementation of stored procedure statement event normalization with type handling.

        Expected fields:
        - timestamp: ISO8601 timestamp string
        - duration_ms: float (milliseconds)
        - source_database_id: int
        - object_id: int
        - object_type: string (e.g., "PROC")
        - cpu_time: int (microseconds)
        - page_server_reads: int
        - physical_reads: int
        - logical_reads: int
        - writes: int
        - spills: int
        - row_count: int
        - last_row_count: int
        - nest_level: int
        - line_number: int
        - offset: int
        - offset_end: int
        - object_name: string (name of the stored procedure)
        - statement: string (SQL statement text)
        - database_name: string
        - request_id: int
        - session_id: int
        - client_app_name: string
        - sql_text: string (may be different from statement, showing calling context)
        - activity_id: string (GUID+sequence when using TRACK_CAUSALITY)
        """
        # Define numeric fields with defaults
        numeric_fields = {
            "duration_ms": 0.0,
            "source_database_id": 0,
            "object_id": 0,
            "cpu_time": 0,
            "page_server_reads": 0,
            "physical_reads": 0,
            "logical_reads": 0,
            "writes": 0,
            "spills": 0,
            "row_count": 0,
            "last_row_count": 0,
            "nest_level": 0,
            "line_number": 0,
            "offset": 0,
            "offset_end": 0,
            "session_id": 0,
            "request_id": 0,
        }

        # Define string fields
        string_fields = [
            "object_type",
            "object_name",
            "statement",
            "database_name",
            "client_app_name",
            "sql_text",
            "activity_id",
        ]

        # Use base class method to normalize
        return self._normalize_event(event, numeric_fields, string_fields)

    def _get_important_fields(self):
        """Get the list of important fields for SP statement events logging"""
        return [
            'timestamp',
            'object_name',
            'object_type',
            'statement',
            'sql_text',
            'duration_ms',
            'nest_level',
            'cpu_time',
            'logical_reads',
            'client_app_name',
            'database_name',
            'activity_id',
        ]
