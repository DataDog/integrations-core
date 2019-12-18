# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import time
from datetime import datetime

import mock
import pytest
from mock import MagicMock
from pyVmomi import vim

from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.cache_config import CacheConfig
from datadog_checks.vsphere.common import SOURCE_TYPE
from datadog_checks.vsphere.errors import BadConfigError, ConnectionError
from datadog_checks.vsphere.vsphere import (
    REFRESH_METRICS_METADATA_INTERVAL,
    REFRESH_MORLIST_INTERVAL,
    RESOURCE_TYPE_METRICS,
    SHORT_ROLLUP,
)

from .utils import MockedMOR, assertMOR, disable_thread_pool, get_mocked_server

SERVICE_CHECK_TAGS = ["vcenter_server:vsphere_mock", "vcenter_host:None", "foo:bar"]


def test__init__(instance):
    with pytest.raises(BadConfigError):
        # Must define a unique 'name' per vCenter instance
        VSphereCheck('vsphere', {}, {}, [{'': ''}])

    init_config = {
        'clean_morlist_interval': 50,
        'refresh_morlist_interval': 42,
        'refresh_metrics_metadata_interval': -42,
        'batch_property_collector_size': -1,
    }
    check = VSphereCheck('vsphere', init_config, {}, [instance])
    i_key = check._instance_key(instance)

    assert check.time_started > 0
    assert not check.server_instances
    assert check.cache_config.get_interval(CacheConfig.Morlist, i_key) == 42
    assert check.cache_config.get_interval(CacheConfig.Metadata, i_key) == -42
    assert check.clean_morlist_interval == 50
    assert len(check.event_config) == 1
    assert 'vsphere_mock' in check.event_config
    assert not check.registry
    assert not check.latest_event_query
    assert check.batch_collector_size == 0
    assert check.batch_morlist_size == 50
    assert check.excluded_host_tags == []


def test_excluded_host_tags(vsphere, instance, aggregator):
    # Check default value and precedence of instance config over init config
    check = VSphereCheck('vsphere', {}, {}, [instance])
    assert check.excluded_host_tags == []
    check = VSphereCheck('vsphere', {"excluded_host_tags": ["vsphere_host"]}, {}, [instance])
    assert check.excluded_host_tags == ["vsphere_host"]
    instance["excluded_host_tags"] = []
    check = VSphereCheck('vsphere', {"excluded_host_tags": ["vsphere_host"]}, {}, [instance])
    assert check.excluded_host_tags == []

    # Test host tags are excluded from external host metadata, but still stored in the cache for metrics
    vsphere.excluded_host_tags = ["vsphere_host"]
    mocked_vm = MockedMOR(spec="VirtualMachine")
    mocked_host = MockedMOR(spec="HostSystem")
    mocked_mors_attrs = {
        mocked_vm: {
            "name": "mocked_vm",
            "parent": mocked_host,
            "runtime.powerState": vim.VirtualMachinePowerState.poweredOn,
        },
        mocked_host: {"name": "mocked_host", "parent": None},
    }

    with mock.patch("datadog_checks.vsphere.VSphereCheck._collect_mors_and_attributes", return_value=mocked_mors_attrs):

        server_instance = vsphere._get_server_instance(instance)
        result = MagicMock()
        result.value = [23.4]
        server_instance.content.perfManager.QueryPerf.return_value = [MagicMock(value=[result], entity=mocked_vm)]
        vsphere.metadata_cache = MagicMock()
        vsphere.metadata_cache.get_metadata.return_value = {"name": "mymetric", "unit": "kb"}
        vsphere.in_compatibility_mode = MagicMock()
        vsphere.in_compatibility_mode.return_value = False

        vsphere.check(instance)
        ext_host_tags = vsphere.get_external_host_tags()

        # vsphere_host tag not in external metadata
        for host, source_tags in ext_host_tags:
            if host == u"mocked_vm":
                tags = source_tags["vsphere"]
                for tag in tags:
                    assert "vsphere_host:" not in tag
                break

        # vsphere_host tag still in cache for sending with metrics
        aggregator.assert_metric('vsphere.mymetric', value=23.4, hostname="mocked_vm", count=1)
        aggregator.assert_metric_has_tag('vsphere.mymetric', tag="vsphere_host:mocked_host", count=1)


