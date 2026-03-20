# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""
Tests for VM, Host, and Cluster capacity/inventory metrics.

These metrics report allocated resources (CPU, memory) rather than usage stats.
"""

import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import CLUSTER_TAGS, HOST_NAME, HOST_TAGS, PCVM_TAGS, RANDOM_VM_TAGS, UBUNTU_VM_TAGS

pytestmark = [pytest.mark.unit]


class TestVMCapacityMetrics:
    """Test VM CPU and memory allocation metrics."""

    def test_vm_cpu_sockets(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report number of CPU sockets allocated."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.cpu.sockets", value=6, tags=PCVM_TAGS)
        aggregator.assert_metric("nutanix.vm.cpu.sockets", value=2, tags=UBUNTU_VM_TAGS)
        aggregator.assert_metric("nutanix.vm.cpu.sockets", value=2, tags=RANDOM_VM_TAGS)

    def test_vm_cpu_cores_per_socket(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report cores per socket."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.cpu.cores_per_socket", value=1, tags=PCVM_TAGS)
        aggregator.assert_metric("nutanix.vm.cpu.cores_per_socket", value=1, tags=UBUNTU_VM_TAGS)
        aggregator.assert_metric("nutanix.vm.cpu.cores_per_socket", value=1, tags=RANDOM_VM_TAGS)

    def test_vm_cpu_vcpus_allocated(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report total vCPUs allocated (sockets * cores_per_socket)."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.cpu.vcpus_allocated", value=6, tags=PCVM_TAGS)
        aggregator.assert_metric("nutanix.vm.cpu.vcpus_allocated", value=2, tags=UBUNTU_VM_TAGS)
        aggregator.assert_metric("nutanix.vm.cpu.vcpus_allocated", value=2, tags=RANDOM_VM_TAGS)

    def test_vm_cpu_threads_per_core(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report threads per core."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.cpu.threads_per_core", value=1, tags=PCVM_TAGS)
        aggregator.assert_metric("nutanix.vm.cpu.threads_per_core", value=1, tags=UBUNTU_VM_TAGS)
        aggregator.assert_metric("nutanix.vm.cpu.threads_per_core", value=1, tags=RANDOM_VM_TAGS)

    def test_vm_memory_allocated(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report memory allocated in bytes."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.memory.allocated_bytes", value=30064771072, tags=PCVM_TAGS)
        aggregator.assert_metric("nutanix.vm.memory.allocated_bytes", value=8589934592, tags=UBUNTU_VM_TAGS)
        aggregator.assert_metric("nutanix.vm.memory.allocated_bytes", value=8589934592, tags=RANDOM_VM_TAGS)


class TestHostCapacityMetrics:
    """Test Host CPU and memory capacity metrics."""

    def test_host_cpu_sockets(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report number of CPU sockets."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.host.cpu.sockets", value=2, tags=HOST_TAGS, hostname=HOST_NAME)

    def test_host_cpu_cores(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report total CPU cores."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.host.cpu.cores", value=24, tags=HOST_TAGS, hostname=HOST_NAME)

    def test_host_cpu_threads(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report total CPU threads."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.host.cpu.threads", value=48, tags=HOST_TAGS, hostname=HOST_NAME)

    def test_host_memory_bytes(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report total memory in bytes."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.host.memory.bytes", value=404834222080, tags=HOST_TAGS, hostname=HOST_NAME)


class TestClusterCapacityMetrics:
    """Test Cluster aggregated capacity metrics."""

    def test_cluster_cpu_total_cores(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total CPU cores (sum from all hosts)."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.cpu.total_cores", value=24, tags=CLUSTER_TAGS)

    def test_cluster_cpu_total_threads(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total CPU threads (sum from all hosts)."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.cpu.total_threads", value=48, tags=CLUSTER_TAGS)

    def test_cluster_memory_total_bytes(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total memory in bytes (sum from all hosts)."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.memory.total_bytes", value=404834222080, tags=CLUSTER_TAGS)

    def test_cluster_vcpus_allocated(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total vCPUs allocated to all VMs."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        # All VMs contribute: PCVM=6, ubuntu=2, random=2, OFF=2 (hostless VMs still accumulate)
        aggregator.assert_metric("nutanix.cluster.cpu.vcpus_allocated", value=12, tags=CLUSTER_TAGS)

    def test_cluster_memory_allocated_bytes(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total memory allocated to all VMs."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        # All VMs contribute: PCVM + ubuntu + random + OFF (hostless VMs still accumulate)
        aggregator.assert_metric("nutanix.cluster.memory.allocated_bytes", value=55834574848, tags=CLUSTER_TAGS)
