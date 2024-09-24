# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
import logging

import mock
import pytest
from pyVmomi import vim, vmodl

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.time import get_current_datetime
from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.constants import DEFAULT_MAX_QUERY_METRICS

from .common import (
    EVENTS,
    HISTORICAL_INSTANCE,
    REALTIME_INSTANCE,
    VSPHERE_VERSION,
)

pytestmark = [pytest.mark.unit]


@contextlib.contextmanager
def does_not_raise(enter_result=None):
    yield enter_result


def test_log_deprecation_warning(dd_run_check, caplog, default_instance):
    check = VSphereCheck('vsphere', {}, [default_instance])
    dd_run_check(check)
    deprecation_message = 'DEPRECATION NOTICE: You are using a deprecated version of the vSphere integration.'
    assert deprecation_message not in caplog.text


def test_connection_exception(aggregator, dd_run_check, default_instance, connect_exception):
    with pytest.raises(Exception):
        check = VSphereCheck('vsphere', {}, [default_instance])
        dd_run_check(check)
    aggregator.assert_service_check(
        'vsphere.can_connect',
        AgentCheck.CRITICAL,
        tags=['vcenter_server:FAKE'],
    )
    assert len(aggregator._metrics) == 0
    assert len(aggregator.events) == 0
    assert connect_exception.call_count == 1


def test_connection_ok(aggregator, dd_run_check, default_instance):
    check = VSphereCheck('vsphere', {}, [default_instance])
    dd_run_check(check)
    aggregator.assert_service_check('vsphere.can_connect', AgentCheck.OK, tags=['vcenter_server:FAKE'])


def test_metadata(datadog_agent, aggregator, dd_run_check, default_instance, service_instance):
    check = VSphereCheck('vsphere', {}, [default_instance])
    check.check_id = 'test:123'
    dd_run_check(check)
    major, minor, patch = VSPHERE_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.build': '123456789',
        'version.raw': '{}+123456789'.format(VSPHERE_VERSION),
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


def test_disabled_metadata(datadog_agent, aggregator, dd_run_check, default_instance, service_instance):
    check = VSphereCheck('vsphere', {}, [default_instance])
    check.check_id = 'test:123'
    datadog_agent._config["enable_metadata_collection"] = False
    dd_run_check(check)
    datadog_agent.assert_metadata_count(0)


def test_event_exception(aggregator, dd_run_check, events_only_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(side_effect=[Exception()])
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'vsphere.can_connect',
        AgentCheck.CRITICAL,
        count=0,
    )
    assert len(aggregator.events) == 0
    assert service_instance.content.eventManager.QueryEvents.call_count == 2


def test_two_events(aggregator, dd_run_check, events_only_instance, service_instance):
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 2
    assert service_instance.content.eventManager.QueryEvents.call_count == 1


def test_two_calls_to_queryevents(aggregator, dd_run_check, events_only_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        side_effect=[
            EVENTS,
            [],
        ]
    )
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 2
    aggregator.reset()
    dd_run_check(check)
    assert len(aggregator.events) == 0
    assert service_instance.content.eventManager.QueryEvents.call_count == 2


def test_event_filtered(aggregator, dd_run_check, events_only_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmDiskFailedEvent(
                createdTime=get_current_datetime(),
            ),
        ]
    )
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0


def test_event_vm_being_hot_migrated_change_host(aggregator, dd_run_check, events_only_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
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
            'vcenter_server:FAKE',
            'vsphere_host:host1',
            'vsphere_host:host2',
            'vsphere_datacenter:dc1',
            'vsphere_datacenter:dc1',
        ],
    )


def test_event_vm_being_hot_migrated_change_datacenter(
    aggregator, dd_run_check, events_only_instance, service_instance
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
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
            'vcenter_server:FAKE',
            'vsphere_host:host1',
            'vsphere_host:host2',
            'vsphere_datacenter:dc1',
            'vsphere_datacenter:dc2',
        ],
    )


def test_event_vm_being_hot_migrated_change_datastore(aggregator, dd_run_check, events_only_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
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
            'vcenter_server:FAKE',
            'vsphere_host:host1',
            'vsphere_host:host1',
            'vsphere_datacenter:dc1',
            'vsphere_datacenter:dc1',
        ],
    )


def test_event_alarm_status_changed_excluded(aggregator, dd_run_check, events_only_instance, service_instance):
    event = vim.event.AlarmStatusChangedEvent(
        createdTime=get_current_datetime(),
        entity=vim.event.ManagedEntityEventArgument(entity=vim.VirtualMachine(moId="vm1"), name="vm1"),
        alarm=vim.event.AlarmEventArgument(name="alarm1"),
        to='gray',
        datacenter=vim.event.DatacenterEventArgument(name="dc1"),
        fullFormattedMessage="Green to Gray",
    )
    setattr(event, 'from', 'green')
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0


def test_event_alarm_status_changed_vm(aggregator, dd_run_check, events_only_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """vCenter monitor status changed on this alarm, it was green and it's now yellow.""",
        count=1,
        msg_title="[Triggered] alarm1 on VM vm1 is now yellow",
        alert_type="warning",
        host="vm1",
        tags=[
            'vcenter_server:FAKE',
        ],
    )


def test_event_alarm_status_changed_vm_recovered(aggregator, dd_run_check, events_only_instance, service_instance):
    event = vim.event.AlarmStatusChangedEvent(
        createdTime=get_current_datetime(),
        entity=vim.event.ManagedEntityEventArgument(entity=vim.VirtualMachine(moId="vm1"), name="vm1"),
        alarm=vim.event.AlarmEventArgument(name="alarm1"),
        to='green',
        datacenter=vim.event.DatacenterEventArgument(name="dc1"),
        fullFormattedMessage="Red to Green",
    )
    setattr(event, 'from', 'red')
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """vCenter monitor status changed on this alarm, it was red and it's now green.""",
        count=1,
        msg_title="[Recovered] alarm1 on VM vm1 is now green",
        alert_type="success",
        host="vm1",
        tags=[
            'vcenter_server:FAKE',
        ],
    )


def test_event_alarm_status_changed_host(aggregator, dd_run_check, events_only_instance, service_instance):
    event = vim.event.AlarmStatusChangedEvent(
        createdTime=get_current_datetime(),
        entity=vim.event.ManagedEntityEventArgument(entity=vim.HostSystem(moId="host1"), name="host1"),
        alarm=vim.event.AlarmEventArgument(name="alarm1"),
        to='yellow',
        datacenter=vim.event.DatacenterEventArgument(name="dc1"),
        fullFormattedMessage="Green to Yellow",
    )
    setattr(event, 'from', 'green')
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(return_value=[event])
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """vCenter monitor status changed on this alarm, it was green and it's now yellow.""",
        count=1,
        msg_title="[Triggered] alarm1 on host host1 is now yellow",
        alert_type="warning",
        host="host1",
        tags=[
            'vcenter_server:FAKE',
        ],
    )


def test_event_alarm_status_changed_other(aggregator, dd_run_check, events_only_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0


def test_event_alarm_status_changed_wrong_from(aggregator, dd_run_check, events_only_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0


def test_event_alarm_status_changed_wrong_to(aggregator, dd_run_check, events_only_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    assert len(aggregator.events) == 0


def test_event_vm_message(aggregator, dd_run_check, events_only_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmMessageEvent(
                createdTime=get_current_datetime(),
                vm=vim.event.VmEventArgument(name="vm1"),
                fullFormattedMessage="Event example",
            )
        ]
    )
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """@@@\nEvent example\n@@@""",
        msg_title="VM vm1 is reporting",
        host="vm1",
        tags=['vcenter_server:FAKE'],
    )


def test_event_vm_migrated(aggregator, dd_run_check, events_only_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.VmMigratedEvent(
                createdTime=get_current_datetime(),
                vm=vim.event.VmEventArgument(name="vm1"),
                fullFormattedMessage="Event example",
            )
        ]
    )
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """@@@\nEvent example\n@@@""",
        msg_title="VM vm1 has been migrated",
        host="vm1",
        tags=['vcenter_server:FAKE'],
    )


def test_event_task(aggregator, dd_run_check, events_only_instance, service_instance):
    service_instance.content.eventManager.QueryEvents = mock.MagicMock(
        return_value=[
            vim.event.TaskEvent(
                createdTime=get_current_datetime(),
                fullFormattedMessage="Task completed successfully",
            )
        ]
    )
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """@@@\nTask completed successfully\n@@@""",
        msg_title="TaskEvent",
        tags=['vcenter_server:FAKE'],
    )


def test_event_vm_powered_on(aggregator, dd_run_check, events_only_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """datadog has powered on this virtual machine. It is running on:
- datacenter: dc1
- host: host1
"""
    )


def test_event_vm_powered_off(aggregator, dd_run_check, events_only_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """datadog has powered off this virtual machine. It was running on:
- datacenter: dc1
- host: host1
""",
        count=1,
    )


