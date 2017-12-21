# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from mock import patch

# project
from tests.core.test_wmi import TestCommonWMI
from tests.checks.common import AgentCheckTest


def to_time(wmi_ts):
    "Just return any time struct"
    return (2100, 12, 24, 11, 30, 47, 0, 0)


def from_time(year=0, month=0, day=0, hours=0, minutes=0,
            seconds=0, microseconds=0, timezone=0):
    "Just return any WMI date"
    return "20151224113047.000000-480"


class TestWin32_event_log(AgentCheckTest, TestCommonWMI):
    """Basic Test for win32_event_log integration."""
    CHECK_NAME = 'win32_event_log'

    WIN_LOGEVENT_CONFIG = {
        'host': ".",
        'tags': ["mytag1", "mytag2"],
        'sites': ["Default Web Site", "Failing site"],
        'logfile': ["Application"],
        'type': ["Error", "Warning"],
        'source_name': ["MSSQLSERVER"]
    }

    @patch('checks.winwmi_check.to_time', side_effect=to_time)
    @patch('checks.winwmi_check.from_time', side_effect=from_time)
    def test_check(self, from_time, to_time):
        """
        Returns the right metrics and service checks
        """
        # Run check
        config = {
            'instances': [self.WIN_LOGEVENT_CONFIG]
        }
        self.run_check_twice(config)

        self.assertEvent(u'SomeMessage', count=1,
                         tags=self.WIN_LOGEVENT_CONFIG['tags'],
                         msg_title='Application/MSQLSERVER',
                         event_type='win32_log_event', alert_type='error',
                         source_type_name='event viewer')

        self.coverage_report()
