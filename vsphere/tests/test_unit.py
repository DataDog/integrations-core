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