def test_event_vm_reconfigured(aggregator, dd_run_check, events_only_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    dd_run_check(check)
    aggregator.assert_event(
        """datadog saved the new configuration:\n@@@\n""",
        count=1,
        exact_match=False,
        msg_title="VM vm1 configuration has been changed",
        host="vm1",
    )


def test_event_vm_suspended(aggregator, dd_run_check, events_only_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [events_only_instance])
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


def test_report_realtime_vm_count(aggregator, dd_run_check, realtime_instance):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vm.count',
        count=2,
        value=2,
        tags=['vcenter_server:FAKE', 'vsphere_host:unknown', 'vsphere_type:vm'],
    )


def test_report_realtime_vm_metrics(aggregator, dd_run_check, realtime_instance):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=52,
        count=1,
        hostname='vm1',
        tags=['vcenter_server:FAKE'],
    )
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=11,
        count=1,
        hostname='vm2',
        tags=['vcenter_server:FAKE'],
    )


def test_report_realtime_vm_percent_metrics(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerfCounterByLevel = mock.MagicMock(
        return_value=[
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='usage'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.average,
                unitInfo=vim.ElementDescription(key='percent'),
            ),
        ]
    )
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[5299],
                            id=vim.PerformanceManager.MetricId(counterId=100),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.usage.avg',
        value=52.99,
        count=1,
        hostname='vm1',
        tags=['vcenter_server:FAKE'],
    )


def test_report_realtime_vm_vcpu_percent_metrics(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerfCounterByLevel = mock.MagicMock(
        return_value=[
            vim.PerformanceManager.CounterInfo(
                key=33,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='usage.vcpus'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.average,
                unitInfo=vim.ElementDescription(key='percent'),
            ),
        ]
    )
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[5299],
                            id=vim.PerformanceManager.MetricId(counterId=33),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.usage.vcpus.avg',
        value=52.99,
        count=1,
        hostname='vm1',
        tags=['vcenter_server:FAKE'],
    )


def test_report_realtime_vm_metrics_invalid_value(aggregator, dd_run_check, realtime_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        count=0,
    )


def test_report_realtime_vm_metrics_exception(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.CurrentTime = mock.MagicMock(
        side_effect=[
            Exception(),
        ]
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        count=0,
    )


def test_report_realtime_vm_metrics_empty_value(aggregator, dd_run_check, realtime_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        count=0,
    )


def test_report_realtime_vm_metrics_counter_id_not_found(aggregator, dd_run_check, realtime_instance, service_instance):
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
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        count=0,
    )


def test_report_realtime_vm_metrics_instance_one_value(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=103, instance='vm1'),
                        )
                    ],
                ),
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm2"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[30, 11],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    realtime_instance.update(
        {
            'collect_per_instance_filters': {
                'vm': ['cpu.costop.sum'],
            }
        }
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=52,
        count=1,
        hostname='vm1',
        tags=['cpu_core:vm1', 'vcenter_server:FAKE'],
    )


def test_report_realtime_vm_metrics_instance_two_values(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=103, instance='vm1'),
                        )
                    ],
                ),
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm2"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[30, 11],
                            id=vim.PerformanceManager.MetricId(counterId=103, instance='vm2'),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    realtime_instance.update(
        {
            'collect_per_instance_filters': {
                'vm': ['cpu.costop.sum'],
            }
        }
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=52,
        count=1,
        hostname='vm1',
        tags=['cpu_core:vm1', 'vcenter_server:FAKE'],
    )
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=11,
        count=1,
        hostname='vm2',
        tags=['cpu_core:vm2', 'vcenter_server:FAKE'],
    )


def test_report_realtime_vm_metrics_instance_untagged(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=104, instance='vm1'),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    realtime_instance.update(
        {
            'collect_per_instance_filters': {
                'vm': ['mem.active.avg'],
            }
        }
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.mem.active.avg',
        value=52,
        count=1,
        hostname='vm1',
        tags=['vcenter_server:FAKE', 'instance:vm1'],
    )


def test_report_realtime_vm_metrics_runtime_host(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="root"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm1',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.host',
                            val=vim.HostSystem(moId="host1"),
                        ),
                    ],
                ),
            ],
        )
    )
    realtime_instance['excluded_host_tags'] = ['vsphere_host']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=52,
        count=1,
        hostname='vm1',
        tags=['vcenter_server:FAKE', 'vsphere_host:host1'],
    )


def test_report_realtime_vm_metrics_runtime_host_not_in_infrastructure(
    aggregator, dd_run_check, realtime_instance, service_instance
):
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="root"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm1',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.host',
                            val=vim.HostSystem(moId="host2"),
                        ),
                    ],
                ),
            ],
        )
    )
    realtime_instance['excluded_host_tags'] = ['vsphere_host']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=52,
        count=1,
        hostname='vm1',
        tags=['vcenter_server:FAKE', 'vsphere_host:unknown'],
    )


def test_report_realtime_vm_metrics_guest_hostname(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm1',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm2"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm2',
                        ),
                        vmodl.DynamicProperty(
                            name='guest.hostName',
                            val='guest_vm2',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                    ],
                ),
            ],
        )
    )
    realtime_instance['use_guest_hostname'] = True
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=52,
        count=1,
        hostname='vm1',
        tags=['vcenter_server:FAKE'],
    )
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=11,
        count=1,
        hostname='guest_vm2',
        tags=['vcenter_server:FAKE'],
    )


def test_report_realtime_vm_metrics_excluded_host_tags(aggregator, dd_run_check, realtime_instance):
    realtime_instance['excluded_host_tags'] = ['vsphere_type']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=52,
        count=1,
        hostname='vm1',
        tags=['vcenter_server:FAKE', 'vsphere_type:vm'],
    )
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=11,
        count=1,
        hostname='vm2',
        tags=['vcenter_server:FAKE', 'vsphere_type:vm'],
    )


def test_report_realtime_vm_metrics_filtered(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm2"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[30, 11],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    realtime_instance['metric_filters'] = {'vm': ['cpu.maxlimited.sum']}
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=0)


def test_report_realtime_vm_metrics_whitelisted(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm2"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[30, 11],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm1',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm2"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm2',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                    ],
                ),
            ]
        )
    )
    realtime_instance['resource_filters'] = [
        {
            'type': 'whitelist',
            'resource': 'vm',
            'property': 'name',
            'patterns': [
                'vm1.*',
            ],
        }
    ]
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=1)


def test_report_realtime_vm_metrics_blacklisted(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm2"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[30, 11],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm1',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm2"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm2',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                    ],
                ),
            ]
        )
    )
    realtime_instance['resource_filters'] = [
        {
            'type': 'blacklist',
            'resource': 'vm',
            'property': 'name',
            'patterns': [
                'vm.*',
            ],
        }
    ]
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=0)


def test_report_realtime_vm_metrics_powered_off(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm1',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOff,
                        ),
                    ],
                ),
            ]
        )
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        name='vsphere.cpu.costop.sum',
        count=0,
    )


@pytest.mark.usefixtures('mock_http_api')
def test_vm_hostname_suffix_tag(aggregator, caplog, dd_run_check, realtime_instance, service_instance):
    caplog.set_level(logging.DEBUG)
    realtime_instance.update(
        {
            'collect_tags': True,
            'vm_hostname_suffix_tag': 'my_cat_name_1',
            'excluded_host_tags': ['my_cat_name_1', 'my_cat_name_2'],
        }
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm1',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm2"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm2',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                    ],
                ),
            ]
        )
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        name='vsphere.cpu.costop.sum',
        count=1,
        value=52,
        tags=[
            'my_cat_name_1:my_tag_name_1',
            'my_cat_name_2:my_tag_name_2',
            'vcenter_server:FAKE',
        ],
        hostname='vm1-my_tag_name_1',
    )
    assert "Attached hostname suffix key my_cat_name_1, new hostname: vm1-my_tag_name_1" in caplog.text
    assert "Could not attach hostname suffix key my_cat_name_1 for host: vm2" in caplog.text


@pytest.mark.usefixtures('mock_http_api')
def test_vm_hostname_suffix_tag_integration(aggregator, caplog, dd_run_check, realtime_instance, service_instance):
    caplog.set_level(logging.DEBUG)
    realtime_instance.update(
        {
            'collect_tags': True,
            'vm_hostname_suffix_tag': 'vsphere_host',
            'excluded_host_tags': ['my_cat_name_1', 'my_cat_name_2'],
        }
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="root"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm1',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.host',
                            val=vim.HostSystem(moId="host1"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm2"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm2',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                    ],
                ),
            ]
        )
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        name='vsphere.cpu.costop.sum',
        count=1,
        value=52,
        tags=[
            'my_cat_name_1:my_tag_name_1',
            'my_cat_name_2:my_tag_name_2',
            'vcenter_server:FAKE',
        ],
        hostname='vm1-host1',
    )
    assert "Attached hostname suffix key vsphere_host, new hostname: vm1-host1" in caplog.text


