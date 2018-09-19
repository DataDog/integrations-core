# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals
import time

import pytest
import mock
from mock import MagicMock
from pyVmomi import vim

from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.errors import BadConfigError, ConnectionError
from datadog_checks.vsphere.cache_config import CacheConfig
from datadog_checks.vsphere.common import SOURCE_TYPE
from datadog_checks.vsphere.vsphere import (
    REFRESH_MORLIST_INTERVAL, REFRESH_METRICS_METADATA_INTERVAL, RESOURCE_TYPE_METRICS, SHORT_ROLLUP
)
from .utils import assertMOR, MockedMOR
from .utils import disable_thread_pool, get_mocked_server

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
    assert check.pool_started is False
    assert len(check.server_instances) == 0
    assert check.cache_config.get_interval(CacheConfig.Morlist, i_key) == 42
    assert check.cache_config.get_interval(CacheConfig.Metadata, i_key) == -42
    assert check.clean_morlist_interval == 50
    assert len(check.event_config) == 1
    assert 'vsphere_mock' in check.event_config
    assert len(check.registry) == 0
    assert len(check.latest_event_query) == 0
    assert check.batch_collector_size == 0
    assert check.batch_morlist_size == 50


def test__is_excluded():
    """
     * Exclude hosts/vms not compliant with the user's `*_include` configuration.
     * Exclude "non-labeled" virtual machines when the user configuration instructs to.
    """
    # Sample(s)
    include_regexes = {
        'host_include': "f[o]+",
        'vm_include': "f[o]+",
    }

    # OK
    included_host = MockedMOR(spec="HostSystem", name="foo")
    included_vm = MockedMOR(spec="VirtualMachine", name="foo")

    assert VSphereCheck._is_excluded(included_host, {"name": included_host.name}, include_regexes, None) is False
    assert VSphereCheck._is_excluded(included_vm, {"name": included_vm.name}, include_regexes, None) is False

    # Not OK!
    excluded_host = MockedMOR(spec="HostSystem", name="bar")
    excluded_vm = MockedMOR(spec="VirtualMachine", name="bar")

    assert VSphereCheck._is_excluded(excluded_host, {"name": excluded_host.name}, include_regexes, None) is True
    assert VSphereCheck._is_excluded(excluded_vm, {"name": excluded_vm.name}, include_regexes, None) is True

    # Sample(s)
    include_regexes = None
    include_only_marked = True

    # OK
    included_vm = MockedMOR(spec="VirtualMachine", name="foo", label=True)
    assert VSphereCheck._is_excluded(included_vm, {"customValue": included_vm.customValue},
                                     include_regexes, include_only_marked) is False

    # Not OK
    included_vm = MockedMOR(spec="VirtualMachine", name="foo")
    assert VSphereCheck._is_excluded(included_vm, {"customValue": []}, include_regexes, include_only_marked) is True


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
    mocked_mors_attrs = {
        vm_no_parent: {"name": "vm_no_parent", "runtime.powerState": vim.VirtualMachinePowerState.poweredOn},
        vm_no_powerstate: {"name": "vm_no_powerstate"},
        vm_host_parent: {"parent": mocked_host, "runtime.powerState": vim.VirtualMachinePowerState.poweredOn},
        mocked_host: {"name": "mocked_host", "parent": None},
        mocked_datastore: {},
        mocked_datacenter: {"parent": MockedMOR(spec="Folder", name="unknown folder")}
    }
    with mock.patch("datadog_checks.vsphere.VSphereCheck._collect_mors_and_attributes", return_value=mocked_mors_attrs):
        obj_list = vsphere._get_all_objs(server_instance)
        assert len(obj_list[vim.VirtualMachine]) == 2
        assert {
            "mor_type": "vm",
            "mor": vm_no_parent,
            "hostname": "vm_no_parent",
            "tags": ["vsphere_host:unknown", "vsphere_type:vm"]
        } in obj_list[vim.VirtualMachine]
        assert {
            "mor_type": "vm",
            "mor": vm_host_parent,
            "hostname": "unknown",
            "tags": ["vsphere_host:mocked_host", "vsphere_host:unknown", "vsphere_type:vm"]
        } in obj_list[vim.VirtualMachine]
        assert len(obj_list[vim.HostSystem]) == 1
        assert {
            "mor_type": "host",
            "mor": mocked_host,
            "hostname": "mocked_host",
            "tags": ["vsphere_type:host"]
        } in obj_list[vim.HostSystem]
        assert len(obj_list[vim.Datastore]) == 1
        assert {
            "mor_type": "datastore",
            "mor": mocked_datastore,
            "hostname": None,
            "tags": ["vsphere_datastore:unknown", "vsphere_type:datastore"]
        } in obj_list[vim.Datastore]
        assert len(obj_list[vim.Datacenter]) == 1
        assert {
            "mor_type": "datacenter",
            "mor": mocked_datacenter,
            "hostname": None,
            "tags": ["vsphere_folder:unknown", "vsphere_type:datacenter"]
        } in obj_list[vim.Datacenter]


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
        log.error.assert_called_once_with("Unable to retrieve property prop for object obj: fault")
        assert len(mor_attrs) == 1