def test__is_excluded():
    """
     * Exclude hosts/vms not compliant with the user's `*_include` configuration.
     * Exclude "non-labeled" virtual machines when the user configuration instructs to.
    """
    # Sample(s)
    include_regexes = {'host_include': "f[o]+", 'vm_include': "f[o]+"}

    # OK
    included_host = MockedMOR(spec="HostSystem", name="foo")
    included_vm = MockedMOR(spec="VirtualMachine", name="foo")

    assert not VSphereCheck._is_excluded(included_host, {"name": included_host.name}, include_regexes, None)
    assert not VSphereCheck._is_excluded(included_vm, {"name": included_vm.name}, include_regexes, None)

    # Not OK!
    excluded_host = MockedMOR(spec="HostSystem", name="bar")
    excluded_vm = MockedMOR(spec="VirtualMachine", name="bar")

    assert VSphereCheck._is_excluded(excluded_host, {"name": excluded_host.name}, include_regexes, None)
    assert VSphereCheck._is_excluded(excluded_vm, {"name": excluded_vm.name}, include_regexes, None)

    # Sample(s)
    include_regexes = None
    include_only_marked = True

    # OK
    included_vm = MockedMOR(spec="VirtualMachine", name="foo", label=True)
    assert not VSphereCheck._is_excluded(
        included_vm, {"customValue": included_vm.customValue}, include_regexes, include_only_marked
    )

    # Not OK
    included_vm = MockedMOR(spec="VirtualMachine", name="foo")
    assert VSphereCheck._is_excluded(included_vm, {"customValue": []}, include_regexes, include_only_marked)


def test_vms_in_filtered_host_are_filtered(vsphere, instance):
    """Test that all vms belonging to a filtered host are also filtered"""
    server_instance = vsphere._get_server_instance(instance)
    filtered_host = MockedMOR(spec="HostSystem")
    filtered_vm = MockedMOR(spec="VirtualMachine")
    non_filtered_host = MockedMOR(spec="HostSystem")
    non_filtered_vm = MockedMOR(spec="VirtualMachine")
    mocked_mors_attrs = {
        filtered_host: {"name": "filtered_host_number_1", "parent": None},
        filtered_vm: {
            "name": "this_vm_is_filtered",
            "runtime.powerState": vim.VirtualMachinePowerState.poweredOn,
            "runtime.host": filtered_host,
        },
        non_filtered_host: {"name": "non_filtered_host_number_1", "parent": None},
        non_filtered_vm: {
            "name": "this_vm_is_not_filtered",
            "runtime.powerState": vim.VirtualMachinePowerState.poweredOn,
            "runtime.host": non_filtered_host,
        },
    }

    regex = {'host_include': '^(?!filtered_.+)'}
    with mock.patch("datadog_checks.vsphere.VSphereCheck._collect_mors_and_attributes", return_value=mocked_mors_attrs):
        obj_list = vsphere._get_all_objs(server_instance, regex, False, [])
        assert len(obj_list[vim.VirtualMachine]) == 1
        assert len(obj_list[vim.HostSystem]) == 1
        assert {
            "mor_type": "vm",
            "mor": non_filtered_vm,
            "hostname": "this_vm_is_not_filtered",
            "tags": ["vsphere_host:non_filtered_host_number_1", "vsphere_type:vm"],
        } == obj_list[vim.VirtualMachine][0]
        assert {
            "mor_type": "host",
            "mor": non_filtered_host,
            "hostname": "non_filtered_host_number_1",
            "tags": ["vsphere_type:host"],
        } == obj_list[vim.HostSystem][0]


