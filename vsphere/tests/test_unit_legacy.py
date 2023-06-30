# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from pyVmomi import vim

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.time import get_current_datetime
from datadog_checks.vsphere import VSphereCheck

from .common import EVENTS

pytestmark = [pytest.mark.unit]


def test_log_deprecation_warning(dd_run_check, caplog, legacy_default_instance):
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    deprecation_message = 'DEPRECATION NOTICE: You are using a deprecated version of the vSphere integration.'
    assert deprecation_message in caplog.text


def test_connection_exception(aggregator, dd_run_check, legacy_default_instance, connect_exception):
    with pytest.raises(Exception):
        check = VSphereCheck('vsphere', {}, [legacy_default_instance])
        dd_run_check(check)
    aggregator.assert_service_check(
        'vcenter.can_connect',
        AgentCheck.CRITICAL,
        tags=['vcenter_host:vsphere_host', 'vcenter_server:vsphere_mock'],
    )
    assert len(aggregator._metrics) == 0
    assert len(aggregator.events) == 0
    assert connect_exception.call_count == 1


def test_connection_ok(aggregator, dd_run_check, legacy_default_instance):
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'vcenter.can_connect',
        AgentCheck.OK,
        tags=['vcenter_host:vsphere_host', 'vcenter_server:vsphere_mock'],
    )


def test_metadata(datadog_agent, aggregator, dd_run_check, legacy_default_instance):
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    check.check_id = 'test:123'
    dd_run_check(check)
    datadog_agent.assert_metadata_count(0)


def test_event_exception(aggregator, dd_run_check, legacy_default_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(side_effect=[Exception()])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'vcenter.can_connect',
        AgentCheck.CRITICAL,
        count=0,
    )
    assert len(aggregator.events) == 0
    assert service_instance.content.eventManager.QueryEvents.call_count == 1


def test_two_events(aggregator, dd_run_check, legacy_default_instance, service_instance):
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 2
    assert service_instance.content.eventManager.QueryEvents.call_count == 1


