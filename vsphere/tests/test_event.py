# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import datetime as dt

import pytest
from mock import MagicMock, patch
from pyVmomi import vim

from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.legacy.event import ALLOWED_EVENTS

from .legacy.utils import mock_alarm_event


def test_allowed_event_list():
    expected_events = [
        vim.event.AlarmStatusChangedEvent,
        vim.event.TaskEvent,
        vim.event.VmBeingHotMigratedEvent,
        vim.event.VmMessageEvent,
        vim.event.VmMigratedEvent,
        vim.event.VmPoweredOnEvent,
        vim.event.VmPoweredOffEvent,
        vim.event.VmReconfiguredEvent,
        vim.event.VmSuspendedEvent,
    ]
    assert sorted(str(e) for e in expected_events) == sorted(str(e) for e in ALLOWED_EVENTS)


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_events_collection(aggregator, realtime_instance):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    check.initiate_api_connection()
    time_initial = check.latest_event_query

    time1 = dt.datetime.now()
    time2 = time1 + dt.timedelta(seconds=3)
    time3 = time1 + dt.timedelta(seconds=5)
    event1 = mock_alarm_event(from_status='green', key=10, created_time=time1)
    event2 = mock_alarm_event(from_status='yellow', key=20, created_time=time3)
    event3 = mock_alarm_event(from_status='red', key=30, created_time=time2)

    # No events
    check.check(None)
    assert len(aggregator.events) == 0
    assert check.latest_event_query > time_initial  # check time not changed if there is no event

    # 1 events
    aggregator.reset()
    check.api.mock_events = [event1]
    check.check(None)
    aggregator.assert_event("vCenter monitor status changed on this alarm, it was green and it's now red.", count=1)
    assert len(aggregator.events) == 1
    assert check.latest_event_query == time1 + dt.timedelta(seconds=1)

    # 3 events
    aggregator.reset()
    check.api.mock_events = [event2, event3, event3]
    check.check(None)
    for status, count in [('yellow', 1), ('red', 2)]:
        aggregator.assert_event(
            "vCenter monitor status changed on this alarm, it was {} and it's now red.".format(status), count=count
        )
    assert len(aggregator.events) == 3
    assert check.latest_event_query == time3 + dt.timedelta(seconds=1)


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_events_collection_safeguard(realtime_instance):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    check.initiate_api_connection()
    time_initial = check.latest_event_query

    # base case, latest_event_query set to last event datetime + 1 sec
    event1 = mock_alarm_event(from_status='green', key=10, created_time=time_initial)
    check.api.mock_events = [event1]
    check.check(None)

    assert check.latest_event_query == time_initial + dt.timedelta(seconds=1)

    # error case, latest_event_query set to collection datetime
    with patch('datadog_checks.vsphere.vsphere.dt') as mock_dt:
        collection_datetime = dt.datetime(2010, 10, 8)
        mock_dt.datetime.utcnow.return_value = collection_datetime
        check.log = MagicMock()

        check.api.get_new_events = MagicMock(side_effect=RuntimeError('my error'))
        check.check(None)

        assert check.latest_event_query == collection_datetime
        check.log.warning.assert_called_with("Unable to fetch Events %s", "my error")
