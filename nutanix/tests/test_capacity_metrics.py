# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""
Tests for VM, Host, and Cluster capacity/inventory metrics.

These metrics report allocated resources (CPU, memory) rather than usage stats.
"""

import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import (
    CLUSTER_TAGS,
    HOST_NAME,
    HOST_TAGS,
    PCVM_TAGS,
    RANDOM_VM_TAGS,
    SECOND_CLUSTER_TAGS,
    UBUNTU_VM_TAGS,
)

pytestmark = [pytest.mark.unit]


def test_vm_capacity_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.cpu.sockets", value=6, tags=PCVM_TAGS)
    aggregator.assert_metric("nutanix.vm.cpu.sockets", value=2, tags=UBUNTU_VM_TAGS)
    aggregator.assert_metric("nutanix.vm.cpu.sockets", value=2, tags=RANDOM_VM_TAGS)

    aggregator.assert_metric("nutanix.vm.cpu.cores_per_socket", value=1, tags=PCVM_TAGS)
    aggregator.assert_metric("nutanix.vm.cpu.cores_per_socket", value=1, tags=UBUNTU_VM_TAGS)
    aggregator.assert_metric("nutanix.vm.cpu.cores_per_socket", value=1, tags=RANDOM_VM_TAGS)

    aggregator.assert_metric("nutanix.vm.cpu.vcpus_allocated", value=6, tags=PCVM_TAGS)
    aggregator.assert_metric("nutanix.vm.cpu.vcpus_allocated", value=2, tags=UBUNTU_VM_TAGS)
    aggregator.assert_metric("nutanix.vm.cpu.vcpus_allocated", value=2, tags=RANDOM_VM_TAGS)

    aggregator.assert_metric("nutanix.vm.cpu.threads_per_core", value=1, tags=PCVM_TAGS)
    aggregator.assert_metric("nutanix.vm.cpu.threads_per_core", value=1, tags=UBUNTU_VM_TAGS)
    aggregator.assert_metric("nutanix.vm.cpu.threads_per_core", value=1, tags=RANDOM_VM_TAGS)

    aggregator.assert_metric("nutanix.vm.memory.allocated_bytes", value=30064771072, tags=PCVM_TAGS)
    aggregator.assert_metric("nutanix.vm.memory.allocated_bytes", value=8589934592, tags=UBUNTU_VM_TAGS)
    aggregator.assert_metric("nutanix.vm.memory.allocated_bytes", value=8589934592, tags=RANDOM_VM_TAGS)


def test_host_capacity_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.cpu.sockets", value=2, tags=HOST_TAGS, hostname=HOST_NAME)
    aggregator.assert_metric("nutanix.host.cpu.cores", value=24, tags=HOST_TAGS, hostname=HOST_NAME)
    aggregator.assert_metric("nutanix.host.cpu.threads", value=48, tags=HOST_TAGS, hostname=HOST_NAME)
    aggregator.assert_metric("nutanix.host.memory.bytes", value=404834222080, tags=HOST_TAGS, hostname=HOST_NAME)


def test_cluster_capacity_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.cpu.total_cores", value=24, tags=CLUSTER_TAGS)
    aggregator.assert_metric("nutanix.cluster.cpu.total_threads", value=48, tags=CLUSTER_TAGS)
    aggregator.assert_metric("nutanix.cluster.memory.total_bytes", value=404834222080, tags=CLUSTER_TAGS)
    # PCVM=6, ubuntu=2, random=2, OFF=2 (filtered VM with host still accumulates capacity)
    aggregator.assert_metric("nutanix.cluster.cpu.vcpus_allocated", value=12, tags=CLUSTER_TAGS)
    # PCVM + ubuntu + random + OFF (filtered VM with host still accumulates capacity)
    aggregator.assert_metric("nutanix.cluster.memory.allocated_bytes", value=55834574848, tags=CLUSTER_TAGS)


def test_hostless_vcpus_not_overcounted_across_clusters(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Each cluster should only count hostless VMs that belong to it."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # second-nutanix-cluster: vm-on-second-cluster(8 vcpus) + hostless-vm-second-cluster(4 vcpus) = 12
    aggregator.assert_metric("nutanix.cluster.cpu.vcpus_allocated", value=12, tags=SECOND_CLUSTER_TAGS)

    # datadog-nutanix-dev: PCVM(6) + ubuntu(2) + random(2) + OFF with host(2) = 12
    aggregator.assert_metric("nutanix.cluster.cpu.vcpus_allocated", value=12, tags=CLUSTER_TAGS)


@pytest.mark.parametrize("batch_vm_collection", [True, False])
def test_exclude_filtered_resources_from_cluster_capacity(
    dd_run_check, aggregator, mock_instance, mock_http_get, batch_vm_collection
):
    mock_instance["batch_vm_collection"] = batch_vm_collection
    mock_instance["exclude_filtered_resources_from_cluster_capacity"] = True
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # cluster1: only 3 ON VMs contribute (PCVM=6, ubuntu=2, random=2 = 10 vcpus)
    aggregator.assert_metric("nutanix.cluster.cpu.vcpus_allocated", value=10, tags=CLUSTER_TAGS)
    # PCVM(30064771072) + ubuntu(8589934592) + random(8589934592) = 47244640256
    aggregator.assert_metric("nutanix.cluster.memory.allocated_bytes", value=47244640256, tags=CLUSTER_TAGS)
    # cluster2: only vm-on-second-cluster (8 vcpus, 17179869184 bytes) contributes
    aggregator.assert_metric("nutanix.cluster.cpu.vcpus_allocated", value=8, tags=SECOND_CLUSTER_TAGS)
    aggregator.assert_metric("nutanix.cluster.memory.allocated_bytes", value=17179869184, tags=SECOND_CLUSTER_TAGS)


def test_default_includes_filtered_resources_in_cluster_capacity(
    dd_run_check, aggregator, mock_instance, mock_http_get
):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # cluster1: all 4 VMs contribute (PCVM=6, ubuntu=2, random=2, OFF=2 = 12 vcpus)
    aggregator.assert_metric("nutanix.cluster.cpu.vcpus_allocated", value=12, tags=CLUSTER_TAGS)
    # cluster2: both VMs contribute (on-host=8, hostless=4 = 12 vcpus)
    aggregator.assert_metric("nutanix.cluster.cpu.vcpus_allocated", value=12, tags=SECOND_CLUSTER_TAGS)


def test_hostless_memory_not_overcounted_across_clusters(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Each cluster should only count hostless VM memory that belongs to it."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # second-nutanix-cluster: 17179869184 + 4294967296 = 21474836480
    aggregator.assert_metric("nutanix.cluster.memory.allocated_bytes", value=21474836480, tags=SECOND_CLUSTER_TAGS)

    # datadog-nutanix-dev: 30064771072 + 8589934592 + 8589934592 + 8589934592 = 55834574848
    aggregator.assert_metric("nutanix.cluster.memory.allocated_bytes", value=55834574848, tags=CLUSTER_TAGS)