def test_two_calls_to_queryevents(aggregator, dd_run_check, legacy_default_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        side_effect=[
            EVENTS,
            [],
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 2
    aggregator.reset()
    dd_run_check(check)
    assert len(aggregator.events) == 0
    assert service_instance.content.eventManager.QueryEvents.call_count == 2


def test_event_filtered(aggregator, dd_run_check, legacy_default_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmDiskFailedEvent(
                createdTime=get_current_datetime(),
            ),
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0


def test_event_vm_being_hot_migrated_change_host(aggregator, dd_run_check, legacy_default_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmBeingHotMigratedEvent(
                createdTime=get_current_datetime(),
                userName="datadog",
                host=vim.event.HostEventArgument(name="host1"),
                destHost=vim.event.HostEventArgument(name="host2"),
                datacenter=vim.event.DatacenterEventArgument(name="dc1"),
                destDatacenter=vim.event.DatacenterEventArgument(name="dc1"),
                ds=vim.event.DatastoreEventArgument(name="ds1"),
                destDatastore=vim.event.DatastoreEventArgument(name="ds1"),
                vm=vim.event.VmEventArgument(name="vm1"),
            ),
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """datadog has launched a hot migration of this virtual machine:
- Host MIGRATION: from host1 to host2
- No datacenter migration: still dc1
- No datastore migration: still ds1""",
        count=1,
        msg_title="VM vm1 is being migrated",
        host="vm1",
        tags=[
            'vsphere_host:host1',
            'vsphere_host:host2',
            'vsphere_datacenter:dc1',
            'vsphere_datacenter:dc1',
        ],
    )


def test_event_vm_being_hot_migrated_change_datacenter(
    aggregator, dd_run_check, legacy_default_instance, service_instance
):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmBeingHotMigratedEvent(
                createdTime=get_current_datetime(),
                userName="datadog",
                host=vim.event.HostEventArgument(name="host1"),
                destHost=vim.event.HostEventArgument(name="host2"),
                datacenter=vim.event.DatacenterEventArgument(name="dc1"),
                destDatacenter=vim.event.DatacenterEventArgument(name="dc2"),
                ds=vim.event.DatastoreEventArgument(name="ds1"),
                destDatastore=vim.event.DatastoreEventArgument(name="ds1"),
                vm=vim.event.VmEventArgument(name="vm1"),
            ),
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """datadog has launched a hot migration of this virtual machine:
- Datacenter MIGRATION: from dc1 to dc2
- Host MIGRATION: from host1 to host2
- No datastore migration: still ds1""",
        count=1,
        msg_title="VM vm1 is being migrated",
        host="vm1",
        tags=[
            'vsphere_host:host1',
            'vsphere_host:host2',
            'vsphere_datacenter:dc1',
            'vsphere_datacenter:dc2',
        ],
    )


def test_event_vm_being_hot_migrated_change_datastore(
    aggregator, dd_run_check, legacy_default_instance, service_instance
):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmBeingHotMigratedEvent(
                createdTime=get_current_datetime(),
                userName="datadog",
                host=vim.event.HostEventArgument(name="host1"),
                destHost=vim.event.HostEventArgument(name="host1"),
                datacenter=vim.event.DatacenterEventArgument(name="dc1"),
                destDatacenter=vim.event.DatacenterEventArgument(name="dc1"),
                ds=vim.event.DatastoreEventArgument(name="ds1"),
                destDatastore=vim.event.DatastoreEventArgument(name="ds2"),
                vm=vim.event.VmEventArgument(name="vm1"),
            ),
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """datadog has launched a hot migration of this virtual machine:
- Datastore MIGRATION: from ds1 to ds2
- No host migration: still host1
- No datacenter migration: still dc1""",
        count=1,
        msg_title="VM vm1 is being migrated",
        host="vm1",
        tags=[
            'vsphere_host:host1',
            'vsphere_host:host1',
            'vsphere_datacenter:dc1',
            'vsphere_datacenter:dc1',
        ],
    )


def test_event_alarm_status_changed_excluded(aggregator, dd_run_check, legacy_default_instance, service_instance):
    event = vim.event.AlarmStatusChangedEvent(
        createdTime=get_current_datetime(),
        entity=vim.event.ManagedEntityEventArgument(entity=vim.VirtualMachine(moId="vm1"), name="vm1"),
        alarm=vim.event.AlarmEventArgument(name="alarm1"),
        to='yellow',
        datacenter=vim.event.DatacenterEventArgument(name="dc1"),
        fullFormattedMessage="Green to Gray",
    )
    setattr(event, 'from', 'green')
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0


def test_event_alarm_status_changed_vm(aggregator, dd_run_check, legacy_default_instance, service_instance):
    event = vim.event.AlarmStatusChangedEvent(
        createdTime=get_current_datetime(),
        entity=vim.event.ManagedEntityEventArgument(entity=vim.VirtualMachine(moId="vm1"), name="vm1"),
        alarm=vim.event.AlarmEventArgument(name="alarm1"),
        to='yellow',
        datacenter=vim.event.DatacenterEventArgument(name="dc1"),
        fullFormattedMessage="Green to Yellow",
    )
    setattr(event, 'from', 'green')
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """vCenter monitor status changed on this alarm, it was green and it's now yellow.""",
        count=1,
        msg_title="[Triggered] alarm1 on VM vm1 is now yellow",
        alert_type="warning",
        host="vm1",
    )


def test_event_alarm_status_changed_vm_recovered(aggregator, dd_run_check, legacy_default_instance, service_instance):
    event = vim.event.AlarmStatusChangedEvent(
        createdTime=get_current_datetime(),
        entity=vim.event.ManagedEntityEventArgument(entity=vim.VirtualMachine(moId="vm1"), name="vm1"),
        alarm=vim.event.AlarmEventArgument(name="alarm1"),
        to='green',
        datacenter=vim.event.DatacenterEventArgument(name="dc1"),
        fullFormattedMessage="Green to Yellow",
    )
    setattr(event, 'from', 'red')
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """vCenter monitor status changed on this alarm, it was red and it's now green.""",
        count=1,
        msg_title="[Recovered] alarm1 on VM vm1 is now green",
        alert_type="success",
        host="vm1",
    )