def test__get_all_objs(vsphere, instance):
    """
    Test that we don't raise KeyError if the property collector failed to collect some attributes
    and that we handle the case were there are missing attributes
    """
    server_instance = vsphere._get_server_instance(instance)

    vm_no_parent = MockedMOR(spec="VirtualMachine")
    vm_no_powerstate = MockedMOR(spec="VirtualMachine")
    vm_host_parent = MockedMOR(spec="VirtualMachine")
    mocked_host = MockedMOR(spec="HostSystem")
    mocked_datastore = MockedMOR(spec="Datastore")
    mocked_datacenter = MockedMOR(spec="Datacenter")
    mocked_cluster = MockedMOR(spec="ClusterComputeResource")
    mocked_mors_attrs = {
        vm_no_parent: {"name": "vm_no_parent", "runtime.powerState": vim.VirtualMachinePowerState.poweredOn},
        vm_no_powerstate: {"name": "vm_no_powerstate"},
        vm_host_parent: {"parent": mocked_host, "runtime.powerState": vim.VirtualMachinePowerState.poweredOn},
        mocked_host: {"name": "mocked_host", "parent": None},
        mocked_datastore: {},
        mocked_cluster: {"name": "cluster"},
        mocked_datacenter: {"parent": MockedMOR(spec="Folder", name="unknown folder"), "name": "datacenter"},
    }
    with mock.patch("datadog_checks.vsphere.VSphereCheck._collect_mors_and_attributes", return_value=mocked_mors_attrs):
        obj_list = vsphere._get_all_objs(server_instance, None, False, [])
        assert len(obj_list[vim.VirtualMachine]) == 2
        assert {
            "mor_type": "vm",
            "mor": vm_no_parent,
            "hostname": "vm_no_parent",
            "tags": ["vsphere_host:unknown", "vsphere_type:vm"],
        } in obj_list[vim.VirtualMachine]
        assert {
            "mor_type": "vm",
            "mor": vm_host_parent,
            "hostname": "unknown",
            "tags": ["vsphere_host:mocked_host", "vsphere_host:unknown", "vsphere_type:vm"],
        } in obj_list[vim.VirtualMachine]
        assert len(obj_list[vim.HostSystem]) == 1
        assert {
            "mor_type": "host",
            "mor": mocked_host,
            "hostname": "mocked_host",
            "tags": ["vsphere_type:host"],
        } in obj_list[vim.HostSystem]
        assert len(obj_list[vim.Datastore]) == 1
        assert {
            "mor_type": "datastore",
            "mor": mocked_datastore,
            "hostname": None,
            "tags": ["vsphere_datastore:unknown", "vsphere_type:datastore"],
        } in obj_list[vim.Datastore]
        assert len(obj_list[vim.Datacenter]) == 1
        assert {
            "mor_type": "datacenter",
            "mor": mocked_datacenter,
            "hostname": None,
            "tags": ["vsphere_folder:unknown", "vsphere_datacenter:datacenter", "vsphere_type:datacenter"],
        } in obj_list[vim.Datacenter]
        assert len(obj_list[vim.ClusterComputeResource]) == 1
        assert {
            "mor_type": "cluster",
            "mor": mocked_cluster,
            "hostname": None,
            "tags": ["vsphere_cluster:cluster", "vsphere_type:cluster"],
        } in obj_list[vim.ClusterComputeResource]


def test__collect_mors_and_attributes(vsphere, instance):
    """
    Test that we check for errors when collecting properties with property collector
    """
    server_instance = vsphere._get_server_instance(instance)
    with mock.patch("datadog_checks.vsphere.vsphere.vmodl"):
        obj = MagicMock(missingSet=None, obj="obj")
        result = MagicMock(token=None, objects=[obj])
        server_instance.content.propertyCollector.RetrievePropertiesEx.return_value = result
        log = MagicMock()
        vsphere.log = log
        mor_attrs = vsphere._collect_mors_and_attributes(server_instance)
        log.error.assert_not_called()
        assert len(mor_attrs) == 1

        obj.missingSet = [MagicMock(path="prop", fault="fault")]
        mor_attrs = vsphere._collect_mors_and_attributes(server_instance)
        log.error.assert_called_once_with('Unable to retrieve property %s for object %s: %s', 'prop', 'obj', 'fault')
        assert len(mor_attrs) == 1


