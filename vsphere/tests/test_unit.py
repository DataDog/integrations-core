# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime as dt

import mock
import pytest
from pyVmomi import vim, vmodl

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.time import get_current_datetime
from datadog_checks.vsphere import VSphereCheck

from .common import (
    VSPHERE_VERSION,
    default_instance,
    historical_instance,
    legacy_default_instance,
    legacy_historical_instance,
    legacy_realtime_host_exclude_instance,
    legacy_realtime_host_include_instance,
    legacy_realtime_instance,
    realtime_blacklist_instance,
    realtime_instance,
    realtime_whitelist_instance,
)

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ("instance", "log_deprecation_warning"),
    [
        pytest.param(
            legacy_default_instance,
            True,
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            False,
            id='New version',
        ),
    ],
)
def test_log_deprecation_warning(dd_run_check, caplog, instance, log_deprecation_warning):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        deprecation_message = 'DEPRECATION NOTICE: You are using a deprecated version of the vSphere integration.'
        assert (
            (deprecation_message in caplog.text)
            if log_deprecation_warning
            else (deprecation_message not in caplog.text)
        )


@pytest.mark.parametrize(
    ("instance", "service_check", "expected_tags"),
    [
        pytest.param(
            legacy_default_instance,
            'vcenter.can_connect',
            ['vcenter_host:vsphere_host', 'vcenter_server:vsphere_mock'],
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            'vsphere.can_connect',
            ['vcenter_server:vsphere_host'],
            id='New version',
        ),
    ],
)
def test_connection_exception(aggregator, dd_run_check, instance, service_check, expected_tags):
    mock_connect = mock.MagicMock(side_effect=[Exception("Connection error")])
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        with pytest.raises(Exception):
            check = VSphereCheck('vsphere', {}, [instance])
            dd_run_check(check)
        aggregator.assert_service_check(
            service_check,
            AgentCheck.CRITICAL,
            tags=expected_tags,
        )
        assert len(aggregator._metrics) == 0
        assert len(aggregator.events) == 0


@pytest.mark.parametrize(
    ("instance", "service_check", "expected_tags"),
    [
        pytest.param(
            legacy_default_instance,
            'vcenter.can_connect',
            ['vcenter_host:vsphere_host', 'vcenter_server:vsphere_mock'],
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            'vsphere.can_connect',
            ['vcenter_server:vsphere_host'],
            id='New version',
        ),
    ],
)
def test_connection_ok(aggregator, dd_run_check, instance, service_check, expected_tags):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check(service_check, AgentCheck.OK, tags=expected_tags)


def test_legacy_metadata(datadog_agent, aggregator, dd_run_check):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.about.version = VSPHERE_VERSION
        mock_si.content.about.build = '123456789'
        mock_si.content.about.apiType = 'VirtualCenter'
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [legacy_default_instance])
        check.check_id = 'test:123'
        dd_run_check(check)
        datadog_agent.assert_metadata_count(0)


def test_metadata(datadog_agent, aggregator, dd_run_check):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.about.version = VSPHERE_VERSION
        mock_si.content.about.build = '123456789'
        mock_si.content.about.apiType = 'VirtualCenter'
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_connect.return_value = mock_si
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


