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

    def _extract_value(self, element, default=None):
        """Helper method to extract values from XML elements with consistent handling"""
        if element is None:
            return default

        # First try to get from value element
        value_elem = element.find('./value')
        if value_elem is not None and value_elem.text:
            return value_elem.text.strip()

        # If no value element or empty, try the element's text directly
        if element.text:
            return element.text.strip()

        return default

    def _extract_int_value(self, element, default=None):
        """Helper method to extract integer values with error handling"""
        value = self._extract_value(element, default)
        if value is None:
            return default

        try:
            return int(value)
        except (ValueError, TypeError) as e:
            self._log.debug(f"Error converting to int: {e}")
            return default

    def _extract_text_representation(self, element, default=None):
        """Get the text representation when both value and text are available"""
        text_elem = element.find('./text')
        if text_elem is not None and text_elem.text:
            return text_elem.text.strip()
        return default

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
                        event_data[action_name] = self._extract_value(action)

                events.append(event_data)
            except Exception as e:
                self._log.error(f"Error processing RPC event: {e}")
                continue

        return events
