# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from lxml import etree

from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.xe_sessions.base import XESessionBase, agent_check_getter


class ErrorEventsHandler(XESessionBase):
    """Handler for Error Events and Attentions"""

    def __init__(self, check, config):
        super(ErrorEventsHandler, self).__init__(check, config, "datadog_query_errors")

    @tracked_method(agent_check_getter=agent_check_getter)
    def _process_events(self, xml_data):
        """Process error events from the XML data"""
        try:
            root = etree.fromstring(xml_data.encode('utf-8') if isinstance(xml_data, str) else xml_data)
        except Exception as e:
            self._log.error(f"Error parsing XML data: {e}")
            return []

        events = []
        self._last_processed_event_type = None

        for event in root.findall('./event')[: self.max_events]:
            try:
                # Extract basic info
                timestamp = event.get('timestamp')
                event_name = event.get('name', '')
                # Store the event type for _get_important_fields
                self._last_processed_event_type = event_name

                # Initialize event data
                event_data = {"timestamp": timestamp, "event_name": event_name}

                # Handle specific event types
                if event_name == 'xml_deadlock_report':
                    self._process_deadlock_event(event, event_data)
                elif event_name == 'error_reported':
                    self._process_error_reported_event(event, event_data)
                elif event_name == 'attention':
                    self._process_attention_event(event, event_data)
                else:
                    self._log.debug(f"Unknown event type: {event_name}, skipping")
                    continue

                events.append(event_data)
            except Exception as e:
                self._log.error(f"Error processing error event: {e}")
                continue

        return events

    def _process_deadlock_event(self, event, event_data):
        """Process xml_deadlock_report event"""
        # Extract deadlock graph
        for data in event.findall('./data'):
            if data.get('name') == 'xml_report' and data.text:
                event_data["deadlock_graph"] = data.text

        # Extract action data
        for action in event.findall('./action'):
            action_name = action.get('name')
            if action_name and action.text:
                event_data[action_name] = action.text

    def _process_error_reported_event(self, event, event_data):
        """Process error_reported event"""
        # Define field groups for error_reported events
        numeric_fields = ['error_number', 'severity', 'state', 'category']
        string_fields = ['message', 'client_hostname', 'username', 'database_name', 'client_app_name', 'sql_text']

        # Extract data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            if data_name in numeric_fields:
                self._extract_numeric_fields(data, event_data, data_name, numeric_fields)
            elif data_name in string_fields:
                self._extract_string_fields(data, event_data, data_name, string_fields)
            else:
                event_data[data_name] = self._extract_value(data)

        # Extract action elements
        for action in event.findall('./action'):
            action_name = action.get('name')
            if action_name:
                event_data[action_name] = self._extract_value(action)

    def _process_attention_event(self, event, event_data):
        """Process attention event"""
        # Define field groups for attention events
        numeric_fields = ['request_id']
        string_fields = ['client_hostname', 'username', 'database_name', 'client_app_name', 'sql_text']
        # Process duration specifically to convert to milliseconds
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue
            if data_name == 'duration':
                self._extract_duration(data, event_data)
            elif data_name in numeric_fields:
                self._extract_numeric_fields(data, event_data, data_name, numeric_fields)
            else:
                event_data[data_name] = self._extract_value(data)
        # Extract action elements
        for action in event.findall('./action'):
            action_name = action.get('name')
            if not action_name:
                continue
            if action_name == 'session_id' or action_name == 'request_id':
                # These are numeric values in the actions
                value = self._extract_int_value(action)
                if value is not None:
                    event_data[action_name] = value
            elif action_name in string_fields:
                event_data[action_name] = self._extract_value(action)
            else:
                event_data[action_name] = self._extract_value(action)

    def _normalize_event_impl(self, event):
        """Normalize error event data based on event type"""
        event_name = event.get('name', '')

        if event_name == 'error_reported':
            return self._normalize_error_reported_event(event)
        elif event_name == 'attention':
            return self._normalize_attention_event(event)

        # Default normalization for other error events
        return event

    def _normalize_error_reported_event(self, event):
        """Normalize error_reported event data"""
        # Define field types for normalization
        numeric_fields = {'error_number': 0, 'severity': 0, 'state': 0, 'category': 0, 'session_id': 0, 'request_id': 0}

        string_fields = [
            'message',
            'client_hostname',
            'username',
            'database_name',
            'client_app_name',
            'sql_text',
            'destination',
            'is_intercepted',
            'user_defined',
        ]

        return self._normalize_event(event, numeric_fields, string_fields)

    def _normalize_attention_event(self, event):
        """Normalize attention event data"""
        # Define field types for normalization
        numeric_fields = {'duration_ms': 0.0, 'request_id': 0, 'session_id': 0}  # Float for duration in ms

        string_fields = ['client_hostname', 'username', 'database_name', 'client_app_name', 'sql_text']

        return self._normalize_event(event, numeric_fields, string_fields)

    def _get_important_fields(self):
        """Define important fields for logging based on event type"""
        # Common important fields for all event types
        important_fields = ['timestamp', 'name']
        # Add event-type specific fields
        if hasattr(self, '_last_processed_event_type'):
            if self._last_processed_event_type == 'error_reported':
                important_fields.extend(['error_number', 'severity', 'message', 'sql_text'])
            elif self._last_processed_event_type == 'attention':
                important_fields.extend(['duration_ms', 'session_id', 'sql_text'])
        return important_fields

    def _get_sql_fields_to_obfuscate(self, event):
        """
        Get the SQL fields to obfuscate based on the error event type.

        Args:
            event: The event data dictionary

        Returns:
            List of field names to obfuscate for this error event type
        """
        event_name = event.get('name', '')

        if event_name == 'error_reported':
            return ['sql_text']  # error_reported events may have sql_text
        elif event_name == 'attention':
            return ['sql_text']  # attention events may have sql_text
        elif event_name == 'xml_deadlock_report':
            # No SQL to obfuscate in deadlock reports, but they may contain sensitive data in the XML
            # This could be handled in _post_process_obfuscated_event if needed
            return []
        else:
            # Default case
            return ['sql_text']

    def _get_primary_sql_field(self, event):
        """
        Get the primary SQL field for error events.
        For error events, sql_text is typically the only SQL field.

        Args:
            event: The event data dictionary

        Returns:
            Name of the primary SQL field for this event type
        """
        # For most error events, sql_text is the only SQL field
        if 'sql_text' in event and event['sql_text']:
            return 'sql_text'

        return None