def test__cache_morlist_raw(vsphere, instance):
    """
    Explore the vCenter infrastructure to discover hosts, virtual machines.

    Input topology:
        ```
        rootFolder
            - datacenter1
                - compute_resource1
                    - host1                   # Filtered out
                    - host2
            - folder1
                - datacenter2
                    - compute_resource2
                        - host3
                        - vm1               # Not labeled
                        - vm2               # Filtered out
                        - vm3               # Powered off
                        - vm4
        ```
    """
    # Samples
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        instance["host_include_only_regex"] = "host[2-9]"
        instance["vm_include_only_regex"] = "vm[^2]"
        instance["include_only_marked"] = True

        # Discover hosts and virtual machines
        vsphere._cache_morlist_raw(instance)

        # Assertions: 1 labeled+monitored VM + 2 hosts + 2 datacenters + 2 clusters + 1 datastore.
        assertMOR(vsphere, instance, count=8)

        # ...on hosts
        assertMOR(vsphere, instance, spec="host", count=2)
        tags = [
            "vcenter_server:vsphere_mock",
            "vsphere_folder:rootFolder",
            "vsphere_datacenter:datacenter1",
            "vsphere_compute:compute_resource1",
            "vsphere_cluster:compute_resource1",
            "vsphere_type:host",
        ]
        assertMOR(vsphere, instance, name="host2", spec="host", tags=tags)
        tags = [
            "vcenter_server:vsphere_mock",
            "vsphere_folder:rootFolder",
            "vsphere_folder:folder1",
            "vsphere_datacenter:datacenter2",
            "vsphere_compute:compute_resource2",
            "vsphere_cluster:compute_resource2",
            "vsphere_type:host",
        ]
        assertMOR(vsphere, instance, name="host3", spec="host", tags=tags)

        # ...on VMs
        assertMOR(vsphere, instance, spec="vm", count=1)
        tags = [
            "vcenter_server:vsphere_mock",
            "vsphere_folder:folder1",
            "vsphere_datacenter:datacenter2",
            "vsphere_compute:compute_resource2",
            "vsphere_cluster:compute_resource2",
            "vsphere_host:host3",
            "vsphere_type:vm",
        ]
        assertMOR(vsphere, instance, name="vm4", spec="vm", subset=True, tags=tags)


def test_use_guest_hostname(vsphere, instance):
    # Default value
    with mock.patch("datadog_checks.vsphere.VSphereCheck._get_all_objs") as mock_get_all_objs, mock.patch(
        "datadog_checks.vsphere.vsphere.vmodl"
    ):
        vsphere._cache_morlist_raw(instance)
        # Default value
        assert not mock_get_all_objs.call_args[1]["use_guest_hostname"]

        # use guest hostname
        instance["use_guest_hostname"] = True
        vsphere._cache_morlist_raw(instance)
        assert mock_get_all_objs.call_args[1]["use_guest_hostname"]

    with mock.patch("datadog_checks.vsphere.vsphere.vmodl"):

        # Discover hosts and virtual machines
        instance["use_guest_hostname"] = True
        vsphere._cache_morlist_raw(instance)
        assertMOR(vsphere, instance, spec="vm", count=3)
        # Fallback on VM name when guest hostname not available
        assertMOR(vsphere, instance, name="vm1", spec="vm", subset=True)
        assertMOR(vsphere, instance, name="vm2_guest", spec="vm", subset=True)
        assertMOR(vsphere, instance, name="vm4_guest", spec="vm", subset=True)


def test__process_mor_objects_queue(vsphere, instance):
    vsphere.log = MagicMock()
    vsphere._process_mor_objects_queue_async = MagicMock()
    vsphere._process_mor_objects_queue(instance)
    # Queue hasn't been initialized
    vsphere.log.debug.assert_called_once_with(
        "Objects queue is not initialized yet for instance %s, skipping processing", vsphere._instance_key(instance)
    )

    vsphere.batch_morlist_size = 1
    i_key = vsphere._instance_key(instance)
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        vsphere._cache_morlist_raw(instance)
        assert sum(vsphere.mor_objects_queue.size(i_key, res_type) for res_type in RESOURCE_TYPE_METRICS) == 11
        vsphere._process_mor_objects_queue(instance)
        # Object queue should be empty after processing
        assert sum(vsphere.mor_objects_queue.size(i_key, res_type) for res_type in RESOURCE_TYPE_METRICS) == 0
        assert vsphere._process_mor_objects_queue_async.call_count == 0  # realtime only
        for call_args in vsphere._process_mor_objects_queue_async.call_args_list:
            # query_specs parameter should be a list of size 1 since the batch size is 1
            assert len(call_args[0][1]) == 1

        instance["collect_realtime_only"] = False
        vsphere._cache_morlist_raw(instance)
        assert sum(vsphere.mor_objects_queue.size(i_key, res_type) for res_type in RESOURCE_TYPE_METRICS) == 11
        vsphere._process_mor_objects_queue(instance)
        # Object queue should be empty after processing
        assert sum(vsphere.mor_objects_queue.size(i_key, res_type) for res_type in RESOURCE_TYPE_METRICS) == 0
        assert vsphere._process_mor_objects_queue_async.call_count == 5  # 2 datacenters, 2 clusters, 1 datastore


