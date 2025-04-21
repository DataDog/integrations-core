# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from lxml import etree

from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.xe_sessions.base import XESessionBase, agent_check_getter


class BatchEventsHandler(XESessionBase):
    """Handler for SQL Server Batch Events"""

    def __init__(self, check, config):
        super(BatchEventsHandler, self).__init__(check, config, "datadog_batch")

    @tracked_method(agent_check_getter=agent_check_getter)
    def _process_events(self, xml_data):
        """Process batch events from the XML data"""
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
                self._log.error(f"Error processing batch event: {e}")
                continue

        return events

    def _normalize_event_impl(self, event):
        """
        Implementation of Batch event normalization with type handling.

        Expected fields:
        - timestamp: ISO8601 timestamp string
        - duration_ms: float (milliseconds)
        - cpu_time: int (microseconds)
        - page_server_reads: int
        - physical_reads: int
        - logical_reads: int
        - writes: int
        - spills: int
        - result: string ("OK", etc.)
        - row_count: int
        - batch_text: string (SQL text)
        - database_name: string
        - request_id: int
        - session_id: int
        - client_app_name: string
        - sql_text: string (may be same as batch_text)
        - activity_id: string (GUID+sequence when using TRACK_CAUSALITY)
        """
        # Define numeric fields with defaults
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

        # Define string fields
        string_fields = ["result", "batch_text", "database_name", "client_app_name", "sql_text", "activity_id"]

        # Use base class method to normalize
        return self._normalize_event(event, numeric_fields, string_fields)

    def _get_important_fields(self):
        """Get the list of important fields for Batch events logging"""
        return ['timestamp', 'batch_text', 'sql_text', 'duration_ms', 'client_app_name', 'database_name', 'activity_id']
