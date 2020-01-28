# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
from pyVmomi import vim

from datadog_checks.vsphere.utils import get_mapped_instance_tag, is_metric_available_per_instance


@pytest.mark.parametrize(
    'metric_name, expected_tag_key',
    [
        ('cpu.coreUtilization.avg', 'cpu_core'),
        ('datastore.datastoreIops.avg', 'vmfs_uuid'),
        ('disk.busResets.sum', 'device_path'),
        ('net.broadcastRx.sum', 'nic'),
        ('storageAdapter.commandsAveraged.avg', 'storage_adapter'),
        ('storagePath.commandsAveraged.avg', 'storage_path'),
        ('sys.resourceCpuAct1.latest', 'resource_path'),
        ('virtualDisk.largeSeeks.latest', 'disk'),
        ('foo.bar', 'instance'),
    ],
)
def test_get_mapped_instance_tag(metric_name, expected_tag_key):
    assert expected_tag_key == get_mapped_instance_tag(metric_name)


@pytest.mark.parametrize(
    'metric_name, resource_type, is_available_per_inst',
    [
        ('cpu.idle.sum', vim.VirtualMachine, True),
        ('cpu.latency.avg', vim.VirtualMachine, False),
        ('cpu.coreUtilization.avg', vim.HostSystem, True),
        ('cpu.costop.sum', vim.HostSystem, False),
        ('vmop.numChangeDS.latest', vim.Datacenter, False),
        ('datastore.busResets.sum', vim.Datastore, True),
        ('datastore.numberReadAveraged.avg', vim.Datastore, False),
        ('cpu.usage.avg', vim.ClusterComputeResource, True),
        ('cpu.usagemhz.avg', vim.ClusterComputeResource, False),
        ('cpu.usagemhz.avg', 'invalid resource type', False),
        ('unknown.metric.name', vim.ClusterComputeResource, False),
    ],
)
def test_is_metric_available_per_instance(metric_name, resource_type, is_available_per_inst):
    assert is_available_per_inst == is_metric_available_per_instance(metric_name, resource_type)