def test_disabled_metadata(datadog_agent, aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        mock_si = mock.MagicMock()
        mock_si.content.about.version = VSPHERE_VERSION
        mock_si.content.about.build = '123456789'
        mock_si.content.about.apiType = 'VirtualCenter'
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        check.check_id = 'test:123'
        datadog_agent._config["enable_metadata_collection"] = False
        dd_run_check(check)
        datadog_agent.assert_metadata_count(0)


@pytest.mark.parametrize(
    ("instance", "service_check", "query_events_call_count"),
    [
        pytest.param(
            legacy_default_instance,
            'vcenter.can_connect',
            1,
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            'vsphere.can_connect',
            2,
            id='New version',
        ),
    ],
)
def test_event_exception(aggregator, dd_run_check, instance, service_check, query_events_call_count):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.side_effect = [Exception()]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check(
            service_check,
            AgentCheck.CRITICAL,
            count=0,
        )
        assert len(aggregator.events) == 0
        assert mock_si.content.eventManager.QueryEvents.call_count == query_events_call_count


@pytest.mark.parametrize(
    ("instance",),
    [
        pytest.param(
            legacy_default_instance,
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            id='New version',
        ),
    ],
)
def test_two_events(aggregator, dd_run_check, instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        event1 = vim.event.VmMessageEvent()
        event1.createdTime = get_current_datetime()
        event1.vm = vim.event.VmEventArgument()
        event1.vm.name = "vm1"
        event1.fullFormattedMessage = "First event in time"

        event2 = vim.event.VmMessageEvent()
        event2.createdTime = get_current_datetime()
        event2.vm = vim.event.VmEventArgument()
        event2.vm.name = "vm1"
        event2.fullFormattedMessage = "Second event in time"

        mock_si = mock.MagicMock()
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.side_effect = [[event1, event2]]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        assert len(aggregator.events) == 2
        assert mock_si.content.eventManager.QueryEvents.call_count == 1


@pytest.mark.parametrize(
    ("instance",),
    [
        pytest.param(
            legacy_default_instance,
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            id='New version',
        ),
    ],
)
def test_two_calls_to_queryevents(aggregator, dd_run_check, instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        event1 = vim.event.VmMessageEvent()
        event1.createdTime = get_current_datetime()
        event1.vm = vim.event.VmEventArgument()
        event1.vm.name = "vm1"
        event1.fullFormattedMessage = "First event in time"

        event2 = vim.event.VmMessageEvent()
        event2.createdTime = get_current_datetime()
        event2.vm = vim.event.VmEventArgument()
        event2.vm.name = "vm1"
        event2.fullFormattedMessage = "Second event in time"

        mock_si = mock.MagicMock()
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.side_effect = [[event1, event2], []]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        assert len(aggregator.events) == 2
        aggregator.reset()
        dd_run_check(check)
        assert len(aggregator.events) == 0
        assert mock_si.content.eventManager.QueryEvents.call_count == 2


@pytest.mark.parametrize(
    ("instance",),
    [
        pytest.param(
            legacy_default_instance,
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            id='New version',
        ),
    ],
)
def test_event_filtered(aggregator, dd_run_check, instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        event = vim.event.VmDiskFailedEvent()
        event.createdTime = get_current_datetime()

        mock_si = mock.MagicMock()
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        assert len(aggregator.events) == 0


@pytest.mark.parametrize(
    (
        "instance",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_default_instance,
            [
                'vsphere_host:host1',
                'vsphere_host:host2',
                'vsphere_datacenter:dc1',
                'vsphere_datacenter:dc1',
            ],
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            [
                'vcenter_server:vsphere_host',
                'vsphere_host:host1',
                'vsphere_host:host2',
                'vsphere_datacenter:dc1',
                'vsphere_datacenter:dc1',
            ],
            id='New version',
        ),
    ],
)
def test_event_vm_being_hot_migrated_change_host(aggregator, dd_run_check, instance, expected_tags):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        event = vim.event.VmBeingHotMigratedEvent()
        event.createdTime = get_current_datetime()
        event.userName = "datadog"
        event.host = vim.event.HostEventArgument()
        event.host.name = "host1"
        event.destHost = vim.event.HostEventArgument()
        event.destHost.name = "host2"
        event.datacenter = vim.event.DatacenterEventArgument()
        event.datacenter.name = "dc1"
        event.destDatacenter = vim.event.DatacenterEventArgument()
        event.destDatacenter.name = "dc1"
        event.ds = vim.event.DatastoreEventArgument()
        event.ds.name = "ds1"
        event.destDatastore = vim.event.DatastoreEventArgument()
        event.destDatastore.name = "ds1"
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"

        mock_si = mock.MagicMock()
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        aggregator.assert_event(
            """datadog has launched a hot migration of this virtual machine:
- Host MIGRATION: from host1 to host2
- No datacenter migration: still dc1
- No datastore migration: still ds1""",
            count=1,
            msg_title="VM vm1 is being migrated",
            host="vm1",
            tags=expected_tags,
        )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_default_instance,
            [
                'vsphere_host:host1',
                'vsphere_host:host2',
                'vsphere_datacenter:dc1',
                'vsphere_datacenter:dc2',
            ],
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            [
                'vcenter_server:vsphere_host',
                'vsphere_host:host1',
                'vsphere_host:host2',
                'vsphere_datacenter:dc1',
                'vsphere_datacenter:dc2',
            ],
            id='New version',
        ),
    ],
)
def test_event_vm_being_hot_migrated_change_datacenter(aggregator, dd_run_check, instance, expected_tags):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        event = vim.event.VmBeingHotMigratedEvent()
        event.createdTime = get_current_datetime()
        event.userName = "datadog"
        event.host = vim.event.HostEventArgument()
        event.host.name = "host1"
        event.destHost = vim.event.HostEventArgument()
        event.destHost.name = "host2"
        event.datacenter = vim.event.DatacenterEventArgument()
        event.datacenter.name = "dc1"
        event.destDatacenter = vim.event.DatacenterEventArgument()
        event.destDatacenter.name = "dc2"
        event.ds = vim.event.DatastoreEventArgument()
        event.ds.name = "ds1"
        event.destDatastore = vim.event.DatastoreEventArgument()
        event.destDatastore.name = "ds1"
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"

        mock_si = mock.MagicMock()
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        aggregator.assert_event(
            """datadog has launched a hot migration of this virtual machine:
- Datacenter MIGRATION: from dc1 to dc2
- Host MIGRATION: from host1 to host2
- No datastore migration: still ds1""",
            count=1,
            msg_title="VM vm1 is being migrated",
            host="vm1",
            tags=expected_tags,
        )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_default_instance,
            [
                'vsphere_host:host1',
                'vsphere_host:host1',
                'vsphere_datacenter:dc1',
                'vsphere_datacenter:dc1',
            ],
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            [
                'vcenter_server:vsphere_host',
                'vsphere_host:host1',
                'vsphere_host:host1',
                'vsphere_datacenter:dc1',
                'vsphere_datacenter:dc1',
            ],
            id='New version',
        ),
    ],
)
def test_event_vm_being_hot_migrated_change_datastore(aggregator, dd_run_check, instance, expected_tags):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        event = vim.event.VmBeingHotMigratedEvent()
        event.createdTime = get_current_datetime()
        event.userName = "datadog"
        event.host = vim.event.HostEventArgument()
        event.host.name = "host1"
        event.destHost = vim.event.HostEventArgument()
        event.destHost.name = "host1"
        event.datacenter = vim.event.DatacenterEventArgument()
        event.datacenter.name = "dc1"
        event.destDatacenter = vim.event.DatacenterEventArgument()
        event.destDatacenter.name = "dc1"
        event.ds = vim.event.DatastoreEventArgument()
        event.ds.name = "ds1"
        event.destDatastore = vim.event.DatastoreEventArgument()
        event.destDatastore.name = "ds2"
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"

        mock_si = mock.MagicMock()
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        aggregator.assert_event(
            """datadog has launched a hot migration of this virtual machine:
- Datastore MIGRATION: from ds1 to ds2
- No host migration: still host1
- No datacenter migration: still dc1""",
            count=1,
            msg_title="VM vm1 is being migrated",
            host="vm1",
            tags=expected_tags,
        )


