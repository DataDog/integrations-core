# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from pyVmomi import vim

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.time import get_current_datetime
from datadog_checks.vsphere import VSphereCheck

from .common import EVENTS, LEGACY_HISTORICAL_INSTANCE

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
        tags=['vcenter_host:FAKE', 'vcenter_server:vsphere_mock'],
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
        tags=['vcenter_host:FAKE', 'vcenter_server:vsphere_mock'],
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
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmMessageEvent(
                createdTime=get_current_datetime(),
                vm=vim.event.VmEventArgument(name="vm1"),
                fullFormattedMessage="Event example",
            )
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """@@@\nEvent example\n@@@""",
        msg_title="VM vm1 is reporting",
        host="vm1",
    )


def test_event_vm_migrated(aggregator, dd_run_check, legacy_default_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmMigratedEvent(
                createdTime=get_current_datetime(),
                vm=vim.event.VmEventArgument(name="vm1"),
                fullFormattedMessage="Event example",
            )
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """@@@\nEvent example\n@@@""",
        msg_title="VM vm1 has been migrated",
        host="vm1",
    )


def test_event_task(aggregator, dd_run_check, legacy_default_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.TaskEvent(
                createdTime=get_current_datetime(),
                fullFormattedMessage="Task completed successfully",
            )
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """@@@\nTask completed successfully\n@@@""",
        msg_title="TaskEvent",
    )


def test_event_vm_powered_on(aggregator, dd_run_check, legacy_default_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmPoweredOnEvent(
                createdTime=get_current_datetime(),
                userName="datadog",
                host=vim.event.HostEventArgument(name="host1"),
                datacenter=vim.event.DatacenterEventArgument(name="dc1"),
                vm=vim.event.VmEventArgument(name="vm1"),
                fullFormattedMessage="Virtual machine powered on",
            )
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """datadog has powered on this virtual machine. It is running on:
- datacenter: dc1
- host: host1
"""
    )


def test_event_vm_powered_off(aggregator, dd_run_check, legacy_default_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmPoweredOffEvent(
                createdTime=get_current_datetime(),
                userName="datadog",
                host=vim.event.HostEventArgument(name="host1"),
                datacenter=vim.event.DatacenterEventArgument(name="dc1"),
                vm=vim.event.VmEventArgument(name="vm1"),
                fullFormattedMessage="Virtual machine powered off",
            )
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """datadog has powered off this virtual machine. It was running on:
- datacenter: dc1
- host: host1
""",
        count=1,
    )


def test_event_vm_reconfigured(aggregator, dd_run_check, legacy_default_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmReconfiguredEvent(
                createdTime=get_current_datetime(),
                userName="datadog",
                vm=vim.event.VmEventArgument(name="vm1"),
                configSpec=vim.vm.ConfigSpec(),
            )
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """datadog saved the new configuration:\n@@@\n""",
        count=1,
        exact_match=False,
        msg_title="VM vm1 configuration has been changed",
        host="vm1",
    )


def test_event_vm_suspended(aggregator, dd_run_check, legacy_default_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmSuspendedEvent(
                createdTime=get_current_datetime(),
                userName="datadog",
                host=vim.event.HostEventArgument(name="host1"),
                datacenter=vim.event.DatacenterEventArgument(name="dc1"),
                vm=vim.event.VmEventArgument(name="vm1"),
            )
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_default_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """datadog has suspended this virtual machine. It was running on:
- datacenter: dc1
- host: host1
""",
        count=1,
        msg_title="VM vm1 has been SUSPENDED",
        host="vm1",
    )


def test_report_realtime_vm_count(aggregator, dd_run_check, legacy_realtime_instance, service_instance):
    check = VSphereCheck('vsphere', {}, [legacy_realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vm.count',
        count=1,
        value=2,
        tags=[
            'vcenter_server:vsphere_mock',
        ],
    )


def test_report_realtime_vm_metrics(aggregator, dd_run_check, legacy_realtime_instance, service_instance):
    check = VSphereCheck('vsphere', {}, [legacy_realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=52,
        count=1,
        hostname='vm1',
        tags=[
            'instance:none',
        ],
    )
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=11,
        count=1,
        hostname='vm2',
        tags=[
            'instance:none',
        ],
    )


def test_report_realtime_vm_metrics_invalid_value(aggregator, dd_run_check, legacy_realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        return_value=[
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[-3],
                        id=vim.PerformanceManager.MetricId(counterId=103),
                    )
                ],
            ),
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        count=0,
    )


def test_report_realtime_vm_metrics_empty_value(aggregator, dd_run_check, legacy_realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        return_value=[
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[],
                        id=vim.PerformanceManager.MetricId(counterId=103),
                    )
                ],
            ),
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        count=0,
    )


