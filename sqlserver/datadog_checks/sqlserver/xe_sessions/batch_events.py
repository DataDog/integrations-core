# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import xml.etree.ElementTree as ET
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.xe_sessions.base import XESessionBase, agent_check_getter

class BatchEventsHandler(XESessionBase):
    """Handler for SQL Batch Completed events"""
    
    def __init__(self, check, config):
        super(BatchEventsHandler, self).__init__(check, config, "datadog_batch")
    
    @tracked_method(agent_check_getter=agent_check_getter)
    def _process_events(self, xml_data):
        """Process batch events from the XML data - keeping SQL text unobfuscated"""
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
                
                # Get the SQL text - NOT obfuscating as per requirements
                for action in event.findall('./action'):
                    action_name = action.get('name').split('.')[-1] if action.get('name') else None
                    if action_name and action.text:
                        event_data[action_name] = action.text
                
                # Extract data elements
                for data in event.findall('./data'):
                    data_name = data.get('name')
                    if data_name == 'duration':
                        # Convert from microseconds to milliseconds
                        try:
                            event_data["duration_ms"] = int(data.text) / 1000 if data.text else None
                        except (ValueError, TypeError):
                            event_data["duration_ms"] = None
                    elif data_name:
                        event_data[data_name] = data.text
                
                events.append(event_data)
            except Exception as e:
                self._log.error(f"Error processing batch event: {e}")
                continue
                
        return events 