@pytest.mark.usefixtures('mock_http_api')
def test_vm_hostname_suffix_tag_custom(aggregator, caplog, dd_run_check, realtime_instance, service_instance):
    caplog.set_level(logging.DEBUG)
    realtime_instance.update(
        {
            'collect_tags': True,
            'vm_hostname_suffix_tag': 'test',
            'tags': ['test:tag_name'],
        },
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="root"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm1',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.host',
                            val=vim.HostSystem(moId="host1"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm2"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm2',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                    ],
                ),
            ]
        )
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        name='vsphere.cpu.costop.sum',
        count=1,
        value=52,
        tags=['test:tag_name', 'vcenter_server:FAKE'],
        hostname='vm1-tag_name',
    )
    assert "Attached hostname suffix key test, new hostname: vm1-tag_name" in caplog.text


def test_report_realtime_host_count(aggregator, dd_run_check, realtime_instance):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.host.count',
        count=1,
        value=1,
        tags=['vcenter_server:FAKE', 'vsphere_type:host'],
    )


def test_report_realtime_host_metrics(aggregator, dd_run_check, realtime_instance):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=61,
        count=1,
        hostname='host1',
        tags=['vcenter_server:FAKE'],
    )


def test_report_realtime_host_metrics_filtered(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.HostSystem(moId="host1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    realtime_instance['metric_filters'] = {'host': ['cpu.maxlimited.sum']}
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=0)


def test_report_realtime_host_metrics_whitelisted(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.HostSystem(moId="host1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
                vim.PerformanceManager.EntityMetric(
                    entity=vim.HostSystem(moId="host2"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 61],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host1',
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host2"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host2',
                        ),
                    ],
                ),
            ]
        )
    )
    realtime_instance['resource_filters'] = [
        {
            'type': 'whitelist',
            'resource': 'host',
            'property': 'name',
            'patterns': [
                'host1.*',
            ],
        }
    ]
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=1)


def test_report_realtime_host_metrics_blacklisted(aggregator, dd_run_check, realtime_instance, service_instance):
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.HostSystem(moId="host1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
                vim.PerformanceManager.EntityMetric(
                    entity=vim.HostSystem(moId="host2"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 61],
                            id=vim.PerformanceManager.MetricId(counterId=103),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host1',
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host2"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host2',
                        ),
                    ],
                ),
            ]
        )
    )
    realtime_instance['resource_filters'] = [
        {
            'type': 'blacklist',
            'resource': 'host',
            'property': 'name',
            'patterns': [
                'host.*',
            ],
        }
    ]
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=0)


def test_report_historical_datacenter_count(aggregator, dd_run_check, historical_instance):
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datacenter.count',
        count=1,
        value=1,
        tags=['vcenter_server:FAKE', 'vsphere_datacenter:dc1', 'vsphere_type:datacenter'],
    )


def test_report_historical_datacenter_metrics(aggregator, dd_run_check, historical_instance):
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=1,
        value=7,
        tags=['vcenter_server:FAKE', 'vsphere_datacenter:dc1', 'vsphere_type:datacenter'],
    )


def test_report_historical_datacenter_in_folder_metrics(
    aggregator, dd_run_check, historical_instance, service_instance
):
    service_instance.content.rootFolder = mock.MagicMock(return_value=vim.Folder(moId="root"))
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.Folder(moId="folder1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='folder1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="root"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.Datacenter(moId="dc1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='dc1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="folder1"),
                        ),
                    ],
                ),
            ]
        )
    )
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.Datacenter(moId="dc1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[1, 7],
                            id=vim.PerformanceManager.MetricId(
                                counterId=102,
                                instance='dc1',
                            ),
                        )
                    ],
                ),
            ]
        ]
    )
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=1,
        value=7,
        tags=[
            'vcenter_server:FAKE',
            'vsphere_datacenter:dc1',
            'vsphere_folder:folder1',
            'vsphere_folder:unknown',
            'vsphere_type:datacenter',
        ],
    )


def test_report_historical_datacenter_in_storagepod_metrics(
    aggregator, dd_run_check, historical_instance, service_instance
):
    service_instance.content.rootFolder = mock.MagicMock(return_value=vim.Folder(moId="root"))
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.StoragePod(moId="pod1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='pod1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="root"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.Datacenter(moId="dc1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='dc1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.StoragePod(moId="pod1"),
                        ),
                    ],
                ),
            ]
        )
    )
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.Datacenter(moId="dc1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[1, 7],
                            id=vim.PerformanceManager.MetricId(
                                counterId=102,
                                instance='dc1',
                            ),
                        )
                    ],
                ),
            ]
        ]
    )
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=1,
        value=7,
        tags=[
            'vcenter_server:FAKE',
            'vsphere_datacenter:dc1',
            'vsphere_datastore_cluster:pod1',
            'vsphere_folder:pod1',
            'vsphere_folder:unknown',
            'vsphere_type:datacenter',
        ],
    )


def test_report_historical_datacenter_in_compute_resource_metrics(
    aggregator, dd_run_check, historical_instance, service_instance
):
    service_instance.content.rootFolder = mock.MagicMock(return_value=vim.Folder(moId="root"))
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.ComputeResource(moId="cr1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='cr1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="root"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.Datacenter(moId="dc1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='dc1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.ComputeResource(moId="cr1"),
                        ),
                    ],
                ),
            ]
        )
    )
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.Datacenter(moId="dc1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[1, 7],
                            id=vim.PerformanceManager.MetricId(
                                counterId=102,
                                instance='dc1',
                            ),
                        )
                    ],
                ),
            ]
        ]
    )
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=1,
        value=7,
        tags=[
            'vcenter_server:FAKE',
            'vsphere_compute:cr1',
            'vsphere_datacenter:dc1',
            'vsphere_folder:unknown',
            'vsphere_type:datacenter',
        ],
    )


def test_report_historical_datacenter_in_cluster_compute_resource_metrics(
    aggregator, dd_run_check, historical_instance, service_instance
):
    service_instance.content.rootFolder = mock.MagicMock(return_value=vim.Folder(moId="root"))
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.ClusterComputeResource(moId="ccr1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='ccr1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="root"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.Datacenter(moId="dc1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='dc1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.ClusterComputeResource(moId="ccr1"),
                        ),
                    ],
                ),
            ]
        )
    )
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.Datacenter(moId="dc1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[1, 7],
                            id=vim.PerformanceManager.MetricId(
                                counterId=102,
                                instance='dc1',
                            ),
                        )
                    ],
                ),
            ]
        ]
    )
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=1,
        value=7,
        tags=[
            'vcenter_server:FAKE',
            'vsphere_cluster:ccr1',
            'vsphere_compute:ccr1',
            'vsphere_datacenter:dc1',
            'vsphere_folder:unknown',
            'vsphere_type:datacenter',
        ],
    )


def test_report_historical_datacenter_in_datacenter_resource_metrics(
    aggregator, dd_run_check, historical_instance, service_instance
):
    service_instance.content.rootFolder = mock.MagicMock(return_value=vim.Folder(moId="root"))
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.Datacenter(moId="dc0"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='dc0',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="root"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.Datacenter(moId="dc1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='dc1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Datacenter(moId="dc0"),
                        ),
                    ],
                ),
            ]
        )
    )
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.Datacenter(moId="dc1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[1, 7],
                            id=vim.PerformanceManager.MetricId(
                                counterId=102,
                                instance='dc1',
                            ),
                        )
                    ],
                ),
            ]
        ]
    )
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=1,
        value=7,
        tags=[
            'vcenter_server:FAKE',
            'vsphere_datacenter:dc0',
            'vsphere_datacenter:dc1',
            'vsphere_folder:unknown',
            'vsphere_type:datacenter',
        ],
    )


def test_report_historical_datacenter_in_datastore_resource_metrics(
    aggregator, dd_run_check, historical_instance, service_instance
):
    service_instance.content.rootFolder = mock.MagicMock(return_value=vim.Folder(moId="root"))
    service_instance.content.propertyCollector.RetrievePropertiesEx = mock.MagicMock(
        return_value=vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.Datastore(moId="ds0"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='ds0',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Folder(moId="root"),
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.Datacenter(moId="dc1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='dc1',
                        ),
                        vmodl.DynamicProperty(
                            name='parent',
                            val=vim.Datastore(moId="ds0"),
                        ),
                    ],
                ),
            ]
        )
    )
    service_instance.content.perfManager.QueryPerf = mock.MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.Datacenter(moId="dc1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[1, 7],
                            id=vim.PerformanceManager.MetricId(
                                counterId=102,
                                instance='dc1',
                            ),
                        )
                    ],
                ),
            ]
        ]
    )
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=1,
        value=7,
        tags=[
            'vcenter_server:FAKE',
            'vsphere_datacenter:dc1',
            'vsphere_datastore:ds0',
            'vsphere_folder:unknown',
            'vsphere_type:datacenter',
        ],
    )


def test_report_historical_datastore_count(aggregator, dd_run_check, historical_instance):
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datastore.count',
        count=1,
        value=1,
        tags=['vcenter_server:FAKE', 'vsphere_datastore:ds1', 'vsphere_type:datastore'],
    )


def test_report_historical_datastore_metrics(aggregator, dd_run_check, historical_instance):
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datastore.busResets.sum',
        count=1,
        value=5,
        tags=['vcenter_server:FAKE', 'vsphere_datastore:ds1', 'vsphere_type:datastore'],
    )