def test_event_alarm_status_changed_host(aggregator, dd_run_check, legacy_default_instance, service_instance):
    event = vim.event.AlarmStatusChangedEvent(
        createdTime=get_current_datetime(),
        entity=vim.event.ManagedEntityEventArgument(entity=vim.HostSystem(moId="vm1"), name="host1"),
        alarm=vim.event.AlarmEventArgument(name="alarm1"),
        to='yellow',
        datacenter=vim.event.DatacenterEventArgument(name="dc1"),
        fullFormattedMessage="Green to Yellow",
    )
    setattr(event, 'from', 'green')
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """vCenter monitor status changed on this alarm, it was green and it's now yellow.""",
        count=1,
        msg_title="[Triggered] alarm1 on host host1 is now yellow",
        alert_type="warning",
        host="host1",
    )


def test_event_alarm_status_changed_other(aggregator, dd_run_check, legacy_default_instance, service_instance):
    event = vim.event.AlarmStatusChangedEvent(
        createdTime=get_current_datetime(),
        entity=vim.event.ManagedEntityEventArgument(entity=vim.Folder(moId="folder1"), name="folder1"),
        alarm=vim.event.AlarmEventArgument(name="alarm1"),
        to='yellow',
        datacenter=vim.event.DatacenterEventArgument(name="dc1"),
        fullFormattedMessage="Green to Yellow",
    )
    setattr(event, 'from', 'green')
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0


def test_event_alarm_status_changed_wrong_from(aggregator, dd_run_check, legacy_default_instance, service_instance):
    event = vim.event.AlarmStatusChangedEvent(
        createdTime=get_current_datetime(),
        entity=vim.event.ManagedEntityEventArgument(entity=vim.VirtualMachine(moId="vm1"), name="vm1"),
        alarm=vim.event.AlarmEventArgument(name="alarm1"),
        to='yellow',
        datacenter=vim.event.DatacenterEventArgument(name="dc1"),
        fullFormattedMessage="Green to Yellow",
    )
    setattr(event, 'from', 'other')
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0


def test_event_alarm_status_changed_wrong_to(aggregator, dd_run_check, legacy_default_instance, service_instance):
    event = vim.event.AlarmStatusChangedEvent(
        createdTime=get_current_datetime(),
        entity=vim.event.ManagedEntityEventArgument(entity=vim.VirtualMachine(moId="vm1"), name="vm1"),
        alarm=vim.event.AlarmEventArgument(name="alarm1"),
        to='other',
        datacenter=vim.event.DatacenterEventArgument(name="dc1"),
        fullFormattedMessage="Green to Yellow",
    )
    setattr(event, 'from', 'green')
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0


def test_event_vm_message(aggregator, dd_run_check, legacy_default_instance, service_instance):
    event = vim.event.VmMessageEvent(
        createdTime=get_current_datetime(),
        vm=vim.event.VmEventArgument(name="vm1"),
        fullFormattedMessage="Event example",
    )
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """@@@\nEvent example\n@@@""",
        msg_title="VM vm1 is reporting",
        host="vm1",
    )


def test_event_vm_migrated(aggregator, dd_run_check, legacy_default_instance, service_instance):
    event = vim.event.VmMigratedEvent(
        createdTime=get_current_datetime(),
        vm=vim.event.VmEventArgument(name="vm1"),
        fullFormattedMessage="Event example",
    )
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """@@@\nEvent example\n@@@""",
        msg_title="VM vm1 has been migrated",
        host="vm1",
    )


def test_event_task(aggregator, dd_run_check, legacy_default_instance, service_instance):
    event = vim.event.TaskEvent(
        createdTime=get_current_datetime(),
        fullFormattedMessage="Task completed successfully",
    )
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """@@@\nTask completed successfully\n@@@""",
        msg_title="TaskEvent",
    )