def test_collect_realtime_only(vsphere, instance):
    """
    Test the collect_realtime_only parameter acts as expected
    """
    vsphere._process_mor_objects_queue_async = MagicMock()
    instance["collect_realtime_only"] = False
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        vsphere._cache_morlist_raw(instance)
        vsphere._process_mor_objects_queue(instance)
        # Called once to process the 2 datacenters, then 2 clusters, then the datastore
        assert vsphere._process_mor_objects_queue_async.call_count == 3

    instance["collect_realtime_only"] = True
    vsphere._process_mor_objects_queue_async.reset_mock()
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        vsphere._cache_morlist_raw(instance)
        vsphere._process_mor_objects_queue(instance)
        assert vsphere._process_mor_objects_queue_async.call_count == 0


def test__cache_metrics_metadata(vsphere, instance):
    vsphere.metadata_cache = MagicMock()
    vsphere._cache_metrics_metadata(instance)

    vsphere.metadata_cache.init_instance.assert_called_once_with(vsphere._instance_key(instance))
    vsphere.metadata_cache.set_metadata.assert_called_once()
    vsphere.metadata_cache.set_metric_ids.assert_called_once()


def test__cache_metrics_metadata_compatibility(vsphere, instance):
    server_instance = vsphere._get_server_instance(instance)
    i_key = vsphere._instance_key(instance)
    counter = MagicMock()
    counter.rollupType = "average"
    counter.key = 1
    vsphere.format_metric_name = MagicMock()

    # New way
    instance["collection_level"] = 3
    server_instance.content.perfManager.QueryPerfCounterByLevel.return_value = [counter]
    vsphere._cache_metrics_metadata(instance)

    server_instance.content.perfManager.QueryPerfCounterByLevel.assert_called_once_with(3)
    assert len(vsphere.metadata_cache._metric_ids[i_key]) == 1
    assert len(vsphere.metadata_cache._metadata[i_key]) == 1
    vsphere.format_metric_name.assert_called_once_with(counter)

    # Compatibility mode
    instance["all_metrics"] = False
    del instance["collection_level"]
    vsphere.format_metric_name.reset_mock()
    server_instance.content.perfManager.perfCounter = [counter]
    vsphere._cache_metrics_metadata(instance)

    assert not vsphere.metadata_cache._metric_ids[i_key]
    assert len(vsphere.metadata_cache._metadata[i_key]) == 1
    vsphere.format_metric_name.assert_called_once_with(counter, compatibility=True)


def test_in_compatibility_mode(vsphere, instance):
    vsphere.log = MagicMock()

    instance["collection_level"] = 2
    assert not vsphere.in_compatibility_mode(instance)

    instance["all_metrics"] = True
    assert not vsphere.in_compatibility_mode(instance)
    vsphere.log.warning.assert_not_called()

    assert not vsphere.in_compatibility_mode(instance, log_warning=True)
    vsphere.log.warning.assert_called_once()

    del instance["collection_level"]
    vsphere.log.reset_mock()
    assert vsphere.in_compatibility_mode(instance)
    vsphere.log.warning.assert_not_called()

    assert vsphere.in_compatibility_mode(instance, log_warning=True)
    vsphere.log.warning.assert_called_once()


def test_format_metric_name(vsphere):
    counter = MagicMock()
    counter.groupInfo.key = "group"
    counter.nameInfo.key = "name"
    counter.rollupType = "rollup"
    assert vsphere.format_metric_name(counter, compatibility=True) == "group.name"

    for rollup, short_rollup in SHORT_ROLLUP.items():
        counter.rollupType = rollup
        assert vsphere.format_metric_name(counter) == "group.name.{}".format(short_rollup)


def test_collect_metrics(vsphere, instance):
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        vsphere.batch_morlist_size = 1
        vsphere._collect_metrics_async = MagicMock()
        vsphere._cache_metrics_metadata(instance)
        vsphere._cache_morlist_raw(instance)
        vsphere._process_mor_objects_queue(instance)
        vsphere.collect_metrics(instance)
        assert vsphere._collect_metrics_async.call_count == 6  # One for each VM/host, datacenters are not collected
        for call_args in vsphere._collect_metrics_async.call_args_list:
            # query_specs parameter should be a list of size 1 since the batch size is 1
            assert len(call_args[0][1]) == 1