def test_report_historical_cluster_count(aggregator, dd_run_check, historical_instance):
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cluster.count',
        count=1,
        value=1,
        tags=['vcenter_server:FAKE', 'vsphere_cluster:c1', 'vsphere_type:cluster'],
    )


def test_report_historical_cluster_metrics(aggregator, dd_run_check, historical_instance):
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.totalmhz.avg',
        count=1,
        value=5,
        tags=['vcenter_server:FAKE', 'vsphere_cluster:c1', 'vsphere_type:cluster'],
    )


def test_rest_api_tags_session_exception(aggregator, dd_run_check, historical_instance, mock_http_api):
    if VSPHERE_VERSION.startswith('7.'):
        mock_http_api.exceptions = {'api/session': Exception()}
    else:
        mock_http_api.exceptions = {'rest/com/vmware/cis/session': Exception()}
    historical_instance['collect_tags'] = True
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datastore.busResets.sum',
        count=1,
        value=5,
        tags=[
            'vcenter_server:FAKE',
            'vsphere_datastore:ds1',
            'vsphere_type:datastore',
        ],
    )


def test_rest_api_tags_tag_association_exception(aggregator, dd_run_check, historical_instance, mock_http_api):
    if VSPHERE_VERSION.startswith('7.'):
        mock_http_api.exceptions = {'api/cis/tagging/tag-association?action=list-attached-tags-on-objects': Exception()}
    else:
        mock_http_api.exceptions = {
            'rest/com/vmware/cis/tagging/tag-association?~action=list-attached-tags-on-objects': Exception()
        }
    historical_instance['collect_tags'] = True
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datastore.busResets.sum',
        count=1,
        value=5,
        tags=[
            'vcenter_server:FAKE',
            'vsphere_datastore:ds1',
            'vsphere_type:datastore',
        ],
    )


@pytest.mark.usefixtures('mock_http_api')
def test_report_historical_metrics_with_tags(aggregator, dd_run_check, historical_instance):
    historical_instance['collect_tags'] = True
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datastore.busResets.sum',
        count=1,
        value=5,
        tags=[
            'my_cat_name_2:my_tag_name_2',
            'vcenter_server:FAKE',
            'vsphere_datastore:ds1',
            'vsphere_type:datastore',
        ],
    )


