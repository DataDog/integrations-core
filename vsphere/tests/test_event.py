# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import datetime as dt

import pytest
from pyVmomi import vim

from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.event import ALLOWED_EVENTS


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

    event1 = vim.event.AlarmStatusChangedEvent()
    event1.createdTime = time1
    event1.entity = vim.event.ManagedEntityEventArgument()
    event1.entity.entity = vim.VirtualMachine(moId="vm1")
    event1.entity.name = "vm1"
    event1.alarm = vim.event.AlarmEventArgument()
    event1.alarm.name = "alarm1"
    setattr(event1, 'from', 'green')
    event1.to = 'red'
    event1.datacenter = vim.event.DatacenterEventArgument()
    event1.datacenter.name = "dc1"
    event1.fullFormattedMessage = "Green to Red"

    event2 = vim.event.AlarmStatusChangedEvent()
    event2.createdTime = time2
    event2.entity = vim.event.ManagedEntityEventArgument()
    event2.entity.entity = vim.VirtualMachine(moId="vm1")
    event2.entity.name = "vm1"
    event2.alarm = vim.event.AlarmEventArgument()
    event2.alarm.name = "alarm1"
    setattr(event2, 'from', 'yellow')
    event2.to = 'red'
    event2.datacenter = vim.event.DatacenterEventArgument()
    event2.datacenter.name = "dc1"
    event2.fullFormattedMessage = "Yellow to Red"

    event3 = vim.event.AlarmStatusChangedEvent()
    event3.createdTime = time3
    event3.entity = vim.event.ManagedEntityEventArgument()
    event3.entity.entity = vim.VirtualMachine(moId="vm1")
    event3.entity.name = "vm1"
    event3.alarm = vim.event.AlarmEventArgument()
    event3.alarm.name = "alarm1"
    setattr(event3, 'from', 'red')
    event3.to = 'red'
    event3.datacenter = vim.event.DatacenterEventArgument()
    event3.datacenter.name = "dc1"
    event3.fullFormattedMessage = "Red to Red"

    event4 = vim.event.AlarmStatusChangedEvent()
    event4.createdTime = time3
    event4.entity = vim.event.ManagedEntityEventArgument()
    event4.entity.entity = vim.ClusterComputeResource(moId="c1")
    event4.entity.name = "c1"
    event4.alarm = vim.event.AlarmEventArgument()
    event4.alarm.name = "alarm1"
    setattr(event4, 'from', 'red')
    event4.to = 'green'
    event4.datacenter = vim.event.DatacenterEventArgument()
    event4.datacenter.name = "dc1"
    event4.fullFormattedMessage = "Red to Green"

    # No events
    check.check(None)
    assert len(aggregator.events) == 0
    assert check.latest_event_query > time_initial  # check time not changed if there is no event

    # 1 events
    aggregator.reset()
    check.api.mock_events = [event1]
    check.check(None)
    aggregator.assert_event(
        "vCenter monitor status changed on this alarm, it was green and it's now red.",
        count=1,
        tags=['vcenter_server:FAKE'],
    )
    assert len(aggregator.events) == 1
    assert aggregator.events[0]['msg_title'] == "[Triggered] alarm1 on VM vm1 is now red"
    assert check.latest_event_query == time1 + dt.timedelta(seconds=1)

    # 3 events
    aggregator.reset()
    check.api.mock_events = [event2, event3, event3, event4]
    check.check(None)
    for from_status, to_status, count in [('yellow', 'red', 1), ('red', 'red', 2)]:
        aggregator.assert_event(
            "vCenter monitor status changed on this alarm, it was {} and it's now {}.".format(from_status, to_status),
            tags=['vcenter_server:FAKE'],
            count=count,
        )
    assert len(aggregator.events) == 3
    assert check.latest_event_query == time3 + dt.timedelta(seconds=1)

    aggregator.reset()
    realtime_instance['event_resource_filters'] = ['vm', 'host', 'DATAcenter', 'Cluster', 'datastore']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    check.initiate_api_connection()

    check.api.mock_events = [event2, event3, event3, event4]
    check.check(None)
    for from_status, to_status, count, additional_tags in [
        ('yellow', 'red', 1, []),
        ('red', 'red', 2, []),
        ('red', 'green', 1, ['vsphere_type:cluster', 'vsphere_resource:c1']),
    ]:
        aggregator.assert_event(
            "vCenter monitor status changed on this alarm, it was {} and it's now {}.".format(from_status, to_status),
            tags=additional_tags + ['vcenter_server:FAKE'],
            count=count,
        )
    assert len(aggregator.events) == 4
    assert check.latest_event_query == time3 + dt.timedelta(seconds=1)

    aggregator.reset()
    realtime_instance['event_resource_filters'] = ['host', 'datacenter', 'cluster', 'datastore']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    check.initiate_api_connection()

    check.api.mock_events = [event2, event3, event3, event4]
    check.check(None)
    for from_status, to_status, count, additional_tags in [
        ('red', 'green', 1, ['vsphere_type:cluster', 'vsphere_resource:c1'])
    ]:
        aggregator.assert_event(
            "vCenter monitor status changed on this alarm, it was {} and it's now {}.".format(from_status, to_status),
            tags=additional_tags + ['vcenter_server:FAKE'],
            count=count,
        )
    assert len(aggregator.events) == 1
    assert aggregator.events[0]['msg_title'] == "[Recovered] alarm1 on cluster c1 is now green"
    assert check.latest_event_query == time3 + dt.timedelta(seconds=1)

    aggregator.reset()
    realtime_instance['event_resource_filters'] = []
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    check.initiate_api_connection()

    check.api.mock_events = [event2, event3, event3, event4]
    check.check(None)
    assert len(aggregator.events) == 0
    assert check.latest_event_query == time3 + dt.timedelta(seconds=1)

    with pytest.raises(Exception, match=r"Invalid resource type specified in `event_resource_filters`: hey."):
        realtime_instance['event_resource_filters'] = ['hey']
        check = VSphereCheck('vsphere', {}, [realtime_instance])
