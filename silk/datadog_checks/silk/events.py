# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from .constants import ALERT_TYPES


def _validate_event(raw_event):
    if raw_event.get("timestamp") is None:
        raise ValueError("Event has no timestamp, will not submit event")
    if raw_event.get("name") is None:
        raise ValueError("Event has no name, will not submit event")
    if raw_event.get("message") is None:
        raise ValueError("Event has no message, will not submit event")


class SilkEvent(object):
    def __init__(self, raw_event=None, tags=None):
        if raw_event is None:
            raw_event = {}
        if tags is None:
            tags = []

        _validate_event(raw_event)

        self.payload = {
            "timestamp": raw_event.get("timestamp"),
            "event_type": raw_event.get("labels"),
            "alert_type": ALERT_TYPES[raw_event.get("level", "ERROR")],
            "tags": tags[:],
            "msg_title": raw_event.get("name"),
            "msg_text": raw_event.get("message"),
        }
        self.payload['tags'].append('user:%s' % raw_event.get("user"))

    def get_datadog_payload(self):
        return self.payload