@pytest.mark.parametrize(
    ('instance', 'query_options', 'extra_instance', 'expected_metrics'),
    [
        pytest.param(
            REALTIME_INSTANCE,
            [mock.MagicMock(value=DEFAULT_MAX_QUERY_METRICS)],
            {},
            [
                {
                    'name': 'vsphere.cpu.costop.sum',
                    'count': 1,
                    'value': 61,
                    'hostname': 'host1',
                    'tags': [
                        'vcenter_server:FAKE',
                    ],
                },
            ],
            id='New version.Realtime.Valid value',
        ),
        pytest.param(
            HISTORICAL_INSTANCE,
            [mock.MagicMock(value=DEFAULT_MAX_QUERY_METRICS)],
            {},
            [
                {
                    'name': 'vsphere.vmop.numChangeDS.latest',
                    'count': 1,
                    'value': 7,
                    'tags': [
                        'vcenter_server:FAKE',
                        'vsphere_datacenter:dc1',
                        'vsphere_type:datacenter',
                    ],
                },
            ],
            id='New version.Historical.Valid value',
        ),
        pytest.param(
            REALTIME_INSTANCE,
            [Exception()],
            {},
            [
                {
                    'name': 'vsphere.cpu.costop.sum',
                    'count': 1,
                    'value': 61,
                    'hostname': 'host1',
                    'tags': [
                        'vcenter_server:FAKE',
                    ],
                },
            ],
            id='New version.Realtime.Exception',
        ),
        pytest.param(
            HISTORICAL_INSTANCE,
            [Exception()],
            {},
            [
                {
                    'name': 'vsphere.vmop.numChangeDS.latest',
                    'count': 1,
                    'value': 7,
                    'tags': [
                        'vcenter_server:FAKE',
                        'vsphere_datacenter:dc1',
                        'vsphere_type:datacenter',
                    ],
                },
            ],
            id='New version.Historical.Exception',
        ),
        pytest.param(
            HISTORICAL_INSTANCE,
            [mock.MagicMock(value=DEFAULT_MAX_QUERY_METRICS)],
            {'max_historical_metrics': DEFAULT_MAX_QUERY_METRICS + 10},
            [
                {
                    'name': 'vsphere.vmop.numChangeDS.latest',
                    'count': 1,
                    'value': 7,
                    'tags': [
                        'vcenter_server:FAKE',
                        'vsphere_datacenter:dc1',
                        'vsphere_type:datacenter',
                    ],
                },
            ],
            id='New version.Historical.Valid value.\'max_historical_metrics\' bigger',
        ),
        pytest.param(
            HISTORICAL_INSTANCE,
            [mock.MagicMock(value=DEFAULT_MAX_QUERY_METRICS)],
            {'metrics_per_query': -1},
            [
                {
                    'name': 'vsphere.vmop.numChangeDS.latest',
                    'count': 1,
                    'value': 7,
                    'tags': [
                        'vcenter_server:FAKE',
                        'vsphere_datacenter:dc1',
                        'vsphere_type:datacenter',
                    ],
                },
            ],
            id='New version.Historical.Valid value.\'metrics_per_query\' negative',
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


@pytest.mark.parametrize(
    ('extra_instance', 'expected_exception', 'expected_warning_message'),
    [
        pytest.param(
            {
                'ssl_verify': False,
                'ssl_capath': '/dummy/path',
            },
            does_not_raise(),
            'Your configuration is incorrectly attempting to specify both a CA path, '
            'and to disable SSL verification. You cannot do both. Proceeding with disabling ssl verification.',
            id='\'ssl_verify\' set to False and \'ssl_capath\' configured',
        ),
        pytest.param(
            {
                'collection_type': 'invalid',
            },
            pytest.raises(
                ConfigurationError,
                match="Your configuration is incorrectly attempting to " "set the `collection_type` to ",
            ),
            None,
            id='\'collection_type\' set to invalid value',
        ),
        pytest.param(
            {
                'collection_level': 0,
            },
            pytest.raises(
                ConfigurationError,
                match="Your configuration is incorrectly attempting to set the collection_level to something different"
                " than a integer between 1 and 4.",
            ),
            None,
            id='\'collection_level\' set to invalid value',
        ),
    ],
)
def test_validate_config_errors(default_instance, extra_instance, expected_exception, expected_warning_message, caplog):
    default_instance.update(extra_instance)
    with expected_exception:
        VSphereCheck('vsphere', {}, [default_instance])
        if expected_warning_message:
            assert expected_warning_message in caplog.text


def test_two_checks(aggregator, dd_run_check, realtime_instance, get_timestamp):
    get_timestamp.side_effect = [0, 0, 1000]
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    dd_run_check(check)
    get_timestamp.call_count == 3


def test_vm_property_metrics(aggregator, realtime_instance, dd_run_check, caplog, service_instance, vm_properties_ex):
    realtime_instance['collect_property_metrics'] = True

    service_instance.content.propertyCollector.RetrievePropertiesEx = vm_properties_ex

    base_tags = ['vcenter_server:FAKE', 'vsphere_folder:unknown', 'vsphere_type:vm']
    base_tags_vm1 = base_tags + ['vsphere_host:host1']
    base_tags_vm3 = base_tags + ['vsphere_host:host2']

    realtime_instance['excluded_host_tags'] = ['vsphere_host', 'vsphere_type', 'vsphere_folder']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)
    aggregator.assert_metric('vsphere.vm.count', value=1, count=1, tags=base_tags_vm1)
    aggregator.assert_metric('vsphere.vm.count', value=1, count=1, tags=base_tags_vm3)

    # VM 1
    aggregator.assert_metric(
        'vsphere.vm.guest.guestFullName',
        count=0,
        hostname='vm1',
    )
    assert (
        "Could not submit property metric- no metric data: name=`vm.guest.guestFullName`, "
        "value=`None`, hostname=`vm1`, base tags=`['vsphere_host:host1', 'vsphere_folder:unknown', "
        "'vsphere_type:vm', 'vcenter_server:FAKE']` additional tags=`{}`"
    ) in caplog.text

    aggregator.assert_metric(
        'vsphere.vm.summary.quickStats.uptimeSeconds',
        count=1,
        value=12184573.0,
        tags=base_tags_vm1,
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.summary.config.numCpu',
        count=1,
        value=2.0,
        tags=base_tags_vm1,
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.summary.config.numEthernetCards',
        count=1,
        value=1.0,
        tags=base_tags_vm1,
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.summary.config.numVirtualDisks',
        count=1,
        value=1.0,
        tags=base_tags_vm1,
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.summary.config.memorySizeMB',
        count=1,
        value=2048,
        tags=base_tags_vm1,
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.config.hardware.numCoresPerSocket',
        count=1,
        value=2.0,
        tags=base_tags_vm1,
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.toolsVersion',
        count=1,
        value=1,
        tags=base_tags_vm1 + ['toolsVersion:11296'],
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.toolsRunningStatus',
        count=0,
        hostname='vm1',
    )
    assert (
        "Could not submit property metric- no metric data: name=`vm.guest.toolsRunningStatus`, "
        "value=`None`, hostname=`vm1`, base tags=`['vsphere_host:host1', 'vsphere_folder:unknown', "
        "'vsphere_type:vm', 'vcenter_server:FAKE']` additional tags=`{}`"
    ) in caplog.text

    aggregator.assert_metric(
        'vsphere.vm.guest.net',
        count=1,
        value=1,
        tags=base_tags_vm1 + ['device_id:0', 'is_connected:True', 'nic_mac_address:00:61:58:72:53:13'],
        hostname='vm1',
    )

    aggregator.assert_metric(
        'vsphere.vm.guest.net',
        count=1,
        value=1,
        tags=base_tags_vm1 + ['device_id:0', 'is_connected:True', 'nic_mac_address:00:61:58:72:53:13'],
        hostname='vm1',
    )

    aggregator.assert_metric(
        'vsphere.vm.guest.net.ipConfig.address',
        count=1,
        value=1,
        tags=base_tags_vm1
        + [
            'device_id:0',
            'is_connected:True',
            'nic_ip_address:fe70::150:46ff:fe47:6311',
            'nic_mac_address:00:61:58:72:53:13',
        ],
        hostname='vm1',
    )

    aggregator.assert_metric(
        'vsphere.vm.guest.ipStack.ipRoute',
        count=1,
        value=1,
        tags=base_tags_vm1
        + [
            'device:0',
            'network_dest_ip:fe83::',
            'route_domain_name:example.com',
            'route_hostname:test-hostname',
            'prefix_length:64',
        ],
        hostname='vm1',
    )

    aggregator.assert_metric(
        'vsphere.vm.guest.disk.freeSpace',
        count=1,
        value=1270075392,
        tags=base_tags_vm1 + ['disk_path:\\', 'file_system_type:ext4'],
        hostname='vm1',
    )

    aggregator.assert_metric(
        'vsphere.vm.guest.disk.capacity',
        count=1,
        value=2064642048,
        tags=base_tags_vm1 + ['disk_path:\\', 'file_system_type:ext4'],
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.config.cpuAllocation.limit',
        count=1,
        value=-1,
        tags=base_tags_vm1,
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.config.memoryAllocation.limit',
        count=1,
        value=-1,
        tags=base_tags_vm1,
        hostname='vm1',
    )

    assert (
        "Submit property metric: name=`vm.config.memoryAllocation.limit`, value=`-1.0`, "
        "hostname=`vm1`, tags=`['vsphere_host:host1', 'vsphere_folder:unknown', "
        "'vsphere_type:vm', 'vcenter_server:FAKE']`, count=`False`"
    ) in caplog.text

    aggregator.assert_metric(
        'vsphere.vm.config.cpuAllocation.overheadLimit',
        count=0,
        hostname='vm1',
    )
    assert (
        "Could not submit property metric- unexpected metric value: "
        "name=`vm.config.cpuAllocation.overheadLimit`, value=`None`, hostname=`vm1`, "
        "base tags=`['vsphere_host:host1', 'vsphere_folder:unknown', "
        "'vsphere_type:vm', 'vcenter_server:FAKE']` additional tags=`{}`"
    ) in caplog.text

    aggregator.assert_metric(
        'vsphere.vm.config.memoryAllocation.overheadLimit',
        count=0,
        hostname='vm1',
    )
    assert (
        "Could not submit property metric- unexpected metric value: "
        "name=`vm.config.memoryAllocation.overheadLimit`, value=`None`, hostname=`vm1`, "
        "base tags=`['vsphere_host:host1', 'vsphere_folder:unknown', "
        "'vsphere_type:vm', 'vcenter_server:FAKE']` additional tags=`{}`"
    ) in caplog.text

    # VM 3
    aggregator.assert_metric(
        'vsphere.vm.guest.guestFullName',
        count=1,
        value=1,
        tags=base_tags_vm3 + ['guestFullName:Debian GNU/Linux 12 (32-bit)'],
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.net',
        count=1,
        value=1,
        tags=base_tags_vm3 + ['device_id:43', 'is_connected:False'],
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.net.ipConfig.address',
        count=1,
        value=1,
        tags=base_tags_vm3 + ['device_id:43', 'is_connected:False', 'nic_ip_address:fe80::170:46ff:fe27:6311'],
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.net.ipConfig.address',
        count=1,
        value=1,
        tags=base_tags_vm3 + ['device_id:43', 'is_connected:False', 'nic_ip_address:fe70::150:46ff:fe47:6311'],
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.summary.config.numCpu',
        value=1,
        count=1,
        hostname='vm3',
        tags=base_tags_vm3,
    )
    aggregator.assert_metric(
        'vsphere.vm.summary.config.numEthernetCards',
        count=1,
        value=3.0,
        tags=base_tags_vm3,
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.summary.config.numVirtualDisks',
        count=1,
        value=3.0,
        tags=base_tags_vm3,
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.summary.config.memorySizeMB',
        count=0,
        hostname='vm3',
    )
    assert (
        "Could not submit property metric- unexpected metric value: name=`vm.summary.config.memorySizeMB`, "
        "value=`None`, hostname=`vm3`, base tags=`['vsphere_host:host2', "
        "'vsphere_folder:unknown', 'vsphere_type:vm', 'vcenter_server:FAKE']` additional tags=`{}`"
    ) in caplog.text

    aggregator.assert_metric(
        'vsphere.vm.config.hardware.numCoresPerSocket',
        count=1,
        value=2.0,
        tags=base_tags_vm3,
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.toolsRunningStatus',
        count=1,
        value=1,
        tags=base_tags_vm3 + ['toolsRunningStatus:guestToolsRunning'],
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.toolsVersionStatus2',
        count=1,
        value=1,
        tags=base_tags_vm3 + ['toolsVersionStatus2:guestToolsSupportedOld'],
        hostname='vm3',
    )

    aggregator.assert_metric(
        'vsphere.vm.guest.net.ipConfig.address',
        count=1,
        value=1,
        tags=base_tags_vm3 + ['device_id:43', 'is_connected:False', 'nic_ip_address:fe70::150:46ff:fe47:6311'],
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.ipStack.ipRoute',
        count=1,
        value=1,
        tags=base_tags_vm3 + ['device:0', 'gateway_address:0.0.0.0', 'network_dest_ip:fe83::', 'prefix_length:32'],
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.config.cpuAllocation.overheadLimit',
        count=1,
        value=24,
        tags=base_tags_vm3,
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.config.cpuAllocation.limit',
        count=1,
        value=10,
        tags=base_tags_vm3,
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.config.memoryAllocation.overheadLimit',
        count=1,
        value=59,
        tags=base_tags_vm3,
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.config.memoryAllocation.limit',
        count=1,
        value=-1,
        tags=base_tags_vm3,
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.disk.freeSpace',
        count=0,
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.disk.capacity',
        count=0,
        hostname='vm3',
    )

    # assert we still get VM performance counter metrics
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=1, hostname='vm1')
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=1, hostname='vm3')


def test_host_property_metrics(aggregator, realtime_instance, dd_run_check, caplog, service_instance, vm_properties_ex):
    realtime_instance['collect_property_metrics'] = True

    service_instance.content.propertyCollector.RetrievePropertiesEx = vm_properties_ex
    base_tags_host = ['vcenter_server:FAKE', 'vsphere_type:host']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)
    aggregator.assert_metric('vsphere.host.count', value=2, count=2, tags=base_tags_host)

    # host 1
    aggregator.assert_metric(
        'vsphere.host.hardware.cpuPowerManagementInfo.currentPolicy',
        count=1,
        value=1,
        tags=base_tags_host + ["currentPolicy:Balanced"],
        hostname='host1',
    )
    aggregator.assert_metric(
        'vsphere.host.summary.runtime.connectionState',
        count=1,
        value=1,
        tags=base_tags_host + ["connectionState:connected"],
        hostname='host1',
    )
    aggregator.assert_metric(
        'vsphere.host.summary.runtime.inMaintenanceMode',
        count=1,
        value=0,
        tags=base_tags_host + ["inMaintenanceMode:False"],
        hostname='host1',
    )
    aggregator.assert_metric(
        'vsphere.host.summary.runtime.powerState',
        count=1,
        value=1,
        tags=base_tags_host + ["powerState:poweredOn"],
        hostname='host1',
    )

    # host 2
    aggregator.assert_metric(
        'vsphere.host.hardware.cpuPowerManagementInfo.currentPolicy',
        count=0,
        hostname='host2',
    )

    assert (
        "Could not submit property metric- no metric data: "
        "name=`host.hardware.cpuPowerManagementInfo.currentPolicy`, value=`None`, "
        "hostname=`host2`, base tags=`['vsphere_type:host', 'vcenter_server:FAKE']` "
        "additional tags=`{}`"
    ) in caplog.text

    aggregator.assert_metric(
        'vsphere.host.summary.runtime.connectionState',
        count=1,
        value=1,
        tags=base_tags_host + ["connectionState:notResponding"],
        hostname='host2',
    )
    aggregator.assert_metric(
        'vsphere.host.summary.runtime.inMaintenanceMode',
        count=1,
        value=1,
        tags=base_tags_host + ["inMaintenanceMode:True"],
        hostname='host2',
    )
    aggregator.assert_metric(
        'vsphere.host.summary.runtime.powerState',
        count=1,
        value=1,
        tags=base_tags_host + ["powerState:unknown"],
        hostname='host2',
    )

    # assert we still get host performance counter metrics
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=1, hostname='host1')
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=1, hostname='host2')


