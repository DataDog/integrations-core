# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.time import get_current_datetime
from pyVmomi import vim

from datadog_checks.vsphere import VSphereCheck

from .common import VSPHERE_VERSION

pytestmark = [pytest.mark.unit]


def test_service_check_critical(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock(side_effect=Exception("Connection error"))
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        with pytest.raises(Exception):
            check = VSphereCheck('vsphere', {}, [events_only_instance])
            dd_run_check(check)
        aggregator.assert_service_check("vsphere.can_connect", AgentCheck.CRITICAL, tags=['vcenter_server:FAKE'])


def test_service_check_ok(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        aggregator.assert_service_check("vsphere.can_connect", AgentCheck.OK, tags=['vcenter_server:FAKE'])


def test_metadata(datadog_agent, aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        mock_si = mock.MagicMock()
        mock_si.content.about.version = VSPHERE_VERSION
        mock_si.content.about.build = '123456789'
        mock_si.content.about.apiType = 'VirtualCenter'
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
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


def test_event_alarm_status_changed(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.AlarmStatusChangedEvent()
        event.createdTime = get_current_datetime()
        event.entity = vim.event.ManagedEntityEventArgument()
        event.entity.entity = vim.VirtualMachine(moId="vm1")
        event.entity.name = "vm1"
        event.alarm = vim.event.AlarmEventArgument()
        event.alarm.name = "alarm1"
        setattr(event, 'from', 'green')
        event.to = 'yellow'
        event.datacenter = vim.event.DatacenterEventArgument()
        event.datacenter.name = "dc1"
        event.fullFormattedMessage = "Green to Yellow"

        mock_si = mock.MagicMock()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        aggregator.assert_event("""vCenter monitor status changed on this alarm, it was green and it's now yellow.""")


def test_event_vm_powered_on(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.VmPoweredOnEvent()
        event.createdTime = get_current_datetime()
        event.userName = "datadog"
        event.host = vim.event.HostEventArgument()
        event.host.name = "host1"
        event.datacenter = vim.event.DatacenterEventArgument()
        event.datacenter.name = "dc1"
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"
        event.fullFormattedMessage = "Virtual machine powered on"

        mock_si = mock.MagicMock()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        aggregator.assert_event(
            """datadog has powered on this virtual machine. It is running on:
- datacenter: dc1
- host: host1
"""
        )


def test_event_vm_powered_off(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.VmPoweredOffEvent()
        event.userName = "datadog"
        event.createdTime = get_current_datetime()
        event.host = vim.event.HostEventArgument()
        event.host.name = "host1"
        event.datacenter = vim.event.DatacenterEventArgument()
        event.datacenter.name = "dc1"
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"
        event.fullFormattedMessage = "Virtual machine powered off"

        mock_si = mock.MagicMock()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        aggregator.assert_event(
            """datadog has powered off this virtual machine. It was running on:
- datacenter: dc1
- host: host1
"""
        )
