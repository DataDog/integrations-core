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

        for event in root.findall('./event')[: self.max_events]:
            try:
                # Extract basic info
                timestamp = event.get('timestamp')
                event_name = event.get('name', '')

                # Initialize event data
                event_data = {"timestamp": timestamp, "name": event_name}

                # Handle specific event types
                if event_name == 'xml_deadlock_report':
                    self._process_deadlock_event(event, event_data)
                elif event_name == 'error_reported':
                    self._process_error_reported_event(event, event_data)
                else:
                    # Generic processing for other error events
                    self._process_generic_error_event(event, event_data)

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
        # Extract data elements
        for data in event.findall('./data'):
            name = data.get('name')
            if name:
                value = self._extract_value(data)
                if value is not None:
                    event_data[name] = value

        # Extract action elements
        for action in event.findall('./action'):
            name = action.get('name')
            if name:
                value = self._extract_value(action)
                if value is not None:
                    event_data[name] = value

    def _process_generic_error_event(self, event, event_data):
        """Process other error event types"""
        # Extract action data
        for action in event.findall('./action'):
            action_name = action.get('name')
            if action_name:
                event_data[action_name] = self._extract_value(action)

        # Extract data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if data_name:
                event_data[data_name] = self._extract_value(data)

    def _normalize_event_impl(self, event):
        """Normalize error event data based on event type"""
        event_name = event.get('name', '')

        if event_name == 'error_reported':
            return self._normalize_error_reported_event(event)

        # Default normalization for other error events
        return event

    def _normalize_error_reported_event(self, event):
        """Normalize error_reported event data"""
        # Define field types for normalization
        numeric_fields = {
            'error_number': 0,
            'severity': 0,
            'state': 0,
            'category': 0,
            'session_id': 0,
            'request_id': 0
        }

        string_fields = [
            'message', 'server_instance_name', 'client_hostname',
            'username', 'database_name', 'client_app_name', 'sql_text',
            'destination', 'is_intercepted', 'user_defined'
        ]

        return self._normalize_event(event, numeric_fields, string_fields)

    def _get_important_fields(self):
        """Define important fields for logging based on event type"""
        return ['timestamp', 'name', 'error_number', 'severity', 'message', 'sql_text']