def test_cluster_property_metrics(
    aggregator, historical_instance, dd_run_check, service_instance, vm_properties_ex, caplog
):
    historical_instance['collect_property_metrics'] = True
    caplog.set_level(logging.DEBUG)
    service_instance.content.propertyCollector.RetrievePropertiesEx = vm_properties_ex
    base_tags = ['vcenter_server:FAKE', 'vsphere_type:cluster']
    base_tags_cluster_1 = base_tags + ['vsphere_cluster:c1']
    base_tags_cluster_2 = base_tags + ['vsphere_cluster:c2']

    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)

    # cluster 1
    aggregator.assert_metric(
        'vsphere.cluster.configuration.drsConfig.enabled', count=1, value=1, tags=base_tags_cluster_1 + ['enabled:True']
    )
    aggregator.assert_metric(
        'vsphere.cluster.configuration.dasConfig.enabled', count=1, value=1, tags=base_tags_cluster_1 + ['enabled:True']
    )
    aggregator.assert_metric(
        'vsphere.cluster.configuration.drsConfig.defaultVmBehavior',
        count=1,
        value=1,
        tags=base_tags_cluster_1 + ['defaultVmBehavior:fullyAutomated'],
    )
    aggregator.assert_metric(
        'vsphere.cluster.configuration.drsConfig.vmotionRate', count=1, value=2, tags=base_tags_cluster_1
    )

    # cluster 2
    aggregator.assert_metric(
        'vsphere.cluster.configuration.drsConfig.enabled',
        count=1,
        value=0,
        tags=base_tags_cluster_2 + ['enabled:False'],
    )
    aggregator.assert_metric(
        'vsphere.cluster.configuration.dasConfig.enabled',
        count=1,
        value=0,
        tags=base_tags_cluster_2 + ['enabled:False'],
    )
    aggregator.assert_metric(
        'vsphere.cluster.configuration.drsConfig.defaultVmBehavior',
        count=1,
        value=1,
        tags=base_tags_cluster_2 + ['defaultVmBehavior:fullyAutomated'],
    )
    aggregator.assert_metric(
        'vsphere.cluster.configuration.drsConfig.vmotionRate', count=1, value=1, tags=base_tags_cluster_2
    )
    assert "Could not retrieve properties" not in caplog.text


def test_datastore_property_metrics(aggregator, historical_instance, dd_run_check, service_instance, vm_properties_ex):
    historical_instance['collect_property_metrics'] = True

    service_instance.content.propertyCollector.RetrievePropertiesEx = vm_properties_ex
    base_tags = ['vcenter_server:FAKE', 'vsphere_datastore:ds1', 'vsphere_type:datastore']
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.datastore.summary.freeSpace', count=1, value=305, tags=base_tags)
    aggregator.assert_metric('vsphere.datastore.summary.capacity', count=1, value=100, tags=base_tags)


def test_property_metrics_resource_filters(
    aggregator,
    realtime_instance,
    dd_run_check,
    service_instance,
    vm_properties_ex,
):
    realtime_instance['collect_property_metrics'] = True
    realtime_instance['resource_filters'] = [
        {
            'type': 'whitelist',
            'resource': 'vm',
            'property': 'name',
            'patterns': [
                'vm1.*',
            ],
        },
        {
            'type': 'whitelist',
            'resource': 'host',
            'property': 'name',
            'patterns': [
                'host1.*',
            ],
        },
    ]

    service_instance.content.propertyCollector.RetrievePropertiesEx = vm_properties_ex

    base_tags = ['vcenter_server:FAKE', 'vsphere_folder:unknown', 'vsphere_type:vm']
    base_tags_vm1 = base_tags + ['vsphere_host:host1']
    base_tags_host = ['vcenter_server:FAKE', 'vsphere_type:host']

    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)

    # vms
    aggregator.assert_metric('vsphere.vm.count', value=1, count=1, tags=base_tags_vm1)
    aggregator.assert_metric(
        'vsphere.vm.summary.quickStats.uptimeSeconds',
        count=1,
        value=12184573.0,
        tags=base_tags_vm1,
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.summary.quickStats.uptimeSeconds',
        count=0,
        hostname='vm3',
    )
    aggregator.assert_metric(
        'vsphere.vm.config.cpuAllocation.limit',
        count=1,
        value=-1,
        tags=base_tags_vm1,
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.config.cpuAllocation.limit',
        count=0,
        hostname='vm3',
    )

    # hosts
    aggregator.assert_metric('vsphere.host.count', value=1, count=1, tags=base_tags_host)
    aggregator.assert_metric(
        'vsphere.host.summary.runtime.powerState',
        count=1,
        value=1,
        tags=base_tags_host + ["powerState:poweredOn"],
        hostname='host1',
    )
    aggregator.assert_metric(
        'vsphere.host.summary.runtime.powerState',
        count=0,
        hostname='host2',
    )


def test_property_metrics_metric_filters(
    aggregator,
    default_instance,
    dd_run_check,
    service_instance,
    vm_properties_ex,
):

    default_instance['collection_type'] = 'both'
    default_instance['collect_property_metrics'] = True
    default_instance['metric_filters'] = {
        'host': ['host.summary.runtime.connectionState'],
        'vm': ['vm.guest.net$', 'vm.summary.config.memorySizeMB', 'vm.guest.disk.freeSpace'],
        'cluster': [],
    }

    service_instance.content.propertyCollector.RetrievePropertiesEx = vm_properties_ex

    base_tags = ['vcenter_server:FAKE', 'vsphere_folder:unknown', 'vsphere_type:vm']
    base_tags_vm1 = base_tags + ['vsphere_host:host1']
    base_tags_vm3 = base_tags + ['vsphere_host:host2']

    base_tags_host = ['vcenter_server:FAKE', 'vsphere_type:host']
    base_tags_cluster = ['vcenter_server:FAKE', 'vsphere_type:cluster', 'vsphere_cluster:c1']
    base_tags_datastore = ['vcenter_server:FAKE', 'vsphere_type:datastore', 'vsphere_datastore:ds1']

    check = VSphereCheck('vsphere', {}, [default_instance])
    dd_run_check(check)

    # vms
    aggregator.assert_metric('vsphere.vm.count', value=1, count=1, tags=base_tags_vm1)
    aggregator.assert_metric('vsphere.vm.count', value=1, count=1, tags=base_tags_vm3)

    aggregator.assert_metric(
        'vsphere.vm.summary.config.memorySizeMB', count=1, value=2048, tags=base_tags_vm1, hostname='vm1'
    )

    aggregator.assert_metric(
        'vsphere.vm.guest.disk.freeSpace',
        count=1,
        value=1270075392.0,
        tags=base_tags_vm1 + ['disk_path:\\', 'file_system_type:ext4'],
        hostname='vm1',
    )
    aggregator.assert_metric(
        'vsphere.vm.guest.net',
        count=1,
        value=1,
        tags=base_tags_vm1 + ['device_id:0', 'is_connected:True', 'nic_mac_address:00:61:58:72:53:13'],
        hostname='vm1',
    )

    aggregator.assert_metric(
        'vsphere.vm.guest.net',
        count=1,
        value=1,
        tags=base_tags_vm1 + ['device_id:0', 'is_connected:True', 'nic_mac_address:00:61:58:72:53:13'],
        hostname='vm1',
    )

    aggregator.assert_metric(
        'vsphere.vm.guest.net',
        count=1,
        value=1,
        tags=base_tags_vm3 + ['device_id:43', 'is_connected:False'],
        hostname='vm3',
    )

    # hosts
    aggregator.assert_metric('vsphere.host.count', value=2, count=2, tags=base_tags_host)
    aggregator.assert_metric(
        'vsphere.host.summary.runtime.connectionState',
        count=1,
        tags=base_tags_host + ['connectionState:connected'],
        hostname='host1',
    )
    aggregator.assert_metric(
        'vsphere.host.summary.runtime.connectionState',
        count=1,
        tags=base_tags_host + ['connectionState:notResponding'],
        hostname='host2',
    )

    # clusters
    aggregator.assert_metric('vsphere.cluster.count', value=1, count=1, tags=base_tags_cluster)
    aggregator.assert_metric(
        'vsphere.cluster.configuration.drsConfig.enabled', count=1, value=1, tags=base_tags_cluster + ['enabled:True']
    )
    aggregator.assert_metric(
        'vsphere.cluster.configuration.dasConfig.enabled', count=1, value=1, tags=base_tags_cluster + ['enabled:True']
    )
    aggregator.assert_metric(
        'vsphere.cluster.configuration.drsConfig.defaultVmBehavior',
        count=1,
        value=1,
        tags=base_tags_cluster + ['defaultVmBehavior:fullyAutomated'],
    )
    aggregator.assert_metric(
        'vsphere.cluster.configuration.drsConfig.vmotionRate', count=1, value=2, tags=base_tags_cluster
    )

    # datastores
    aggregator.assert_metric('vsphere.datastore.count', value=1, count=1, tags=base_tags_datastore)
    aggregator.assert_metric('vsphere.datastore.summary.freeSpace', count=1, value=305, tags=base_tags_datastore)
    aggregator.assert_metric('vsphere.datastore.summary.capacity', count=1, value=100, tags=base_tags_datastore)

    # other metrics and assert all covered
    aggregator.assert_metric('datadog.vsphere.refresh_infrastructure_cache.time')
    aggregator.assert_metric('datadog.vsphere.refresh_metrics_metadata_cache.time')
    aggregator.assert_metric('datadog.vsphere.query_metrics.time')
    aggregator.assert_metric('vsphere.datacenter.count')
    aggregator.assert_metric('vsphere.cpu.totalmhz.avg')
    aggregator.assert_metric('vsphere.datastore.busResets.sum')
    aggregator.assert_metric('vsphere.vmop.numChangeDS.latest')
    aggregator.assert_all_metrics_covered()


