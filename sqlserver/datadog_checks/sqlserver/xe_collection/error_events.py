# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from lxml import etree

from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.xe_collection.base import XESessionBase, agent_check_getter


class ErrorEventsHandler(XESessionBase):
    """Handler for Error Events and Attentions"""

    # Event-specific field extensions
    ERROR_REPORTED_SPECIFIC_NUMERIC_FIELDS = {
        "error_number": 0,
        "severity": 0,
        "state": 0,
        "category": 0,
    }

    ERROR_REPORTED_SPECIFIC_STRING_FIELDS = [
        "message",
        "is_intercepted",
        "user_defined",
        "destination",
    ]

    ATTENTION_SPECIFIC_NUMERIC_FIELDS = {}

    ATTENTION_SPECIFIC_STRING_FIELDS = []

    def __init__(self, check, config):
        super(ErrorEventsHandler, self).__init__(check, config, "datadog_query_errors")

        # Register handlers for different event types using the strategy pattern
        self.register_event_handler('error_reported', self._process_error_reported_event)
        self.register_event_handler('attention', self._process_attention_event)

    def get_numeric_fields(self, event_type=None):
        """Get numeric fields with defaults for given event type"""
        base_fields = super().get_numeric_fields(event_type)

        if event_type == 'error_reported':
            base_fields.update(self.ERROR_REPORTED_SPECIFIC_NUMERIC_FIELDS)
        elif event_type == 'attention':
            base_fields.update(self.ATTENTION_SPECIFIC_NUMERIC_FIELDS)

        return base_fields

    def get_string_fields(self, event_type=None):
        """Get string fields for given event type"""
        base_fields = super().get_string_fields(event_type)

        if event_type == 'error_reported':
            return base_fields + self.ERROR_REPORTED_SPECIFIC_STRING_FIELDS
        elif event_type == 'attention':
            return base_fields + self.ATTENTION_SPECIFIC_STRING_FIELDS

        return base_fields

    def get_sql_fields(self, event_type=None):
        """Get SQL fields for given event type"""
        return super().get_sql_fields(event_type)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _process_events(self, xml_data):
        """Process error events from the XML data using base implementation"""
        return super()._process_events(xml_data)

    def _process_error_reported_event(self, event, event_data):
        """Process error_reported event"""
        # Extract data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Use unified field extraction
            self._extract_field(data, event_data, data_name)

        # Extract action elements
        for action in event.findall('./action'):
            action_name = action.get('name')
            if action_name:
                event_data[action_name] = self._extract_value(action)

        return True

    def _process_attention_event(self, event, event_data):
        """Process attention event"""
        # Process data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Use unified field extraction
            self._extract_field(data, event_data, data_name)

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
            else:
                event_data[action_name] = self._extract_value(action)

        return True

    def _normalize_event_impl(self, event):
        """Normalize error event data based on event type"""
        # First use the base normalization with type-specific fields
        normalized = self._normalize_event(event)

        # For error events, remove query_start and duration_ms fields since they're not applicable
        if 'query_start' in normalized:
            del normalized['query_start']
        if 'duration_ms' in normalized:
            del normalized['duration_ms']

        return normalized

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
