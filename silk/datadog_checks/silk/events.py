# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

ALERT_TYPES = {"INFO": "info", "ERROR": "error", "WARNING": "warning", "CRITICAL": "error"}


class SilkEvent(object):
    def __init__(self, raw_event, tags):
        self.payload = {
            "timestamp": raw_event.get("timestamp"),
            "event_type": raw_event.get("labels"),
            "source_type_name": 'silk',
            "alert_type": ALERT_TYPES[raw_event.get("level")],
            "tags": tags[:],
            "msg_title": raw_event.get("name"),
            "msg_text": raw_event.get("message"),
        }
        self.payload['tags'].append('user:%s' % raw_event.get("user"))

    def get_datadog_payload(self):
        return self.payload