def test__collect_metrics_async_compatibility(vsphere, instance):
    server_instance = vsphere._get_server_instance(instance)
    server_instance.content.perfManager.QueryPerf.return_value = [MagicMock(value=[MagicMock()])]
    vsphere.mor_cache = MagicMock()
    vsphere.metadata_cache = MagicMock()
    vsphere.metadata_cache.get_metadata.return_value = {"name": "unknown"}
    vsphere.in_compatibility_mode = MagicMock()
    vsphere.log = MagicMock()

    vsphere.in_compatibility_mode.return_value = True
    vsphere._collect_metrics_async(instance, [])
    vsphere.log.debug.assert_called_with('Skipping unknown `%s` metric.', 'unknown')

    vsphere.log.reset_mock()
    vsphere.in_compatibility_mode.return_value = False
    vsphere._collect_metrics_async(instance, [])
    vsphere.log.debug.assert_not_called()


def test__collect_metrics_async_hostname(vsphere, instance, aggregator):
    server_instance = vsphere._get_server_instance(instance)
    result = MagicMock()
    result.value = [23.4]

    server_instance.content.perfManager.QueryPerf.return_value = [MagicMock(value=[result])]
    mor = {"hostname": "foo"}
    vsphere.mor_cache = MagicMock()
    vsphere.mor_cache.get_mor.return_value = mor
    vsphere.metadata_cache = MagicMock()
    vsphere.metadata_cache.get_metadata.return_value = {"name": "mymetric", "unit": "kb"}
    vsphere.in_compatibility_mode = MagicMock()
    vsphere.in_compatibility_mode.return_value = False

    vsphere._collect_metrics_async(instance, [])
    aggregator.assert_metric('vsphere.mymetric', value=23.4, hostname="foo")


def test_check(vsphere, instance):
    """
    Test the check() method
    """
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        with mock.patch.object(vsphere, 'set_external_tags') as set_external_tags:
            vsphere.check(instance)
            set_external_tags.assert_called_once()
            all_the_tags = dict(set_external_tags.call_args[0][0])

            assert all_the_tags['vm4'][SOURCE_TYPE] == [
                'vcenter_server:vsphere_mock',
                'vsphere_folder:rootFolder',
                'vsphere_folder:folder1',
                'vsphere_datacenter:datacenter2',
                'vsphere_cluster:compute_resource2',
                'vsphere_compute:compute_resource2',
                'vsphere_host:host3',
                'vsphere_host:host3',
                'vsphere_type:vm',
            ]
            assert all_the_tags['host1'][SOURCE_TYPE] == [
                'vcenter_server:vsphere_mock',
                'vsphere_folder:rootFolder',
                'vsphere_datacenter:datacenter1',
                'vsphere_cluster:compute_resource1',
                'vsphere_compute:compute_resource1',
                'vsphere_type:host',
            ]
            assert all_the_tags['host3'][SOURCE_TYPE] == [
                'vcenter_server:vsphere_mock',
                'vsphere_folder:rootFolder',
                'vsphere_folder:folder1',
                'vsphere_datacenter:datacenter2',
                'vsphere_cluster:compute_resource2',
                'vsphere_compute:compute_resource2',
                'vsphere_type:host',
            ]
            assert all_the_tags['vm2'][SOURCE_TYPE] == [
                'vcenter_server:vsphere_mock',
                'vsphere_folder:rootFolder',
                'vsphere_folder:folder1',
                'vsphere_datacenter:datacenter2',
                'vsphere_cluster:compute_resource2',
                'vsphere_compute:compute_resource2',
                'vsphere_host:host3',
                'vsphere_host:host3',
                'vsphere_type:vm',
            ]
            assert all_the_tags['vm1'][SOURCE_TYPE] == [
                'vcenter_server:vsphere_mock',
                'vsphere_folder:rootFolder',
                'vsphere_folder:folder1',
                'vsphere_datacenter:datacenter2',
                'vsphere_cluster:compute_resource2',
                'vsphere_compute:compute_resource2',
                'vsphere_host:host3',
                'vsphere_host:host3',
                'vsphere_type:vm',
            ]
            assert all_the_tags['host2'][SOURCE_TYPE] == [
                'vcenter_server:vsphere_mock',
                'vsphere_folder:rootFolder',
                'vsphere_datacenter:datacenter1',
                'vsphere_cluster:compute_resource1',
                'vsphere_compute:compute_resource1',
                'vsphere_type:host',
            ]


