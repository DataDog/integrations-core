# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import xml.etree.ElementTree as ET

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
            root = ET.fromstring(str(xml_data))
        except Exception as e:
            self._log.error(f"Error parsing XML data: {e}")
            return []

        events = []

        for event in root.findall('./event')[: self.max_events]:
            try:
                # Extract basic info
                timestamp = event.get('timestamp')
                event_name = event.get('name', '').split('.')[-1]

                # Initialize event data
                event_data = {"timestamp": timestamp, "event_type": event_name}

                # Special processing for xml_deadlock_report
                if event_name == 'xml_deadlock_report':
                    # Extract deadlock graph
                    for data in event.findall('./data'):
                        if data.get('name') == 'xml_report' and data.text:
                            event_data["deadlock_graph"] = data.text
                    continue  # Skip standard processing

                # Extract action data
                for action in event.findall('./action'):
                    action_name = action.get('name').split('.')[-1] if action.get('name') else None
                    if action_name and action.text:
                        event_data[action_name] = action.text

                # Extract data elements - error-specific fields
                for data in event.findall('./data'):
                    data_name = data.get('name')
                    if data_name:
                        event_data[data_name] = data.text

                events.append(event_data)
            except Exception as e:
                self._log.error(f"Error processing error event: {e}")
                continue

        return events
