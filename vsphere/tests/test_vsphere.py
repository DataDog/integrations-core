# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals
import time

import pytest
import mock
from mock import MagicMock

from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.errors import BadConfigError, ConnectionError
from datadog_checks.vsphere.cache_config import CacheConfig
from datadog_checks.vsphere.common import SOURCE_TYPE
from datadog_checks.vsphere.vsphere import REFRESH_MORLIST_INTERVAL, REFRESH_METRICS_METADATA_INTERVAL
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
    assert len(check.morlist_raw) == 0
    assert len(check.morlist) == 0
    assert len(check.metrics_metadata) == 0
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


def test__cache_morlist_raw_atomic(vsphere, instance):
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
        vsphere._cache_morlist_raw_atomic(instance, tags, include_regexes, include_only_marked)

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


def test_check(vsphere, instance):
    """
    Test the check() method
    """
    with mock.patch('datadog_checks.vsphere.vsphere.vmodl'):
        with mock.patch('datadog_checks.vsphere.vsphere.set_external_tags') as set_external_tags:
            vsphere.check(instance)
            set_external_tags.assert_called_once()
            all_the_tags = set_external_tags.call_args[0][0]

            assert ('vm4', {SOURCE_TYPE: [
                                        'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                                        'vsphere_folder:folder1', 'vsphere_datacenter:datacenter2',
                                        'vsphere_cluster:compute_resource2', 'vsphere_compute:compute_resource2',
                                        'vsphere_host:host3', 'vsphere_host:host3', 'vsphere_type:vm'
                            ]}) in all_the_tags
            assert ('host1', {SOURCE_TYPE: [
                                        'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                                        'vsphere_datacenter:datacenter1', 'vsphere_cluster:compute_resource1',
                                        'vsphere_compute:compute_resource1', 'vsphere_type:host'
                              ]}) in all_the_tags
            assert ('host3', {SOURCE_TYPE: [
                                        'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                                        'vsphere_folder:folder1', 'vsphere_datacenter:datacenter2',
                                        'vsphere_cluster:compute_resource2', 'vsphere_compute:compute_resource2',
                                        'vsphere_type:host'
                              ]}) in all_the_tags
            assert ('vm2', {SOURCE_TYPE: [
                                        'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                                        'vsphere_folder:folder1', 'vsphere_datacenter:datacenter2',
                                        'vsphere_cluster:compute_resource2', 'vsphere_compute:compute_resource2',
                                        'vsphere_host:host3', 'vsphere_host:host3', 'vsphere_type:vm'
                            ]}) in all_the_tags
            assert ('vm1', {SOURCE_TYPE: [
                                        'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                                        'vsphere_folder:folder1', 'vsphere_datacenter:datacenter2',
                                        'vsphere_cluster:compute_resource2', 'vsphere_compute:compute_resource2',
                                        'vsphere_host:host3', 'vsphere_host:host3', 'vsphere_type:vm'
                            ]}) in all_the_tags
            assert ('host2', {SOURCE_TYPE: [
                                        'vcenter_server:vsphere_mock', 'vsphere_folder:rootFolder',
                                        'vsphere_datacenter:datacenter1', 'vsphere_cluster:compute_resource1',
                                        'vsphere_compute:compute_resource1', 'vsphere_type:host'
                             ]}) in all_the_tags


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
