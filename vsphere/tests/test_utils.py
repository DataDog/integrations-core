# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
from pytest import param
from pyVmomi import vim

from datadog_checks.vsphere.config import VSphereConfig
from datadog_checks.vsphere.utils import get_mapped_instance_tag, should_collect_per_instance_values


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
    'metric_name, resource_type, expect_match',
    [
        param('cpu.idle.sum', vim.VirtualMachine, True, id='found_1'),
        param('cpu.overlap.sum', vim.VirtualMachine, True, id='found_2'),
        param('cpu.usage.avg', vim.VirtualMachine, False, id='does_not_match'),
        param('cpu.overlap.sum', vim.ClusterComputeResource, False, id='wrong_resource_type'),
    ],
)
def test_should_collect_per_instance_values(metric_name, resource_type, expect_match):
    config = VSphereConfig(
        {
            'host': 'foo',
            'username': 'bar',
            'password': 'baz',
            'collect_per_instance_filters': {'vm': [r'cpu\..*\.sum']},
        },
        {},
        None,
    )

    assert expect_match == should_collect_per_instance_values(
        config.collect_per_instance_filters, metric_name, resource_type
    )