def test_report_realtime_vm_metrics_counter_id_not_found(
    aggregator, dd_run_check, legacy_realtime_instance, service_instance
):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        return_value=[
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[5],
                        id=vim.PerformanceManager.MetricId(counterId=200),
                    )
                ],
            ),
        ]
    )
    check = VSphereCheck('vsphere', {}, [legacy_realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        count=0,
    )


def test_report_realtime_host_metrics(aggregator, dd_run_check, legacy_realtime_instance):
    check = VSphereCheck('vsphere', {}, [legacy_realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=61,
        count=1,
        hostname='host1',
        tags=[
            'instance:none',
        ],
    )


def test_report_historical_datacenter_metrics(aggregator, dd_run_check, legacy_historical_instance):
    check = VSphereCheck('vsphere', {}, [legacy_historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=1,
        value=7,
        tags=[
            'instance:dc1',
            'vcenter_server:vsphere_mock',
            'vsphere_datacenter:dc1',
            'vsphere_type:datacenter',
        ],
    )


def test_report_historical_datacenter_in_folder_metrics(aggregator, dd_run_check, legacy_historical_instance):
    check = VSphereCheck('vsphere', {}, [legacy_historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=1,
        value=3,
        tags=[
            'instance:none',
            'vcenter_server:vsphere_mock',
            'vsphere_datacenter:dc2',
            'vsphere_folder:folder_1',
            'vsphere_type:datacenter',
        ],
    )


def test_report_historical_datastore_metrics(aggregator, dd_run_check, legacy_historical_instance):
    check = VSphereCheck('vsphere', {}, [legacy_historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datastore.busResets.sum',
        count=1,
        value=5,
        tags=[
            'instance:ds1',
            'vcenter_server:vsphere_mock',
            'vsphere_datastore:ds1',
            'vsphere_type:datastore',
        ],
    )


def test_report_historical_cluster_metrics(aggregator, dd_run_check, legacy_historical_instance):
    check = VSphereCheck('vsphere', {}, [legacy_historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.totalmhz.avg',
        count=1,
        value=5,
        tags=[
            'instance:c1',
            'vcenter_server:vsphere_mock',
            'vsphere_cluster:c1',
            'vsphere_type:cluster',
        ],
    )


@pytest.mark.parametrize(
    ('instance', 'query_options', 'extra_instance', 'expected_metrics'),
    [
        pytest.param(
            LEGACY_HISTORICAL_INSTANCE,
            [mock.MagicMock(value=10)],
            {},
            [
                {
                    'name': 'vsphere.vmop.numChangeDS.latest',
                    'count': 1,
                    'value': 7,
                    'tags': [
                        'instance:dc1',
                        'vcenter_server:vsphere_mock',
                        'vsphere_datacenter:dc1',
                        'vsphere_type:datacenter',
                    ],
                },
            ],
            id='Legacy version. Valid value',
        ),
        pytest.param(
            LEGACY_HISTORICAL_INSTANCE,
            [mock.MagicMock(value=-1)],
            {},
            [
                {
                    'name': 'vsphere.vmop.numChangeDS.latest',
                    'count': 1,
                    'value': 7,
                    'tags': [
                        'instance:dc1',
                        'vcenter_server:vsphere_mock',
                        'vsphere_datacenter:dc1',
                        'vsphere_type:datacenter',
                    ],
                },
            ],
            id='Legacy version. Invalid value',
        ),
        pytest.param(
            LEGACY_HISTORICAL_INSTANCE,
            [Exception()],
            {},
            [
                {
                    'name': 'vsphere.vmop.numChangeDS.latest',
                    'count': 1,
                    'value': 7,
                    'tags': [
                        'instance:dc1',
                        'vcenter_server:vsphere_mock',
                        'vsphere_datacenter:dc1',
                        'vsphere_type:datacenter',
                    ],
                },
            ],
            id='Legacy version. Exception',
        ),
        pytest.param(
            LEGACY_HISTORICAL_INSTANCE,
            [mock.MagicMock(value=10)],
            {'max_query_metrics': 10},
            [
                {
                    'name': 'vsphere.vmop.numChangeDS.latest',
                    'count': 1,
                    'value': 7,
                    'tags': [
                        'instance:dc1',
                        'vcenter_server:vsphere_mock',
                        'vsphere_datacenter:dc1',
                        'vsphere_type:datacenter',
                    ],
                },
            ],
            id='Legacy version. Configured value',
        ),
    ],
)
def test_max_query_metrics(
    aggregator,
    dd_run_check,
    service_instance,
    mock_rest_api,
    instance,
    query_options,
    extra_instance,
    expected_metrics,
):
    service_instance.content.setting.QueryOptions = mock.MagicMock(return_value=query_options)

    instance['fix_max_query_metrics'] = True
    instance.update(extra_instance)
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    for expected_metric in expected_metrics:
        aggregator.assert_metric(
            expected_metric.get('name'),
            count=expected_metric.get('count'),
            value=expected_metric.get('value'),
            hostname=expected_metric.get('hostname'),
            tags=expected_metric.get('tags'),
        )
