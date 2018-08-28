# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from mock import patch
import pytest
import logging

from datadog_checks.win32_event_log import Win32EventLogWMI

log = logging.getLogger(__file__)


class FakeWmiSampler:
    def __init__(self):
        self._wmi_objects = []

    def __getitem__(self, i):
        return self._wmi_objects[i]

    def __iter__(self):
        for wmi_object in self._wmi_objects:
            yield wmi_object

    def sample(self):
        self._wmi_objects = [
            {
                'EventCode': 0,
                'EventIdentifier': 0,
                'EventType': 0,
                'InsertionStrings': '[insertionstring]',
                'Logfile': 'Application',
                'Message': 'SomeMessage',
                'SourceName': 'MSQLSERVER',
                'TimeGenerated': '21001224113047.000000-480',
                'User': 'FooUser',
                'Type': 'Error',
            }
        ]

    def reset(self):
        self._wmi_objects = []

    def reset_filter(self, new_filters=None):
        pass


@pytest.fixture
def mock_get_wmi_sampler():
    with patch("datadog_checks.win32_event_log.Win32EventLogWMI._get_wmi_sampler", return_value=FakeWmiSampler()):
        yield


def from_time(year=0, month=0, day=0, hours=0, minutes=0,
              seconds=0, microseconds=0, timezone=0):
    "Just return any WMI date"
    return "20151224113047.000000-480"


@pytest.fixture
def mock_from_time():
    with patch('datadog_checks.checks.win.wmi.to_time', side_effect=from_time):
        yield


def to_time(wmi_ts):
    "Just return any time struct"
    return (2100, 12, 24, 11, 30, 47, 0, 0)


@pytest.fixture
def mock_to_time():
    with patch('datadog_checks.checks.win.wmi.to_time', side_effect=to_time):
        yield


@pytest.fixture
def check():
    check = Win32EventLogWMI('win32_event_log', {}, {})
    return check


def test_check(mock_from_time, mock_to_time, check, mock_get_wmi_sampler, aggregator):
    instance = {
        'host': ".",
        'tags': ["mytag1", "mytag2"],
        'sites': ["Default Web Site", "Failing site"],
        'logfile': ["Application"],
        'type': ["Error", "Warning"],
        'source_name': ["MSSQLSERVER"]
    }

    check.check(instance)
    check.check(instance)

    aggregator.assert_event('SomeMessage', count=1,
                            tags=instance['tags'],
                            msg_title='Application/MSQLSERVER',
                            event_type='win32_log_event', alert_type='error',
                            source_type_name='event viewer')