def test_service_check_ko(aggregator, instance):
    check = disable_thread_pool(VSphereCheck('disk', {}, {}, [instance]))

    with mock.patch('datadog_checks.vsphere.vsphere.connect.SmartConnect') as SmartConnect:
        # SmartConnect fails
        SmartConnect.side_effect = Exception()

        with pytest.raises(ConnectionError):
            check.check(instance)

        aggregator.assert_service_check(
            VSphereCheck.SERVICE_CHECK_NAME, status=VSphereCheck.CRITICAL, count=1, tags=SERVICE_CHECK_TAGS
        )

        aggregator.reset()

        # SmartConnect succeeds, CurrentTime fails
        server = MagicMock()
        server.CurrentTime.side_effect = Exception()
        SmartConnect.side_effect = None
        SmartConnect.return_value = server

        with pytest.raises(ConnectionError):
            check.check(instance)

        aggregator.assert_service_check(
            VSphereCheck.SERVICE_CHECK_NAME, status=VSphereCheck.CRITICAL, count=1, tags=SERVICE_CHECK_TAGS
        )


def test_service_check_ok(aggregator, instance):
    check = disable_thread_pool(VSphereCheck('disk', {}, {}, [instance]))
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        with mock.patch('datadog_checks.vsphere.vsphere.connect.SmartConnect') as SmartConnect:
            SmartConnect.return_value = get_mocked_server()
            check.check(instance)

            aggregator.assert_service_check(
                VSphereCheck.SERVICE_CHECK_NAME, status=VSphereCheck.OK, tags=SERVICE_CHECK_TAGS
            )


def test__instance_key(vsphere, instance):
    assert vsphere._instance_key(instance) == "vsphere_mock"
    del instance['name']
    with pytest.raises(BadConfigError):
        vsphere._instance_key(instance)


def test__should_cache(instance):
    now = time.time()
    # do not use fixtures for the check instance, some params are set at
    # __init__ time and we need to instantiate the check multiple times
    check = VSphereCheck('vsphere', {}, {}, [instance])
    i_key = check._instance_key(instance)

    # first run should always cache
    assert check._should_cache(instance, CacheConfig.Morlist)
    assert check._should_cache(instance, CacheConfig.Metadata)

    # explicitly set cache expiration times, don't use defaults so we also test
    # configuration is properly propagated
    init_config = {
        'refresh_morlist_interval': 2 * REFRESH_MORLIST_INTERVAL,
        'refresh_metrics_metadata_interval': 2 * REFRESH_METRICS_METADATA_INTERVAL,
    }
    check = VSphereCheck('vsphere', init_config, {}, [instance])
    # simulate previous runs, set the last execution time in the past
    check.cache_config.set_last(CacheConfig.Morlist, i_key, now - (2 * REFRESH_MORLIST_INTERVAL))
    check.cache_config.set_last(CacheConfig.Metadata, i_key, now - (2 * REFRESH_METRICS_METADATA_INTERVAL))

    with mock.patch("time.time", return_value=now):
        assert not check._should_cache(instance, CacheConfig.Morlist)
        assert not check._should_cache(instance, CacheConfig.Metadata)


def alarm_event(from_status='green', to_status='red', message='Some error'):
    now = datetime.utcnow()
    vm = MockedMOR(spec='VirtualMachine')
    dc = MockedMOR(spec="Datacenter")
    dc_arg = vim.event.DatacenterEventArgument(datacenter=dc, name='dc1')
    alarm = MockedMOR(spec="Alarm")
    alarm_arg = vim.event.AlarmEventArgument(alarm=alarm, name='alarm1')
    entity = vim.event.ManagedEntityEventArgument(entity=vm, name='vm1')
    event = vim.event.AlarmStatusChangedEvent(
        entity=entity, fullFormattedMessage=message, createdTime=now, to=to_status, datacenter=dc_arg, alarm=alarm_arg
    )
    setattr(event, 'from', from_status)  # noqa: B009
    return event