def test_property_metrics_expired_cache(
    aggregator,
    realtime_instance,
    dd_run_check,
    service_instance,
    vm_properties_ex,
):

    with mock.patch('datadog_checks.vsphere.cache.time') as time:

        realtime_instance['collect_property_metrics'] = True

        service_instance.content.rootFolder = mock.MagicMock(return_value=vim.Folder(moId="root"))

        service_instance.content.propertyCollector.RetrievePropertiesEx = vm_properties_ex

        base_tags = ['vcenter_server:FAKE', 'vsphere_folder:unknown', 'vsphere_type:vm']
        base_tags_vm1 = base_tags + ['vsphere_host:host1']
        base_tags_vm3 = base_tags + ['vsphere_host:host2']
        base_tags_host = ['vcenter_server:FAKE', 'vsphere_type:host']

        # run check with expired cache once
        base_time = 1576263848
        mocked_timestamps = [base_time + 160 * i for i in range(10)]
        time.time = mock.MagicMock(side_effect=mocked_timestamps)

        check = VSphereCheck('vsphere', {}, [realtime_instance])
        check.infrastructure_cache._last_ts = base_time
        dd_run_check(check)
        aggregator.assert_metric('vsphere.vm.count', value=1, count=1, tags=base_tags_vm1)
        aggregator.assert_metric('vsphere.vm.count', value=1, count=1, tags=base_tags_vm3)

        aggregator.assert_metric(
            'vsphere.vm.summary.quickStats.uptimeSeconds',
            count=1,
            value=12184573.0,
            tags=base_tags_vm1,
            hostname='vm1',
        )
        aggregator.assert_metric(
            'vsphere.vm.config.cpuAllocation.limit',
            count=1,
            value=-1,
            tags=base_tags_vm1,
            hostname='vm1',
        )

        # run check with non-expired cache once and confirm no property metrics are collected
        aggregator.reset()
        mocked_timestamps = [base_time + 100 * i for i in range(10)]
        time.time = mock.MagicMock(side_effect=mocked_timestamps)
        check.infrastructure_cache._last_ts = base_time

        assert not check.infrastructure_cache.is_expired()

        dd_run_check(check)
        aggregator.assert_metric('vsphere.vm.count')
        aggregator.assert_metric('vsphere.host.count')
        aggregator.assert_metric('datadog.vsphere.collect_events.time')
        aggregator.assert_metric('datadog.vsphere.query_metrics.time')
        aggregator.assert_metric('vsphere.cpu.costop.sum')
        aggregator.assert_all_metrics_covered()

        assert not check.infrastructure_cache.is_expired()
        assert check.infrastructure_cache.is_expired()

        # run check with expired cache again and confirm property metrics are collected again
        aggregator.reset()
        dd_run_check(check)
        aggregator.assert_metric(
            'vsphere.vm.config.cpuAllocation.limit',
            count=1,
            value=-1,
            tags=base_tags_vm1,
            hostname='vm1',
        )
        aggregator.assert_metric(
            'vsphere.host.hardware.cpuPowerManagementInfo.currentPolicy',
            count=1,
            value=1,
            tags=base_tags_host + ["currentPolicy:Balanced"],
            hostname='host1',
        )


def test_property_metrics_invalid_ip_config(
    aggregator, realtime_instance, dd_run_check, service_instance, vm_invalid_properties_ex
):
    realtime_instance['collect_property_metrics'] = True

    service_instance.content.propertyCollector.RetrievePropertiesEx = vm_invalid_properties_ex

    base_tags = ['vcenter_server:FAKE', 'vsphere_folder:unknown', 'vsphere_type:vm', 'vsphere_host:unknown']

    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.vm.count', value=1, count=1, tags=base_tags)

    aggregator.assert_metric(
        'vsphere.vm.guest.net',
        count=1,
        value=1,
        tags=base_tags + ['device_id:0', 'is_connected:True', 'nic_mac_address:00:61:58:72:53:13'],
        hostname='vm1',
    )

    aggregator.assert_metric(
        'vsphere.vm.guest.net.ipConfig.address',
        count=0,
        hostname='vm1',
    )


def test_property_metrics_invalid_ip_route_config(
    aggregator, realtime_instance, dd_run_check, service_instance, vm_invalid_properties_ex
):
    realtime_instance['collect_property_metrics'] = True

    service_instance.content.propertyCollector.RetrievePropertiesEx = vm_invalid_properties_ex

    base_tags = ['vcenter_server:FAKE', 'vsphere_folder:unknown', 'vsphere_type:vm', 'vsphere_host:unknown']

    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.vm.count', value=1, count=1, tags=base_tags)

    aggregator.assert_metric(
        'vsphere.vm.guest.ipStack.ipRoute',
        count=0,
        hostname='vm1',
    )


def test_property_metrics_invalid_ip_route_config_gateway(
    aggregator, realtime_instance, dd_run_check, service_instance, vm_invalid_gateway_properties_ex
):
    realtime_instance['collect_property_metrics'] = True

    service_instance.content.propertyCollector.RetrievePropertiesEx = vm_invalid_gateway_properties_ex

    base_tags = ['vcenter_server:FAKE', 'vsphere_folder:unknown', 'vsphere_type:vm', 'vsphere_host:unknown']

    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.vm.count', value=1, count=1, tags=base_tags)

    aggregator.assert_metric(
        'vsphere.vm.guest.ipStack.ipRoute',
        count=1,
        value=1,
        tags=base_tags + ['network_dest_ip:fe83::', 'prefix_length:32'],
        hostname='vm1',
    )


def test_property_metrics_excluded_host_tags(
    aggregator, realtime_instance, dd_run_check, service_instance, vm_properties_ex, datadog_agent
):
    realtime_instance['collect_property_metrics'] = True

    service_instance.content.propertyCollector.RetrievePropertiesEx = vm_properties_ex

    realtime_instance['excluded_host_tags'] = ['vsphere_host', 'vsphere_folder']
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'vsphere.vm.summary.quickStats.uptimeSeconds',
        count=1,
        value=12184573.0,
        tags=['vcenter_server:FAKE', 'vsphere_folder:unknown', 'vsphere_host:host1'],
        hostname='vm1',
    )
    datadog_agent.assert_external_tags(
        'vm1',
        {'vsphere': ['vcenter_server:FAKE', 'vsphere_type:vm']},
    )
    aggregator.assert_metric(
        'vsphere.host.hardware.cpuPowerManagementInfo.currentPolicy',
        count=1,
        value=1,
        tags=['currentPolicy:Balanced', 'vcenter_server:FAKE'],
        hostname='host1',
    )
    datadog_agent.assert_external_tags(
        'host1',
        {'vsphere': ['vcenter_server:FAKE', 'vsphere_type:host']},
    )