def test__cache_morlist_raw_async(vsphere, instance):
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
        tags = ["toto", "optional:tag1"]
        include_regexes = {
            'host_include': "host[2-9]",
            'vm_include': "vm[^2]",
        }
        include_only_marked = True
        instance["tags"] = ["optional:tag1"]

        # Discover hosts and virtual machines
        vsphere._cache_morlist_raw_async(instance, tags, include_regexes, include_only_marked)

        # Assertions: 1 labeled+monitored VM + 2 hosts + 2 datacenters.
        assertMOR(vsphere, instance, count=5)

        # ...on hosts
        assertMOR(vsphere, instance, spec="host", count=2)
        tags = [
            "toto", "vsphere_folder:rootFolder", "vsphere_datacenter:datacenter1",
            "vsphere_compute:compute_resource1", "vsphere_cluster:compute_resource1",
            "vsphere_type:host", "optional:tag1"
        ]
        assertMOR(vsphere, instance, name="host2", spec="host", tags=tags)
        tags = [
            "toto", "vsphere_folder:rootFolder", "vsphere_folder:folder1",
            "vsphere_datacenter:datacenter2", "vsphere_compute:compute_resource2",
            "vsphere_cluster:compute_resource2", "vsphere_type:host", "optional:tag1"
        ]
        assertMOR(vsphere, instance, name="host3", spec="host", tags=tags)

        # ...on VMs
        assertMOR(vsphere, instance, spec="vm", count=1)
        tags = [
            "toto", "vsphere_folder:folder1", "vsphere_datacenter:datacenter2",
            "vsphere_compute:compute_resource2", "vsphere_cluster:compute_resource2",
            "vsphere_host:host3", "vsphere_type:vm", "optional:tag1"
        ]
        assertMOR(vsphere, instance, name="vm4", spec="vm", subset=True, tags=tags)


def test__process_mor_objects_queue(vsphere, instance):
    vsphere.log = MagicMock()
    vsphere._process_mor_objects_queue_async = MagicMock()
    vsphere._process_mor_objects_queue(instance)
    # Queue hasn't been initialized
    vsphere.log.debug.assert_called_once_with(
        "Objects queue is not initialized yet for instance {}, skipping processing"
        .format(vsphere._instance_key(instance))
    )

    vsphere.batch_morlist_size = 1
    i_key = vsphere._instance_key(instance)
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        vsphere._cache_morlist_raw(instance)
        assert sum(vsphere.mor_objects_queue.size(i_key, resource_type) for resource_type in RESOURCE_TYPE_METRICS) == 8
        vsphere._process_mor_objects_queue(instance)
        # Object queue should be empty after processing
        assert sum(vsphere.mor_objects_queue.size(i_key, resource_type) for resource_type in RESOURCE_TYPE_METRICS) == 0
        assert vsphere._process_mor_objects_queue_async.call_count == 2  # Once for each datacenter
        for call_args in vsphere._process_mor_objects_queue_async.call_args_list:
            # query_specs parameter should be a list of size 1 since the batch size is 1
            assert len(call_args[0][1]) == 1


def test_collect_realtime_only(vsphere, instance):
    """
    Test the collect_realtime_only parameter acts as expected
    """
    vsphere._process_mor_objects_queue_async = MagicMock()
    instance["collect_realtime_only"] = False
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        vsphere._cache_morlist_raw(instance)
        vsphere._process_mor_objects_queue(instance)
        # Called once to process the 2 datacenters
        assert vsphere._process_mor_objects_queue_async.call_count == 1

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

    assert len(vsphere.metadata_cache._metric_ids[i_key]) == 0
    assert len(vsphere.metadata_cache._metadata[i_key]) == 1
    vsphere.format_metric_name.assert_called_once_with(counter, compatibility=True)