def migrated_event():
    now = datetime.utcnow()
    vm = MockedMOR(spec='VirtualMachine', name='vm1')
    vm_arg = vim.event.VmEventArgument(vm=vm)
    host = MockedMOR(spec='HostSystem')
    host_arg = vim.event.HostEventArgument(host=host, name='host1')
    host_dest = MockedMOR(spec='HostSystem')
    host_dest_arg = vim.event.HostEventArgument(host=host_dest, name='host2')
    dc = MockedMOR(spec='Datacenter')
    dc_arg = vim.event.DatacenterEventArgument(datacenter=dc, name='dc1')
    dc_dest = MockedMOR(spec='Datacenter')
    dc_dest_arg = vim.event.DatacenterEventArgument(datacenter=dc_dest, name='dc2')
    ds = MockedMOR(spec='Datastore')
    ds_arg = vim.event.DatastoreEventArgument(datastore=ds, name='ds1')
    ds_dest = MockedMOR(spec='Datastore')
    ds_dest_arg = vim.event.DatastoreEventArgument(datastore=ds_dest, name='ds2')
    event = vim.event.VmBeingHotMigratedEvent(
        vm=vm_arg,
        userName='John',
        fullFormattedMessage='Some error',
        createdTime=now,
        host=host_arg,
        destHost=host_dest_arg,
        datacenter=dc_arg,
        destDatacenter=dc_dest_arg,
        ds=ds_arg,
        destDatastore=ds_dest_arg,
    )
    return event


def test_events(aggregator, vsphere, instance):
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        server_instance = vsphere._get_server_instance(instance)
        server_instance.content.eventManager.QueryEvents.return_value = [alarm_event()]
        vsphere.event_config['vsphere_mock'] = {'collect_vcenter_alarms': True}
        vsphere.check(instance)
        aggregator.assert_event(
            "vCenter monitor status changed on this alarm, it was green and it's now red.", tags=['foo:bar']
        )


def test_events_tags(aggregator, vsphere, instance):
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        server_instance = vsphere._get_server_instance(instance)
        server_instance.content.eventManager.QueryEvents.return_value = [migrated_event()]
        vsphere.event_config['vsphere_mock'] = {'collect_vcenter_alarms': True}
        vsphere.check(instance)
        aggregator.assert_event(
            "John has launched a hot migration of this virtual machine",
            exact_match=False,
            tags=[
                'foo:bar',
                'vsphere_host:host1',
                'vsphere_host:host2',
                'vsphere_datacenter:dc1',
                'vsphere_datacenter:dc2',
            ],
        )

        server_instance = vsphere._get_server_instance(instance)
        server_instance.content.eventManager.QueryEvents.return_value = [alarm_event()]
        vsphere.check(instance)
        aggregator.assert_event(
            "vCenter monitor status changed on this alarm, it was green and it's now red.", tags=['foo:bar']
        )


def test_events_gray_handled(aggregator, vsphere, instance):
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        server_instance = vsphere._get_server_instance(instance)
        event = alarm_event(from_status='gray', message='Went from Gray to Red')
        server_instance.content.eventManager.QueryEvents.return_value = [event]
        vsphere.event_config['vsphere_mock'] = {'collect_vcenter_alarms': True}
        vsphere.check(instance)
        aggregator.assert_event(
            "vCenter monitor status changed on this alarm, it was gray and it's now red.", tags=['foo:bar']
        )

        event = alarm_event(from_status='yellow', to_status='gray', message='Went from Yellow to Gray')
        server_instance.content.eventManager.QueryEvents.return_value = [event]
        vsphere.check(instance)
        aggregator.assert_event(
            "vCenter monitor status changed on this alarm, it was yellow and it's now gray.",
            tags=['foo:bar'],
            alert_type='info',
        )


def test_events_gray_ignored(aggregator, vsphere, instance):
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        server_instance = vsphere._get_server_instance(instance)
        event = alarm_event(from_status='gray', to_status='green', message='Went from Gray to Green')
        server_instance.content.eventManager.QueryEvents.return_value = [event]
        vsphere.event_config['vsphere_mock'] = {'collect_vcenter_alarms': True}
        vsphere.check(instance)
        assert not aggregator.events
        event = alarm_event(from_status='green', to_status='gray', message='Went from Green to Gray')
        server_instance.content.eventManager.QueryEvents.return_value = [event]
        vsphere.check(instance)
        assert not aggregator.events
