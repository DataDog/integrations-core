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

    # Event-specific field extensions
    BATCH_SPECIFIC_NUMERIC_FIELDS = {
        "cpu_time": 0,
        "page_server_reads": 0,
        "physical_reads": 0,
        "logical_reads": 0,
        "writes": 0,
        "spills": 0,
        "row_count": 0,
    }

    BATCH_SPECIFIC_STRING_FIELDS = [
        "result",
    ]

    RPC_SPECIFIC_NUMERIC_FIELDS = {
        "cpu_time": 0,
        "page_server_reads": 0,
        "physical_reads": 0,
        "logical_reads": 0,
        "writes": 0,
        "spills": 0,
        "row_count": 0,
        "object_id": 0,
        "line_number": 0,
    }

    RPC_SPECIFIC_STRING_FIELDS = [
        "result",
        "procedure_name",
        "data_stream",
        "connection_reset_option",
    ]

    MODULE_SPECIFIC_NUMERIC_FIELDS = {
        "source_database_id": 0,
        "object_id": 0,
        "row_count": 0,
        "line_number": 0,
        "offset": 0,
        "offset_end": 0,
    }

    MODULE_SPECIFIC_STRING_FIELDS = [
        "object_name",
        "object_type",
    ]

    def __init__(self, check, config):
        super(QueryCompletionEventsHandler, self).__init__(check, config, "datadog_query_completions")

        # Register handlers for different event types using the strategy pattern
        self.register_event_handler('sql_batch_completed', self._process_batch_event)
        self.register_event_handler('rpc_completed', self._process_rpc_event)
        self.register_event_handler('module_end', self._process_module_event)

    def get_numeric_fields(self, event_type=None):
        """Get numeric fields with defaults for given event type"""
        base_fields = super().get_numeric_fields(event_type)

        if event_type == 'sql_batch_completed':
            base_fields.update(self.BATCH_SPECIFIC_NUMERIC_FIELDS)
        elif event_type == 'rpc_completed':
            base_fields.update(self.RPC_SPECIFIC_NUMERIC_FIELDS)
        elif event_type == 'module_end':
            base_fields.update(self.MODULE_SPECIFIC_NUMERIC_FIELDS)

        return base_fields

    def get_string_fields(self, event_type=None):
        """Get string fields for given event type"""
        base_fields = super().get_string_fields(event_type)

        if event_type == 'sql_batch_completed':
            return base_fields + self.BATCH_SPECIFIC_STRING_FIELDS
        elif event_type == 'rpc_completed':
            return base_fields + self.RPC_SPECIFIC_STRING_FIELDS
        elif event_type == 'module_end':
            return base_fields + self.MODULE_SPECIFIC_STRING_FIELDS

        return base_fields

    @tracked_method(agent_check_getter=agent_check_getter)
    def _process_events(self, xml_data):
        """Process all query completion event types using base implementation"""
        return super()._process_events(xml_data)

    def _process_event(self, event, event_data):
        """Process a single query event - base implementation for backward compatibility"""
        event_name = event_data.get("event_name", "")

        if event_name == 'sql_batch_completed':
            return self._process_batch_event(event, event_data)
        elif event_name == 'rpc_completed':
            return self._process_rpc_event(event, event_data)
        elif event_name == 'module_end':
            return self._process_module_event(event, event_data)
        else:
            self._log.debug(f"Unknown event type: {event_name}, skipping")
            return False

    def _process_batch_event(self, event, event_data):
        """Process sql_batch_completed event"""
        # Process data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Use unified field extraction
            self._extract_field(data, event_data, data_name)

        # Process action elements
        self._process_action_elements(event, event_data)

        return True

    def _process_rpc_event(self, event, event_data):
        """Process rpc_completed event"""
        # Process data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Use unified field extraction
            self._extract_field(data, event_data, data_name)

        # Process action elements
        self._process_action_elements(event, event_data)

        return True

    def _process_module_event(self, event, event_data):
        """Process module_end event (for stored procedures, triggers, functions, etc.)"""
        # Process data elements
        for data in event.findall('./data'):
            data_name = data.get('name')
            if not data_name:
                continue

            # Use unified field extraction
            self._extract_field(data, event_data, data_name)

        # Process action elements
        self._process_action_elements(event, event_data)

        return True

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
        # All event types can use the base normalization with type-specific fields
        return self._normalize_event(event)

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
        for field in self.get_sql_fields(event_name):
            if field in event and event[field]:
                return field

        return None
