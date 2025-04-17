# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import xml.etree.ElementTree as ET
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.xe_sessions.base import XESessionBase, agent_check_getter

class SprocEventsHandler(XESessionBase):
    """Handler for Stored Procedure (Module End) events"""

    def __init__(self, check, config):
        super(SprocEventsHandler, self).__init__(check, config, "datadog_sprocs")

    @tracked_method(agent_check_getter=agent_check_getter)
    def _process_events(self, xml_data):
        """Process stored procedure events from the XML data"""
        try:
            root = ET.fromstring(str(xml_data))
        except Exception as e:
            self._log.error(f"Error parsing XML data: {e}")
            return []

        events = []

        for event in root.findall('./event')[:self.max_events]:
            try:
                # Extract basic info
                timestamp = event.get('timestamp')

                # Extract action data
                event_data = {
                    "timestamp": timestamp,
                }

                # Get the SQL text and other action data
                for action in event.findall('./action'):
                    action_name = action.get('name').split('.')[-1] if action.get('name') else None
                    if action_name and action.text:
                        event_data[action_name] = action.text

                # Extract data elements - stored procedure specific
                for data in event.findall('./data'):
                    data_name = data.get('name')
                    if data_name == 'duration':
                        # Convert from microseconds to milliseconds
                        try:
                            event_data["duration_ms"] = int(data.text) / 1000 if data.text else None
                        except (ValueError, TypeError):
                            event_data["duration_ms"] = None
                    elif data_name == 'statement':
                        # This is the actual SQL statement executed within the procedure
                        event_data["statement"] = data.text
                    elif data_name == 'object_name':
                        # The name of the stored procedure
                        event_data["object_name"] = data.text
                    elif data_name == 'object_type':
                        event_data["object_type"] = data.text
                    elif data_name:
                        event_data[data_name] = data.text

                events.append(event_data)
            except Exception as e:
                self._log.error(f"Error processing stored procedure event: {e}")
                continue

        return events
