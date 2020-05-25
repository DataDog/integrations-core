# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import calendar
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Text, Tuple, Union

from uptime import uptime

from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.base.checks.win.wmi import WinWMICheck, from_time, to_time
from datadog_checks.base.utils.timeout import TimeoutException

from ..constants import EVENT_TYPE, INTEGER_PROPERTIES, SOURCE_TYPE_NAME


class Win32EventLogWMI(WinWMICheck):
    # WMI information
    EVENT_PROPERTIES = ["EventCode", "SourceName", "TimeGenerated", "Type"]
    EXTRA_EVENT_PROPERTIES = ["InsertionStrings", "Message", "Logfile"]
    NAMESPACE = "root\\CIMV2"
    EVENT_CLASS = "Win32_NTLogEvent"

    def __init__(self, name, init_config, instances):
        # type: (str, Dict, List[Dict]) -> None
        instances[0].update({'class': self.EVENT_CLASS, 'namespace': self.NAMESPACE})
        super(Win32EventLogWMI, self).__init__(name, init_config, instances=instances)

        # Settings
        self.instance_tags = self.instance.get('tags', [])  # type: List[str]
        self.notify = self.instance.get('notify', [])  # type: List  # What is this and why is not a documented param

        self.tag_event_id = is_affirmative(init_config.get('tag_event_id', False))  # type: bool

        default_event_priority = init_config.get('default_event_priority', 'normal')  # type: str
        self.event_priority = self.instance.get('event_priority', default_event_priority)  # type: str
        if (self.event_priority.lower() != 'normal') and (self.event_priority.lower() != 'low'):
            self.event_priority = 'normal'

        self.ltypes = self.instance.get('type', [])  # type: List[str]
        self.source_names = self.instance.get('source_name', [])  # type: List
        self.log_files = self.instance.get('log_file', [])  # type: List

        self.event_ids = self.instance.get('event_id', [])  # type: List
        self.event_format = self.instance.get('event_format')  # type: List[str]
        self.message_filters = self.instance.get('message_filters', [])  # type: List[str]

        if not (self.source_names or self.event_ids or self.message_filters or self.log_files or self.ltypes):
            raise ConfigurationError(
                'At least one of the following filters must be set: '
                'source_name, event_id, message_filters, log_file, type'
            )

        # State
        self.last_ts = None  # type: Optional[datetime]

    def check(self, _):
        # type: (Any) -> None
        # Store the last timestamp
        if self.last_ts is None:
            # If system boot was withing 600s of dd agent start then use boottime as last_ts
            if uptime() <= 600:
                self.last_ts = datetime.utcnow() - timedelta(seconds=uptime())
            else:
                self.last_ts = datetime.utcnow()
            return

        # Event properties
        event_properties = list(self.EVENT_PROPERTIES)
        if self.event_format is not None:
            event_properties.extend(list(set(self.EXTRA_EVENT_PROPERTIES) & set(self.event_format)))
        else:
            event_properties.extend(self.EXTRA_EVENT_PROPERTIES)

        # Event filters
        filters = []
        query = {}  # type: Dict[str, Union[List[Tuple[str, str]], Tuple[str, str]]]
        last_ts = self.last_ts
        query['TimeGenerated'] = ('>=', self._dt_to_wmi(last_ts))
        if self.username:
            query['User'] = ('=', self.username)
        if self.ltypes:
            query['Type'] = [('=', ltype) for ltype in self.ltypes]
        if self.source_names:
            query['SourceName'] = [('=', source_name) for source_name in self.source_names]
        if self.log_files:
            query['LogFile'] = [('=', log_file) for log_file in self.log_files]
        if self.event_ids:
            query['EventCode'] = [('=', event_id) for event_id in self.event_ids]
        if self.message_filters:
            not_message = []
            message = []
            for filt in self.message_filters:
                if filt[0] == '-':
                    not_message.append(('LIKE', filt[1:]))
                else:
                    message.append(('LIKE', filt))
            query['NOT Message'] = not_message
            query['Message'] = message

        filters.append(query)

        wmi_sampler = self.get_running_wmi_sampler(properties=event_properties, filters=filters, and_props=['Message'])
        wmi_sampler.reset_filter(new_filters=filters)
        try:
            wmi_sampler.sample()
        except TimeoutException:
            self.log.warning(
                "[Win32EventLog] WMI query timed out. class=%s - properties=%s - filters=%s - tags=%s",
                self.EVENT_CLASS,
                event_properties,
                filters,
                self.instance_tags,
            )
        else:
            for ev in wmi_sampler:
                # for local events we dont need to specify a hostname
                hostname = None if (self.host == "localhost" or self.host == ".") else self.host
                log_ev = LogEvent(
                    ev,
                    self.log,
                    hostname,
                    self.instance_tags,
                    self.notify,
                    self.tag_event_id,
                    self.event_format,
                    self.event_priority,
                )

                # Since WQL only compares on the date and NOT the time, we have to
                # do a secondary check to make sure events are after the last
                # timestamp
                if log_ev.is_after(last_ts):
                    self.event(log_ev.to_event_dict())
                else:
                    self.log.debug('Skipping event after %s. ts=%s', last_ts, log_ev.timestamp)

            # Update the last time checked
            self.last_ts = datetime.utcnow()

    def _dt_to_wmi(self, dt):
        # type: (datetime) -> str
        """
        A wrapper around wmi.from_time to get a WMI-formatted time from a time struct.
        """
        return from_time(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hours=dt.hour,
            minutes=dt.minute,
            seconds=dt.second,
            microseconds=0,
            timezone=0,
        )


