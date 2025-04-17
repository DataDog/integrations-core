# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import xml.etree.ElementTree as ET
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.xe_sessions.base import XESessionBase, agent_check_getter

class RPCEventsHandler(XESessionBase):
    """Handler for RPC Completed events"""

    def __init__(self, check, config):
        super(RPCEventsHandler, self).__init__(check, config, "datadog_rpc")

    @tracked_method(agent_check_getter=agent_check_getter)
    def _process_events(self, xml_data):
        """Process RPC events from the XML data - keeping SQL text unobfuscated"""
        try:
            root = ET.fromstring(str(xml_data))
        except Exception as e:
            self._log.error(f"Error parsing XML data: {e}")
            return []

        events = []

        # Log the raw XML data for debugging if needed
        # self._log.debug(f"Raw XML data: {str(xml_data)[:500]}...")

        for event in root.findall('./event')[:self.max_events]:
            try:
                # Extract basic info from event attributes
                event_data = {
                    "timestamp": event.get('timestamp'),
                }

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
                    # Handle special cases with text representations
                    elif data_name in ['result', 'connection_reset_option']:
                        # Try to get text representation first
                        text_value = self._extract_text_representation(data)
                        if text_value is not None:
                            event_data[data_name] = text_value
                        else:
                            event_data[data_name] = self._extract_value(data)
                    # Handle numeric fields
                    elif data_name in ['cpu_time', 'page_server_reads', 'physical_reads', 'logical_reads', 
                                      'writes', 'row_count']:
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
                self._log.error(f"Error processing RPC event: {e}")
                continue

        return events

    def _normalize_event_impl(self, event):
        """
        Implementation of RPC event normalization with type handling.

        Expected fields:
        - timestamp: ISO8601 timestamp string
        - duration_ms: float (milliseconds)
        - cpu_time: int (microseconds)
        - page_server_reads: int
        - physical_reads: int
        - logical_reads: int
        - writes: int
        - result: string ("OK", etc.)
        - row_count: int
        - connection_reset_option: string
        - object_name: string (procedure name)
        - statement: string (SQL text)
        - data_stream: binary (nullable)
        - output_parameters: string (nullable)
        - username: string
        - database_name: string
        - request_id: int
        - session_id: int
        - client_app_name: string
        - sql_text: string
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
            "row_count": 0,
            "session_id": 0,
            "request_id": 0
        }

        # Define string fields
        string_fields = [
            "result", "connection_reset_option", "object_name", "statement",
            "username", "database_name", "client_app_name", "sql_text",
            "activity_id"
        ]

        # Use base class method to normalize
        return self._normalize_event(event, numeric_fields, string_fields)

    def _get_important_fields(self):
        """Get the list of important fields for RPC events logging"""
        return ['timestamp', 'sql_text', 'duration_ms', 'statement', 'client_app_name', 'database_name', 'activity_id']
