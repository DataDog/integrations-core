from datetime import timezone

from dateutil import parser

EVENT_TYPES = {
    'UNKNOWN': 'error',
    'INFORMATIONAL': 'info',
    'IMPORTANT': 'info',
    'CRITICAL': 'error',
}


class ClouderaEvent:
    def __init__(self, item):
        self._item = item

    def get_event(self):

        timestamp_datetime = parser.isoparse(self._item.time_occurred)
        utc_timestamp = timestamp_datetime.replace(tzinfo=timezone.utc).timestamp()

        payload = {
            "timestamp": utc_timestamp,
            "event_type": EVENT_TYPES[self._item.severity],
            "alert_type": EVENT_TYPES[self._item.severity],
            "tags": [],
            "msg_title": self._item.content,
            "msg_text": self._item.content,
        }
        return payload
