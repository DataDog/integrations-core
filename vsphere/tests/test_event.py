# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import datetime as dt

import mock
import pytest
from pyVmomi import vim

from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.constants import EXCLUDE_FILTERS

from .mocked_api import MockedAPI


def mock_api_with_events(events):
    def get_infrastructure():
        return {}

    def get_perf_counter_by_level(_):
        return {}

    def get_new_events(start_time):
        return events

    def create_mocked_api(config, log):
        mocked_api = MockedAPI(config, log)
        mocked_api.get_new_events = mock.MagicMock(side_effect=get_new_events)
        mocked_api.get_infrastructure = mock.MagicMock(side_effect=get_infrastructure)
        mocked_api.get_perf_counter_by_level = mock.MagicMock(side_effect=get_perf_counter_by_level)
        return mocked_api

    return mock.MagicMock(side_effect=create_mocked_api)


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
    allowed_events = [getattr(vim.event, event_type) for event_type in EXCLUDE_FILTERS.keys()]
    assert sorted(str(e) for e in expected_events) == sorted(str(e) for e in allowed_events)


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_events_collection_no_events(aggregator, realtime_instance, dd_run_check, mock_api):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    time_initial = check.latest_event_query
    mock_api.side_effect = mock_api_with_events([])
    dd_run_check(check)

    dd_run_check(check)

    assert len(aggregator.events) == 0
    assert check.latest_event_query > time_initial  # check time not changed if there is no event


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_events_collection_one_event(aggregator, realtime_instance, dd_run_check, mock_api):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    time1 = dt.datetime.now()
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
    mock_api.side_effect = mock_api_with_events([event1])

    dd_run_check(check)

    aggregator.assert_event(
        "vCenter monitor status changed on this alarm, it was green and it's now red.",
        count=1,
        tags=['vcenter_server:FAKE'],
    )
    assert len(aggregator.events) == 1
    assert aggregator.events[0]['msg_title'] == "[Triggered] alarm1 on VM vm1 is now red"
    assert check.latest_event_query == time1 + dt.timedelta(seconds=1)


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_events_collection_three_events(aggregator, realtime_instance, dd_run_check, mock_api):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    time1 = dt.datetime.now()
    time2 = time1 + dt.timedelta(seconds=3)
    time3 = time1 + dt.timedelta(seconds=5)
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
    mock_api.side_effect = mock_api_with_events([event2, event3, event3, event4])

    dd_run_check(check)

    for from_status, to_status, count in [('yellow', 'red', 1), ('red', 'red', 2)]:
        aggregator.assert_event(
            "vCenter monitor status changed on this alarm, it was {} and it's now {}.".format(from_status, to_status),
            tags=['vcenter_server:FAKE'],
            count=count,
        )
    assert len(aggregator.events) == 3
    assert check.latest_event_query == time3 + dt.timedelta(seconds=1)


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_events_collection_three_events_with_event_resource_filters_all(
    aggregator, realtime_instance, dd_run_check, mock_api
):
    realtime_instance['event_resource_filters'] = ['vm', 'host', 'DATAcenter', 'Cluster', 'datastore']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    time1 = dt.datetime.now()
    time2 = time1 + dt.timedelta(seconds=3)
    time3 = time1 + dt.timedelta(seconds=5)
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
    mock_api.side_effect = mock_api_with_events([event2, event3, event3, event4])

    dd_run_check(check)

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


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_events_collection_three_events_with_event_resource_filters_no_vm(
    aggregator, realtime_instance, dd_run_check, mock_api
):
    realtime_instance['event_resource_filters'] = ['host', 'datacenter', 'cluster', 'datastore']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    time1 = dt.datetime.now()
    time2 = time1 + dt.timedelta(seconds=3)
    time3 = time1 + dt.timedelta(seconds=5)
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
    mock_api.side_effect = mock_api_with_events([event2, event3, event3, event4])

    dd_run_check(check)

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


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_events_collection_three_events_with_event_resource_filters_empty(
    aggregator, realtime_instance, dd_run_check, mock_api
):
    realtime_instance['event_resource_filters'] = []
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    time1 = dt.datetime.now()
    time2 = time1 + dt.timedelta(seconds=3)
    time3 = time1 + dt.timedelta(seconds=5)
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
    mock_api.side_effect = mock_api_with_events([event2, event3, event3, event4])

    dd_run_check(check)

    assert len(aggregator.events) == 0
    assert check.latest_event_query == time3 + dt.timedelta(seconds=1)


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_events_collection_exception_if_invalid_resource(realtime_instance):
    with pytest.raises(Exception, match=r"Invalid resource type specified in `event_resource_filters`: hey."):
        realtime_instance['event_resource_filters'] = ['hey']
        _ = VSphereCheck('vsphere', {}, [realtime_instance])


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_include_events_ok(aggregator, realtime_instance, dd_run_check, mock_api):
    realtime_instance['include_events'] = [
        {"event": "AlarmStatusChangedEvent", "excluded_messages": ["Gray to Green", "Green to Gray"]}
    ]
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    event1 = vim.event.AlarmStatusChangedEvent()
    event1.createdTime = dt.datetime.now()
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
    mock_api.side_effect = mock_api_with_events([event1])

    dd_run_check(check)

    assert len(aggregator.events) == 1
    assert aggregator.events[0]['msg_title'] == "[Triggered] alarm1 on VM vm1 is now red"


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_include_events_filtered(aggregator, realtime_instance, dd_run_check, mock_api):
    realtime_instance['include_events'] = [
        {"event": "AlarmStatusChangedEvent", "excluded_messages": ["Gray to Green", "Green to Gray"]}
    ]
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    event1 = vim.event.AlarmStatusChangedEvent()
    event1.createdTime = dt.datetime.now()
    event1.entity = vim.event.ManagedEntityEventArgument()
    event1.entity.entity = vim.VirtualMachine(moId="vm1")
    event1.entity.name = "vm1"
    event1.alarm = vim.event.AlarmEventArgument()
    event1.alarm.name = "alarm1"
    setattr(event1, 'from', 'green')
    event1.to = 'gray'
    event1.datacenter = vim.event.DatacenterEventArgument()
    event1.datacenter.name = "dc1"
    event1.fullFormattedMessage = "Green to Gray"
    mock_api.side_effect = mock_api_with_events([event1])

    dd_run_check(check)

    assert len(aggregator.events) == 0


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_include_events_incorrectly_formatted_event(aggregator, realtime_instance, dd_run_check, mock_api):
    realtime_instance['include_events'] = [
        {"event": "IncorrectlyFormattedEvent", "excluded_messages": ["Gray to Green", "Green to Gray"]}
    ]
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    event1 = vim.event.AlarmStatusChangedEvent()
    event1.createdTime = dt.datetime.now()
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
    mock_api.side_effect = mock_api_with_events([event1])

    dd_run_check(check)

    assert len(aggregator.events) == 0


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_include_events_ok_new_event_type(aggregator, realtime_instance, dd_run_check, mock_api):
    realtime_instance['include_events'] = [{"event": "AlarmAcknowledgedEvent", "excluded_messages": ["Remove Alarm"]}]
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    event1 = vim.event.AlarmAcknowledgedEvent()
    event1.createdTime = dt.datetime.now()
    event1.entity = vim.event.ManagedEntityEventArgument()
    event1.entity.entity = vim.VirtualMachine(moId="vm1")
    event1.entity.name = "vm1"
    event1.alarm = vim.event.AlarmEventArgument()
    event1.alarm.name = "alarm1"
    event1.datacenter = vim.event.DatacenterEventArgument()
    event1.datacenter.name = "dc1"
    event1.fullFormattedMessage = "The Alarm was acknowledged"
    mock_api.side_effect = mock_api_with_events([event1])

    dd_run_check(check)

    assert len(aggregator.events) == 1
    assert "The Alarm was acknowledged" in aggregator.events[0]['msg_text']
    assert aggregator.events[0]['msg_title'] == "AlarmAcknowledgedEvent"


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_include_events_ok_new_resource(aggregator, realtime_instance, dd_run_check, mock_api):
    realtime_instance['include_events'] = [{"event": "AlarmAcknowledgedEvent", "excluded_messages": ["Remove Alarm"]}]
    realtime_instance['event_resource_filters'] = ['storage_pod']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    event1 = vim.event.AlarmAcknowledgedEvent()
    event1.createdTime = dt.datetime.now()
    event1.entity = vim.event.ManagedEntityEventArgument()
    event1.entity.entity = vim.StoragePod(moId="pod1")
    event1.entity.name = "pod1"
    event1.alarm = vim.event.AlarmEventArgument()
    event1.alarm.name = "alarm1"
    event1.datacenter = vim.event.DatacenterEventArgument()
    event1.datacenter.name = "dc1"
    event1.fullFormattedMessage = "The Alarm was acknowledged"
    mock_api.side_effect = mock_api_with_events([event1])

    dd_run_check(check)

    assert len(aggregator.events) == 1
    assert "The Alarm was acknowledged" in aggregator.events[0]['msg_text']
    assert aggregator.events[0]['msg_title'] == "AlarmAcknowledgedEvent"


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_include_events_excluded_message_new_resource(aggregator, realtime_instance, dd_run_check, mock_api):
    realtime_instance['include_events'] = [
        {"event": "AlarmAcknowledgedEvent", "excluded_messages": ["The Alarm was acknowledged"]}
    ]
    realtime_instance['event_resource_filters'] = ['storage_pod']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    event1 = vim.event.AlarmAcknowledgedEvent()
    event1.createdTime = dt.datetime.now()
    event1.entity = vim.event.ManagedEntityEventArgument()
    event1.entity.entity = vim.StoragePod(moId="pod1")
    event1.entity.name = "pod1"
    event1.alarm = vim.event.AlarmEventArgument()
    event1.alarm.name = "alarm1"
    event1.datacenter = vim.event.DatacenterEventArgument()
    event1.datacenter.name = "dc1"
    event1.fullFormattedMessage = "The Alarm was acknowledged"
    mock_api.side_effect = mock_api_with_events([event1])

    dd_run_check(check)

    assert len(aggregator.events) == 0


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_rest_api')
def test_include_events_empty_event_resource_filters(aggregator, realtime_instance, dd_run_check, mock_api):
    realtime_instance['include_events'] = [{"event": "AlarmAcknowledgedEvent", "excluded_messages": ["Remove Alarm"]}]
    realtime_instance['event_resource_filters'] = []
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    event1 = vim.event.AlarmAcknowledgedEvent()
    event1.createdTime = dt.datetime.now()
    event1.entity = vim.event.ManagedEntityEventArgument()
    event1.entity.entity = vim.VirtualMachine(moId="vm1")
    event1.entity.name = "vm1"
    event1.alarm = vim.event.AlarmEventArgument()
    event1.alarm.name = "alarm1"
    event1.datacenter = vim.event.DatacenterEventArgument()
    event1.datacenter.name = "dc1"
    event1.fullFormattedMessage = "The Alarm was acknowledged"
    mock_api.side_effect = mock_api_with_events([event1])

    dd_run_check(check)

    assert len(aggregator.events) == 0