@pytest.mark.parametrize(
    ('max_query_metrics', 'metrics_per_query', 'max_historical_metrics', 'expected_batch_num'),
    [
        pytest.param(
            None,
            None,
            None,
            4,
            id='defaults',
        ),
        pytest.param(
            1000,
            1000,
            1000,
            4,
            id='High custom settings',
        ),
        pytest.param(
            None,
            None,
            1,
            7,
            id='lowest max historical metrics',
        ),
        pytest.param(
            1,
            None,
            None,
            7,
            id='lowest max query metrics',
        ),
        pytest.param(
            -1,
            1000,
            1,
            7,
            id='negative max query metrics but low max historical',
        ),
        pytest.param(
            -1,
            1000,
            1000,
            4,
            id='negative max query metrics',
        ),
        pytest.param(
            -1,
            -1,
            1,
            7,
            id='negative max query metrics and metrics per query',
        ),
        pytest.param(
            -1,
            -1,
            -1,
            4,
            id='all negative',
        ),
        pytest.param(
            -1,
            -1,
            2,
            5,
            id='larger than 1 batch size',
        ),
        pytest.param(
            -1,
            1,
            1000,
            7,
            id='smaller max query metrics',
        ),
        pytest.param(
            None,
            None,
            -1,
            4,
            id='negative max historical metrics',
        ),
        pytest.param(
            1,
            None,
            -1,
            7,
            id='negative max historical metrics but low max query metrics ',
        ),
        pytest.param(
            10,
            None,
            -1,
            4,
            id='negative max historical metrics and high max query metrics ',
        ),
        pytest.param(
            1,
            1,
            1,
            7,
            id='multiple historical batches',
        ),
    ],
)
def test_make_batch_historical(
    aggregator,
    dd_run_check,
    historical_instance,
    service_instance,
    max_query_metrics,
    expected_batch_num,
    metrics_per_query,
    max_historical_metrics,
):

    # based on PERF_COUNTER_INFO: there are 7 metrics- counter IDs 100- 106
    # 1 cluster metric, 1 datacenter metric, and 3 datastore metrics
    #
    # based on PROPERTIES_EX: there are 5 resources- 2 datacenters, 1 cluster, and 1 datastore
    # counter 103 and 104 are realtime metrics

    # counter 102 is a datacener and cluster metric
    # 101 is a cluster metric
    # 100 105 106 are datastore metrics

    # in total, there are 7 metrics to query for, so that is the largest amount of batches
    # the smallest number of batches is 4, 1 for all datastores + 1 for all datacenters + 1 for each cluster metric

    if max_query_metrics is not None:
        service_instance.content.setting.QueryOptions = mock.MagicMock(
            return_value=[mock.MagicMock(value=max_query_metrics)]
        )
    if metrics_per_query is not None:
        historical_instance['metrics_per_query'] = metrics_per_query
    if max_historical_metrics is not None:
        historical_instance['max_historical_metrics'] = max_historical_metrics

    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)
    num_calls = service_instance.content.perfManager.QueryPerf.call_count
    assert num_calls == expected_batch_num

    # confirm some metrics are still collected
    aggregator.assert_metric(
        'vsphere.cpu.totalmhz.avg',
        count=1,
        value=5,
        tags=['vcenter_server:FAKE', 'vsphere_cluster:c1', 'vsphere_type:cluster'],
    )

    aggregator.assert_metric(
        'vsphere.datastore.busResets.sum',
        count=1,
        value=5,
        tags=['vcenter_server:FAKE', 'vsphere_datastore:ds1', 'vsphere_type:datastore'],
    )

    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=1,
        value=7,
        tags=['vcenter_server:FAKE', 'vsphere_datacenter:dc1', 'vsphere_type:datacenter'],
    )


@pytest.mark.parametrize(
    ('max_query_metrics', 'metrics_per_query', 'max_historical_metrics', 'expected_batch_num'),
    [
        pytest.param(
            None,
            None,
            None,
            2,
            id='defaults',
        ),
        pytest.param(
            1,
            None,
            None,
            2,
            id='small max_query_metrics',
        ),
        pytest.param(
            1,
            1,
            1,
            6,
            id='small max_query_metrics and historical metric',
        ),
        pytest.param(
            None,
            None,
            1,
            2,
            id='ignore max_historical_metrics',
        ),
    ],
)
def test_make_batch_realtime(
    aggregator,
    dd_run_check,
    realtime_instance,
    service_instance,
    max_query_metrics,
    expected_batch_num,
    metrics_per_query,
    max_historical_metrics,
):

    if max_query_metrics is not None:
        service_instance.content.setting.QueryOptions = mock.MagicMock(
            return_value=[mock.MagicMock(value=max_query_metrics)]
        )
    if metrics_per_query is not None:
        realtime_instance['metrics_per_query'] = metrics_per_query
    if max_historical_metrics is not None:
        realtime_instance['max_historical_metrics'] = max_historical_metrics

    # there are 2 VMs, 1 host, and 2 metrics- so 2 * 2 + 2 * 1 = 6 max batches and 2 min batches
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    num_calls = service_instance.content.perfManager.QueryPerf.call_count
    assert num_calls == expected_batch_num

    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=61,
        count=1,
        hostname='host1',
        tags=['vcenter_server:FAKE'],
    )
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        value=52,
        count=1,
        hostname='vm1',
        tags=['vcenter_server:FAKE'],
    )


@pytest.mark.usefixtures("mock_type", "mock_threadpool", "mock_api", "mock_rest_api")
def test_hostname_case_lower(aggregator, realtime_instance, dd_run_check, datadog_agent):
    realtime_instance['hostname_transform'] = 'lower'
    check = VSphereCheck('vsphere', {}, [realtime_instance])

    dd_run_check(check)
    aggregator.assert_metric(
        'datadog.vsphere.collect_events.time', tags=['vcenter_server:FAKE'], hostname='stubbed.hostname'
    )
    aggregator.assert_metric(
        'datadog.vsphere.refresh_metrics_metadata_cache.time', tags=['vcenter_server:FAKE'], hostname='stubbed.hostname'
    )
    aggregator.assert_metric(
        'datadog.vsphere.refresh_infrastructure_cache.time',
        tags=['collect_property_metrics:False', 'vcenter_server:FAKE'],
        hostname='stubbed.hostname',
    )
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='vm4-5')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='vm4-15')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='vm4-19')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='vm4-6')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='vm4-7')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='vm4-8')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='$vm3-2')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='vm3-1')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='vm4-1')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='vm4-6')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='vm4-7')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='vm4-8')
    datadog_agent.assert_external_tags(
        'vm4-5',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm4-15',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm4-19',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm4-6',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm4-7',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm4-8',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )


@pytest.mark.usefixtures("mock_type", "mock_threadpool", "mock_api", "mock_rest_api")
def test_hostname_case_upper(aggregator, realtime_instance, dd_run_check, datadog_agent):
    realtime_instance['hostname_transform'] = 'upper'
    check = VSphereCheck('vsphere', {}, [realtime_instance])

    dd_run_check(check)
    aggregator.assert_metric(
        'datadog.vsphere.collect_events.time', tags=['vcenter_server:FAKE'], hostname='stubbed.hostname'
    )
    aggregator.assert_metric(
        'datadog.vsphere.refresh_metrics_metadata_cache.time', tags=['vcenter_server:FAKE'], hostname='stubbed.hostname'
    )
    aggregator.assert_metric(
        'datadog.vsphere.refresh_infrastructure_cache.time',
        tags=['collect_property_metrics:False', 'vcenter_server:FAKE'],
        hostname='stubbed.hostname',
    )
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-5')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-15')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-19')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-6')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-7')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-8')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='$VM3-2')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='VM3-1')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='VM4-1')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='VM4-6')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='VM4-7')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='VM4-8')
    datadog_agent.assert_external_tags(
        'VM4-5',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'VM4-15',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'VM4-19',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'VM4-6',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'VM4-7',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'VM4-8',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )


@pytest.mark.usefixtures("mock_type", "mock_threadpool", "mock_api", "mock_rest_api")
def test_hostname_case_no_case_change(aggregator, realtime_instance, dd_run_check, datadog_agent):
    check = VSphereCheck('vsphere', {}, [realtime_instance])

    dd_run_check(check)
    aggregator.assert_metric(
        'datadog.vsphere.collect_events.time', tags=['vcenter_server:FAKE'], hostname='stubbed.hostname'
    )
    aggregator.assert_metric(
        'datadog.vsphere.refresh_metrics_metadata_cache.time', tags=['vcenter_server:FAKE'], hostname='stubbed.hostname'
    )
    aggregator.assert_metric(
        'datadog.vsphere.refresh_infrastructure_cache.time',
        tags=['collect_property_metrics:False', 'vcenter_server:FAKE'],
        hostname='stubbed.hostname',
    )
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-5')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-15')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-19')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='vm4-6')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='vm4-7')
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='vm4-8')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='$VM3-2')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='VM3-1')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='VM4-1')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='vm4-6')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='vm4-7')
    aggregator.assert_metric('vsphere.mem.entitlement.avg', tags=['vcenter_server:FAKE'], hostname='vm4-8')
    datadog_agent.assert_external_tags(
        'VM4-5',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'VM4-15',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'VM4-19',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm4-6',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm4-7',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm4-8',
        {
            'vsphere': [
                'vcenter_server:FAKE',
                'vsphere_cluster:Cluster2',
                'vsphere_datacenter:Datacenter2',
                'vsphere_folder:Datacenters',
                'vsphere_folder:Discovered virtual machine',
                'vsphere_folder:vm',
                'vsphere_host:10.0.0.104',
                'vsphere_type:vm',
            ]
        },
    )


@pytest.mark.usefixtures("mock_type", "mock_threadpool", "mock_api", "mock_rest_api")
def test_hostname_case_invalid_value(realtime_instance):
    realtime_instance['hostname_transform'] = 'something else'
    with pytest.raises(ConfigurationError):
        _ = VSphereCheck('vsphere', {}, [realtime_instance])
