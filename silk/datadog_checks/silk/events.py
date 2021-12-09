# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

ALERT_TYPES = {"INFO": "info", "ERROR": "error", "WARNING": "warning", "CRITICAL": "error"}


class SilkEvent(object):
    def __init__(self, raw_event, tags):
        self.raw_event = raw_event

        self.payload = {
            "timestamp": self.raw_event['timestamp'],
            "event_type": self.raw_event["labels"],
            "source_type_name": 'silk',
            "alert_type": ALERT_TYPES[self.raw_event["level"]],
            "tags": tags[:],
        }

    def get_datadog_payload(self):
        self.payload["msg_title"] = self.raw_event['name']
        self.payload['msg_text'] = self.raw_event['message']
        self.payload['tags'].append('user:%s' % self.raw_event['user'])

        return self.payload