@pytest.mark.parametrize(
    ("instance",),
    [
        pytest.param(
            legacy_default_instance,
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            id='New version',
        ),
    ],
)
def test_event_alarm_status_changed_excluded(aggregator, dd_run_check, instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
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
        event.fullFormattedMessage = "Green to Gray"

        mock_si = mock.MagicMock()
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        assert len(aggregator.events) == 0


@pytest.mark.parametrize(
    (
        "instance",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_default_instance,
            None,
            id='Legacy version',
        ),
        pytest.param(
            default_instance,
            [
                'vcenter_server:vsphere_host',
            ],
            id='New version',
        ),
    ],
)
def test_event_alarm_status_changed_vm(aggregator, dd_run_check, instance, expected_tags):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
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
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        aggregator.assert_event(
            """vCenter monitor status changed on this alarm, it was green and it's now yellow.""",
            count=1,
            msg_title="[Triggered] alarm1 on VM vm1 is now yellow",
            alert_type="warning",
            host="vm1",
            tags=expected_tags,
        )


def test_event_alarm_status_changed_vm_recovered(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.AlarmStatusChangedEvent()
        event.createdTime = get_current_datetime()
        event.entity = vim.event.ManagedEntityEventArgument()
        event.entity.entity = vim.VirtualMachine(moId="vm1")
        event.entity.name = "vm1"
        event.alarm = vim.event.AlarmEventArgument()
        event.alarm.name = "alarm1"
        setattr(event, 'from', 'red')
        event.to = 'green'
        event.datacenter = vim.event.DatacenterEventArgument()
        event.datacenter.name = "dc1"
        event.fullFormattedMessage = "Green to Yellow"

        mock_si = mock.MagicMock()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        aggregator.assert_event("""vCenter monitor status changed on this alarm, it was red and it's now green.""")


def test_event_alarm_status_changed_host(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.AlarmStatusChangedEvent()
        event.createdTime = get_current_datetime()
        event.entity = vim.event.ManagedEntityEventArgument()
        event.entity.entity = vim.HostSystem(moId="host1")
        event.entity.name = "host1"
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


def test_event_alarm_status_changed_other(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.AlarmStatusChangedEvent()
        event.createdTime = get_current_datetime()
        event.entity = vim.event.ManagedEntityEventArgument()
        event.entity.entity = vim.Folder(moId="host1")
        event.entity.name = "folder1"
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
        assert len(aggregator.events) == 0


def test_event_alarm_status_changed_wrong_from(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.AlarmStatusChangedEvent()
        event.createdTime = get_current_datetime()
        event.entity = vim.event.ManagedEntityEventArgument()
        event.entity.entity = vim.VirtualMachine(moId="vm1")
        event.entity.name = "vm1"
        event.alarm = vim.event.AlarmEventArgument()
        event.alarm.name = "alarm1"
        setattr(event, 'from', 'other')
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
        assert len(aggregator.events) == 0


def test_event_alarm_status_changed_wrong_to(aggregator, dd_run_check, events_only_instance):
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
        event.to = 'other'
        event.datacenter = vim.event.DatacenterEventArgument()
        event.datacenter.name = "dc1"
        event.fullFormattedMessage = "Green to Yellow"

        mock_si = mock.MagicMock()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        assert len(aggregator.events) == 0


def test_event_vm_message(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.VmMessageEvent()
        event.createdTime = get_current_datetime()
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"
        event.fullFormattedMessage = "Event example"

        mock_si = mock.MagicMock()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        aggregator.assert_event("""@@@\nEvent example\n@@@""", msg_title="VM vm1 is reporting", host="vm1")


def test_event_vm_migrated(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.VmMigratedEvent()
        event.createdTime = get_current_datetime()
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"
        event.fullFormattedMessage = "Event example"

        mock_si = mock.MagicMock()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        aggregator.assert_event("""@@@\nEvent example\n@@@""", msg_title="VM vm1 has been migrated", host="vm1")


def test_event_task(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.TaskEvent()
        event.createdTime = get_current_datetime()
        event.fullFormattedMessage = "Task completed successfully"

        mock_si = mock.MagicMock()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        aggregator.assert_event("""@@@\nTask completed successfully\n@@@""")


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
""",
            count=1,
        )


def test_event_vm_reconfigured(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.VmReconfiguredEvent()
        event.userName = "datadog"
        event.createdTime = get_current_datetime()
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"
        event.configSpec = vim.vm.ConfigSpec()

        mock_si = mock.MagicMock()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [events_only_instance])
        dd_run_check(check)
        aggregator.assert_event(
            """datadog saved the new configuration:\n@@@\n""",
            count=1,
            exact_match=False,
            msg_title="VM vm1 configuration has been changed",
            host="vm1",
        )


def test_event_vm_suspended(aggregator, dd_run_check, events_only_instance):
    mock_connect = mock.MagicMock()
    with mock.patch('pyVim.connect.SmartConnect', new=mock_connect):
        event = vim.event.VmSuspendedEvent()
        event.userName = "datadog"
        event.createdTime = get_current_datetime()
        event.host = vim.event.HostEventArgument()
        event.host.name = "host1"
        event.datacenter = vim.event.DatacenterEventArgument()
        event.datacenter.name = "dc1"
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"

        mock_si = mock.MagicMock()
        mock_si.content.eventManager = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_connect.return_value = mock_si
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


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_realtime_instance,
            1,
            2,
            ['vcenter_server:vsphere_mock'],
            id='Legacy version',
        ),
        pytest.param(
            realtime_instance,
            2,
            2,
            ['vcenter_server:vsphere_host', 'vsphere_host:unknown', 'vsphere_type:vm'],
            id='New version',
        ),
    ],
)
def test_report_realtime_vm_count(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags, mock_connect
):
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vm.count',
        count=expected_count,
        value=expected_value,
        tags=expected_tags,
    )


def test_report_realtime_vm_metrics(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
            token='123',
        )
        mock_si.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = (
            vim.PropertyCollector.RetrieveResult(
                objects=[
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
                    )
                ]
            )
        )
        mock_connect.return_value = mock_si
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


def test_report_realtime_vm_metrics_invalid_value(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[-3],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
        )
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [realtime_instance])
        dd_run_check(check)
        aggregator.assert_metric(
            'vsphere.cpu.costop.sum',
            count=0,
        )


def test_report_realtime_vm_metrics_empty_value(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
        )
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [realtime_instance])
        dd_run_check(check)
        aggregator.assert_metric(
            'vsphere.cpu.costop.sum',
            count=0,
        )


def test_report_realtime_vm_metrics_counter_id_not_found(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=200,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[5],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
        )
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [realtime_instance])
        dd_run_check(check)
        aggregator.assert_metric(
            'vsphere.cpu.costop.sum',
            count=0,
        )


def test_report_realtime_vm_metrics_instance_one_value(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100, instance='vm1'),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
            token='123',
        )
        mock_si.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = (
            vim.PropertyCollector.RetrieveResult(
                objects=[
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
                    )
                ]
            )
        )
        mock_connect.return_value = mock_si
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
            tags=['vcenter_server:FAKE', 'cpu_core:vm1'],
        )


def test_report_realtime_vm_metrics_instance_two_values(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100, instance='vm1'),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100, instance='vm2'),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
            token='123',
        )
        mock_si.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = (
            vim.PropertyCollector.RetrieveResult(
                objects=[
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
                    )
                ]
            )
        )
        mock_connect.return_value = mock_si
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
            tags=['vcenter_server:FAKE', 'cpu_core:vm1'],
        )
        aggregator.assert_metric(
            'vsphere.cpu.costop.sum',
            value=11,
            count=1,
            hostname='vm2',
            tags=['vcenter_server:FAKE', 'cpu_core:vm2'],
        )


def test_report_realtime_vm_metrics_runtime_host(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.side_effect = [
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=100),
                        )
                    ],
                ),
            ],
            [],
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
        mock_connect.return_value = mock_si
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


def test_report_realtime_vm_metrics_runtime_host_not_in_infrastructure(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.side_effect = [
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=100),
                        )
                    ],
                ),
            ],
            [],
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
        mock_connect.return_value = mock_si
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


def test_report_realtime_vm_metrics_guest_hostname(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
            token='123',
        )
        mock_si.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = (
            vim.PropertyCollector.RetrieveResult(
                objects=[
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
                    )
                ]
            )
        )
        mock_connect.return_value = mock_si
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
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
            token='123',
        )
        mock_si.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = (
            vim.PropertyCollector.RetrieveResult(
                objects=[
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
                    )
                ]
            )
        )
        mock_connect.return_value = mock_si
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


def test_report_realtime_vm_metrics_filtered(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
            token='123',
        )
        mock_si.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = (
            vim.PropertyCollector.RetrieveResult(
                objects=[
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
                    )
                ]
            )
        )
        mock_connect.return_value = mock_si
        realtime_instance['metric_filters'] = {'vm': ['cpu.maxlimited.sum']}
        check = VSphereCheck('vsphere', {}, [realtime_instance])
        dd_run_check(check)
        aggregator.assert_metric('vsphere.cpu.costop.sum', count=0)


def test_report_realtime_vm_metrics_whitelisted(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
            token='123',
        )
        mock_si.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = (
            vim.PropertyCollector.RetrieveResult(
                objects=[
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
                    )
                ]
            )
        )
        mock_connect.return_value = mock_si
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


def test_report_realtime_vm_metrics_blacklisted(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
            token='123',
        )
        mock_si.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = (
            vim.PropertyCollector.RetrieveResult(
                objects=[
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
                    )
                ]
            )
        )
        mock_connect.return_value = mock_si
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


def test_report_realtime_vm_metrics_off(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
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
                )
            ],
            token='123',
        )
        mock_si.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = (
            vim.PropertyCollector.RetrieveResult(
                objects=[
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
                    )
                ]
            )
        )
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [realtime_instance])
        dd_run_check(check)
        aggregator.assert_metric(
            'vsphere.cpu.costop.sum',
            value=52,
            count=0,
            tags=['vcenter_server:FAKE'],
        )
        aggregator.assert_metric(
            'vsphere.cpu.costop.sum',
            value=11,
            count=1,
            hostname='vm2',
            tags=['vcenter_server:FAKE'],
        )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_realtime_instance,
            0,
            0,
            None,
            id='Legacy version',
        ),
        pytest.param(
            realtime_instance,
            1,
            1,
            ['vcenter_server:vsphere_host', 'vsphere_type:host'],
            id='New version',
        ),
    ],
)
def test_report_realtime_host_count(aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.latestEvent.createdTime = dt.datetime.now()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
                unitInfo=vim.ElementDescription(key='millisecond'),
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.HostSystem(moId="host1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[34, 61],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host1',
                        ),
                    ],
                )
            ],
        )
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [instance])
        dd_run_check(check)
        aggregator.assert_metric(
            'vsphere.host.count',
            count=expected_count,
            value=expected_value,
            tags=expected_tags,
        )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_hostname",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_historical_instance,
            1,
            61,
            'host1',
            ['vcenter_server:vsphere_host'],
            id='Legacy version',
        ),
        pytest.param(
            historical_instance,
            1,
            61,
            'host1',
            ['vcenter_server:vsphere_host'],
            id='New version',
        ),
    ],
)
def test_report_realtime_host_metrics(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_hostname, expected_tags
):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.HostSystem(moId="host1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[34, 61],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host1',
                        ),
                    ],
                )
            ],
        )
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [realtime_instance])
        dd_run_check(check)
        aggregator.assert_metric(
            'vsphere.cpu.costop.sum',
            count=expected_count,
            value=expected_value,
            hostname=expected_hostname,
            tags=expected_tags,
        )


def test_report_realtime_host_metrics_filtered(aggregator, dd_run_check, realtime_instance):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.HostSystem(moId="host1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[34, 61],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.HostSystem(moId="host1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='host1',
                        ),
                    ],
                )
            ],
        )
        mock_connect.return_value = mock_si
        realtime_instance['metric_filters'] = {'host': ['cpu.maxlimited.sum']}
        check = VSphereCheck('vsphere', {}, [realtime_instance])
        dd_run_check(check)
        aggregator.assert_metric('vsphere.cpu.costop.sum', count=0)


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_realtime_host_include_instance,
            1,
            61,
            ['instance:host1'],
            id='Legacy version',
        ),
        pytest.param(
            realtime_whitelist_instance,
            1,
            61,
            ['vcenter_server:vsphere_host'],
            id='New version',
        ),
    ],
)
def test_report_realtime_host_metrics_whitelisted(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags, mock_connect
):
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.costop.sum',
        count=expected_count,
        value=expected_value,
        tags=expected_tags,
    )


@pytest.mark.parametrize(
    ("instance",),
    [
        pytest.param(
            legacy_realtime_host_exclude_instance,
            id='Legacy version',
        ),
        pytest.param(
            realtime_blacklist_instance,
            id='New version',
        ),
    ],
)
def test_report_realtime_host_metrics_blacklisted(aggregator, dd_run_check, instance, mock_connect):
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('vsphere.cpu.costop.sum', count=0)


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_historical_instance,
            0,
            0,
            None,
            id='Legacy version',
        ),
        pytest.param(
            historical_instance,
            1,
            1,
            ['vcenter_server:vsphere_host', 'vsphere_datacenter:dc1', 'vsphere_type:datacenter'],
            id='dc1 in New version with tags',
        ),
        pytest.param(
            historical_instance,
            1,
            1,
            [
                'vcenter_server:vsphere_host',
                'vsphere_datacenter:dc2',
                'vsphere_folder:folder_1',
                'vsphere_type:datacenter',
            ],
            id='dc2 in New version with tags',
        ),
        pytest.param(
            historical_instance,
            1,
            2,
            None,
            id='Grouped datacenters in New version',
        ),
    ],
)
def test_report_historical_datacenter_count(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags, mock_connect
):
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datacenter.count',
        count=expected_count,
        value=expected_value,
        tags=expected_tags,
    )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_historical_instance,
            1,
            7,
            ['instance:dc1', 'vcenter_server:vsphere_mock', 'vsphere_datacenter:dc1', 'vsphere_type:datacenter'],
            id='Legacy version',
        ),
        pytest.param(
            historical_instance,
            1,
            7,
            ['vcenter_server:vsphere_host', 'vsphere_datacenter:dc1', 'vsphere_type:datacenter'],
            id='New version',
        ),
    ],
)
def test_report_historical_datacenter_metrics(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags, mock_connect
):
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=expected_count,
        value=expected_value,
        tags=expected_tags,
    )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_historical_instance,
            1,
            3,
            [
                'instance:dc2',
                'vcenter_server:vsphere_mock',
                'vsphere_datacenter:dc2',
                'vsphere_folder:folder_1',
                'vsphere_type:datacenter',
            ],
            id='Legacy version',
        ),
        pytest.param(
            historical_instance,
            1,
            3,
            [
                'vcenter_server:vsphere_host',
                'vsphere_datacenter:dc2',
                'vsphere_folder:folder_1',
                'vsphere_type:datacenter',
            ],
            id='New version',
        ),
    ],
)
def test_report_historical_datacenter_in_folder_metrics(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags, mock_connect
):
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.vmop.numChangeDS.latest',
        count=expected_count,
        value=expected_value,
        tags=expected_tags,
    )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_historical_instance,
            0,
            0,
            None,
            id='Legacy version',
        ),
        pytest.param(
            historical_instance,
            1,
            1,
            ['vcenter_server:vsphere_host', 'vsphere_datastore:NFS-Share-1', 'vsphere_type:datastore'],
            id='New version',
        ),
    ],
)
def test_report_historical_datastore_count(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags, mock_connect
):
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datastore.count',
        count=expected_count,
        value=expected_value,
        tags=expected_tags,
    )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_historical_instance,
            1,
            5,
            ['instance:ds1', 'vcenter_server:vsphere_mock', 'vsphere_datastore:NFS-Share-1', 'vsphere_type:datastore'],
            id='Legacy version',
        ),
        pytest.param(
            historical_instance,
            1,
            5,
            ['vcenter_server:vsphere_host', 'vsphere_datastore:NFS-Share-1', 'vsphere_type:datastore'],
            id='New version',
        ),
    ],
)
def test_report_historical_datastore_metrics(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags, mock_connect
):
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datastore.busResets.sum',
        count=expected_count,
        value=expected_value,
        tags=expected_tags,
    )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_historical_instance,
            0,
            0,
            None,
            id='Legacy version',
        ),
        pytest.param(
            historical_instance,
            1,
            1,
            ['vcenter_server:vsphere_host', 'vsphere_cluster:c1', 'vsphere_type:cluster'],
            id='New version',
        ),
    ],
)
def test_report_historical_cluster_count(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags, mock_connect
):
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cluster.count',
        count=expected_count,
        value=expected_value,
        tags=expected_tags,
    )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_historical_instance,
            1,
            5,
            ['instance:c1', 'vcenter_server:vsphere_mock', 'vsphere_cluster:c1', 'vsphere_type:cluster'],
            id='Legacy version',
        ),
        pytest.param(
            historical_instance,
            1,
            5,
            ['vcenter_server:vsphere_host', 'vsphere_cluster:c1', 'vsphere_type:cluster'],
            id='New version',
        ),
    ],
)
def test_report_historical_cluster_metrics(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags, mock_connect
):
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.cpu.totalmhz.avg',
        count=expected_count,
        value=expected_value,
        tags=expected_tags,
    )


@pytest.mark.parametrize(
    (
        "instance",
        "expected_count",
        "expected_value",
        "expected_tags",
    ),
    [
        pytest.param(
            legacy_historical_instance,
            1,
            5,
            [
                'instance:ds1',
                'vcenter_server:vsphere_mock',
                'vsphere_datastore:NFS-Share-1',
                'vsphere_type:datastore',
            ],
            id='Legacy version',
        ),
        pytest.param(
            historical_instance,
            1,
            5,
            [
                'my_cat_name_2:my_tag_name_2',
                'vcenter_server:vsphere_host',
                'vsphere_datastore:NFS-Share-1',
                'vsphere_type:datastore',
            ],
            id='New version',
        ),
    ],
)
def test_report_historical_metrics_with_tags(
    aggregator, dd_run_check, instance, expected_count, expected_value, expected_tags, mock_connect, mock_rest_api
):

    instance['collect_tags'] = True
    check = VSphereCheck('vsphere', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'vsphere.datastore.busResets.sum',
        count=expected_count,
        value=expected_value,
        tags=expected_tags,
    )