class LogEvent(object):
    def __init__(self, ev, log, hostname, tags, notify_list, tag_event_id, event_format, event_priority):
        # type: (Dict, Any, Optional[str], List[str], List, bool, List[str], str) -> None
        self.event = self._normalize_event(ev.copy())
        self.log = log
        self.hostname = hostname
        self.tags = self._tags(tags, self.event['EventCode']) if tag_event_id else tags
        self.notify_list = notify_list
        self.timestamp = self._wmi_to_ts(self.event['TimeGenerated'])
        self._format = event_format
        self.event_priority = event_priority

    @staticmethod
    def _normalize_event(event):
        # type: (Dict) -> Dict
        for field in INTEGER_PROPERTIES:
            if field in event:
                event[field] = int(event[field])
        return event

    @property
    def _msg_title(self):
        # type: () -> str
        return '{logfile}/{source}'.format(logfile=self.event['Logfile'], source=self.event['SourceName'])

    @property
    def _msg_text(self):
        # type: () -> Text
        """
        Generate the event's body to send to Datadog.

        Consider `event_format` parameter:
        * Only use the specified list of event properties.
        * If unspecified, default to the EventLog's `Message` or `InsertionStrings`.
        """
        msg_text = u""

        if self._format:
            msg_text_fields = ["%%%\n```"]  # type: List[Text]

            for event_property in self._format:
                property_value = self.event.get(event_property)
                if property_value is None:
                    self.log.warning(u"Unrecognized `%s` event property.", event_property)
                    continue
                msg_text_fields.append(
                    u"{property_name}: {property_value}".format(
                        property_name=event_property, property_value=property_value
                    )
                )

            msg_text_fields.append("```\n%%%")

            msg_text = u"\n".join(msg_text_fields)
        else:
            # Override when verbosity
            if self.event.get('Message'):
                msg_text = u"{message}\n".format(message=self.event['Message'])
            elif self.event.get('InsertionStrings'):
                msg_text = u"\n".join([i_str for i_str in self.event['InsertionStrings'] if i_str.strip()])

        if self.notify_list:
            msg_text += u"\n{notify_list}".format(notify_list=' '.join([" @" + n for n in self.notify_list]))

        return msg_text

    @property
    def _alert_type(self):
        # type: () -> str
        event_type = self.event['Type']
        # Convert to a Datadog alert type
        if event_type == 'Warning':
            return 'warning'
        elif event_type == 'Error':
            return 'error'
        return 'info'

    @property
    def _aggregation_key(self):
        # type: () -> Any
        return self.event['SourceName']

    def to_event_dict(self):
        # type: () -> Dict[str, Any]
        event_dict = {
            'timestamp': self.timestamp,
            'event_type': EVENT_TYPE,
            'priority': self.event_priority,
            'msg_title': self._msg_title,
            'msg_text': self._msg_text.strip(),
            'aggregation_key': self._aggregation_key,
            'alert_type': self._alert_type,
            'source_type_name': SOURCE_TYPE_NAME,
            'tags': self.tags,
        }
        if self.hostname:
            event_dict['host'] = self.hostname

        return event_dict

    def is_after(self, ts):
        # type: (datetime) -> bool
        """ Compare this event's timestamp to a give timestamp. """
        if self.timestamp >= int(calendar.timegm(ts.timetuple())):
            return True
        return False

    def _wmi_to_ts(self, wmi_ts):
        # type: (str) -> int
        """
        Convert a wmi formatted timestamp into an epoch.
        """
        year, month, day, hour, minute, second, microsecond, tz = to_time(wmi_ts)
        tz_delta = timedelta(minutes=int(tz))
        if '+' in wmi_ts:
            tz_delta = -tz_delta

        dt = (
            datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second, microsecond=microsecond)
            + tz_delta
        )
        return int(calendar.timegm(dt.timetuple()))

    def _tags(self, tags, event_code):
        # type: (List[str], str) -> List[str]
        """
        Inject additional tags into the list already supplied to LogEvent.
        """
        tags_list = []
        if tags is not None:
            tags_list += list(tags)
        tags_list.append("event_id:{event_id}".format(event_id=event_code))
        return tags_list