def test_in_compatibility_mode(vsphere, instance):
    vsphere.log = MagicMock()

    instance["collection_level"] = 2
    assert vsphere.in_compatibility_mode(instance) is False

    instance["all_metrics"] = True
    assert vsphere.in_compatibility_mode(instance) is False
    vsphere.log.warning.assert_not_called()

    assert vsphere.in_compatibility_mode(instance, log_warning=True) is False
    vsphere.log.warning.assert_called_once()

    del instance["collection_level"]
    vsphere.log.reset_mock()
    assert vsphere.in_compatibility_mode(instance) is True
    vsphere.log.warning.assert_not_called()

    assert vsphere.in_compatibility_mode(instance, log_warning=True) is True
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
    vsphere.log.debug.assert_called_with("Skipping unknown `unknown` metric.")

    vsphere.log.reset_mock()
    vsphere.in_compatibility_mode.return_value = False
    vsphere._collect_metrics_async(instance, [])
    vsphere.log.debug.assert_not_called()


def test_check(vsphere, instance):
    """
    Test the check() method
    """
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        with mock.patch('datadog_checks.vsphere.vsphere.set_external_tags') as set_external_tags:
            vsphere.check(instance)
            set_external_tags.assert_called_once()
            all_the_tags = set_external_tags.call_args[0][0]

            assert ('vm4', {
                SOURCE_TYPE: [
                    'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                    'vsphere_folder:folder1', 'vsphere_datacenter:datacenter2',
                    'vsphere_cluster:compute_resource2', 'vsphere_compute:compute_resource2',
                    'vsphere_host:host3', 'vsphere_host:host3', 'vsphere_type:vm'
                ]
            }) in all_the_tags
            assert ('host1', {
                SOURCE_TYPE: [
                    'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                    'vsphere_datacenter:datacenter1', 'vsphere_cluster:compute_resource1',
                    'vsphere_compute:compute_resource1', 'vsphere_type:host'
                ]
            }) in all_the_tags
            assert ('host3', {
                SOURCE_TYPE: [
                    'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                    'vsphere_folder:folder1', 'vsphere_datacenter:datacenter2',
                    'vsphere_cluster:compute_resource2', 'vsphere_compute:compute_resource2',
                    'vsphere_type:host'
                ]
            }) in all_the_tags
            assert ('vm2', {
                SOURCE_TYPE: [
                    'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                    'vsphere_folder:folder1', 'vsphere_datacenter:datacenter2',
                    'vsphere_cluster:compute_resource2', 'vsphere_compute:compute_resource2',
                    'vsphere_host:host3', 'vsphere_host:host3', 'vsphere_type:vm'
                ]
            }) in all_the_tags
            assert ('vm1', {
                SOURCE_TYPE: [
                    'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                    'vsphere_folder:folder1', 'vsphere_datacenter:datacenter2',
                    'vsphere_cluster:compute_resource2', 'vsphere_compute:compute_resource2',
                    'vsphere_host:host3', 'vsphere_host:host3', 'vsphere_type:vm'
                ]
            }) in all_the_tags
            assert ('host2', {
                SOURCE_TYPE: [
                    'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                    'vsphere_datacenter:datacenter1', 'vsphere_cluster:compute_resource1',
                    'vsphere_compute:compute_resource1', 'vsphere_type:host'
                ]
            }) in all_the_tags


def test_service_check_ko(aggregator, instance):
    check = disable_thread_pool(VSphereCheck('disk', {}, {}, [instance]))

    with mock.patch('datadog_checks.vsphere.vsphere.connect.SmartConnect') as SmartConnect:
        # SmartConnect fails
        SmartConnect.side_effect = Exception()

        with pytest.raises(ConnectionError):
            check.check(instance)

        aggregator.assert_service_check(
            VSphereCheck.SERVICE_CHECK_NAME,
            status=VSphereCheck.CRITICAL,
            count=1,
            tags=SERVICE_CHECK_TAGS
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
            VSphereCheck.SERVICE_CHECK_NAME,
            status=VSphereCheck.CRITICAL,
            count=1,
            tags=SERVICE_CHECK_TAGS
        )


def test_service_check_ok(aggregator, instance):
    check = disable_thread_pool(VSphereCheck('disk', {}, {}, [instance]))
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        with mock.patch('datadog_checks.vsphere.vsphere.connect.SmartConnect') as SmartConnect:
            SmartConnect.return_value = get_mocked_server()
            check.check(instance)

            aggregator.assert_service_check(
                VSphereCheck.SERVICE_CHECK_NAME,
                status=VSphereCheck.OK,
                tags=SERVICE_CHECK_TAGS
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
    assert check._should_cache(instance, CacheConfig.Morlist) is True
    assert check._should_cache(instance, CacheConfig.Metadata) is True

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
        assert check._should_cache(instance, CacheConfig.Morlist) is False
        assert check._should_cache(instance, CacheConfig.Metadata) is False
