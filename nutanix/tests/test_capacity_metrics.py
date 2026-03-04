# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""
Tests for VM, Host, and Cluster capacity/inventory metrics.

These metrics report allocated resources (CPU, memory) rather than usage stats.
"""

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


class TestVMCapacityMetrics:
    """Test VM CPU and memory allocation metrics."""

    def test_vm_cpu_sockets(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report number of CPU sockets allocated."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:vm',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-103-aws-us-east-1a',
            'ntnx_is_agent_vm:False',
            'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # VM "NTNX-10-0-0-165-PCVM-1767014640" has numSockets=6
        aggregator.assert_metric("nutanix.vm.cpu.sockets", value=6, tags=expected_tags)

    def test_vm_cpu_cores_per_socket(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report cores per socket."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:vm',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-103-aws-us-east-1a',
            'ntnx_is_agent_vm:False',
            'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # VM "NTNX-10-0-0-165-PCVM-1767014640" has numCoresPerSocket=1
        aggregator.assert_metric("nutanix.vm.cpu.cores_per_socket", value=1, tags=expected_tags)

    def test_vm_cpu_vcpus_allocated(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report total vCPUs allocated (sockets * cores_per_socket)."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:vm',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-103-aws-us-east-1a',
            'ntnx_is_agent_vm:False',
            'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # VM "NTNX-10-0-0-165-PCVM-1767014640": 6 sockets * 1 core = 6 vCPUs
        aggregator.assert_metric("nutanix.vm.cpu.vcpus_allocated", value=6, tags=expected_tags)

    def test_vm_cpu_threads_per_core(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report threads per core."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:vm',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-103-aws-us-east-1a',
            'ntnx_is_agent_vm:False',
            'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # VM "NTNX-10-0-0-165-PCVM-1767014640" has numThreadsPerCore=1
        aggregator.assert_metric("nutanix.vm.cpu.threads_per_core", value=1, tags=expected_tags)

    def test_vm_memory_allocated(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report memory allocated in bytes."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:vm',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-103-aws-us-east-1a',
            'ntnx_is_agent_vm:False',
            'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # VM "NTNX-10-0-0-165-PCVM-1767014640" has memorySizeBytes=30064771072
        aggregator.assert_metric("nutanix.vm.memory.allocated_bytes", value=30064771072, tags=expected_tags)


class TestHostCapacityMetrics:
    """Test Host CPU and memory capacity metrics."""

    def test_host_cpu_sockets(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report number of CPU sockets."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:host',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-103-aws-us-east-1a',
            'ntnx_host_type:HYPER_CONVERGED',
            'ntnx_hypervisor_name:AHV 10.3',
            'ntnx_hypervisor_type:AHV',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Host has numberOfCpuSockets=2
        aggregator.assert_metric(
            "nutanix.host.cpu.sockets", value=2, tags=expected_tags, hostname="10-0-0-103-aws-us-east-1a"
        )

    def test_host_cpu_cores(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report total CPU cores."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:host',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-103-aws-us-east-1a',
            'ntnx_host_type:HYPER_CONVERGED',
            'ntnx_hypervisor_name:AHV 10.3',
            'ntnx_hypervisor_type:AHV',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Host has numberOfCpuCores=24
        aggregator.assert_metric(
            "nutanix.host.cpu.cores", value=24, tags=expected_tags, hostname="10-0-0-103-aws-us-east-1a"
        )

    def test_host_cpu_threads(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report total CPU threads."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:host',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-103-aws-us-east-1a',
            'ntnx_host_type:HYPER_CONVERGED',
            'ntnx_hypervisor_name:AHV 10.3',
            'ntnx_hypervisor_type:AHV',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Host has numberOfCpuThreads=48
        aggregator.assert_metric(
            "nutanix.host.cpu.threads", value=48, tags=expected_tags, hostname="10-0-0-103-aws-us-east-1a"
        )

    def test_host_memory_bytes(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report total memory in bytes."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:host',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-103-aws-us-east-1a',
            'ntnx_host_type:HYPER_CONVERGED',
            'ntnx_hypervisor_name:AHV 10.3',
            'ntnx_hypervisor_type:AHV',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Host has memorySizeBytes=404834222080
        aggregator.assert_metric(
            "nutanix.host.memory.bytes", value=404834222080, tags=expected_tags, hostname="10-0-0-103-aws-us-east-1a"
        )


class TestClusterCapacityMetrics:
    """Test Cluster aggregated capacity metrics."""

    def test_cluster_cpu_total_cores(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total CPU cores (sum from all hosts)."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_cluster_name:datadog-nutanix-dev',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Cluster has 1 host with 24 cores
        aggregator.assert_metric("nutanix.cluster.cpu.total_cores", value=24, tags=expected_tags)

    def test_cluster_cpu_total_threads(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total CPU threads (sum from all hosts)."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_cluster_name:datadog-nutanix-dev',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Cluster has 1 host with 48 threads
        aggregator.assert_metric("nutanix.cluster.cpu.total_threads", value=48, tags=expected_tags)

    def test_cluster_memory_total_bytes(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total memory in bytes (sum from all hosts)."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_cluster_name:datadog-nutanix-dev',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Cluster has 1 host with 404834222080 bytes
        aggregator.assert_metric("nutanix.cluster.memory.total_bytes", value=404834222080, tags=expected_tags)

    def test_cluster_vcpus_allocated(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total vCPUs allocated to all VMs."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_cluster_name:datadog-nutanix-dev',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # NTNX-10-0-0-165-PCVM: 6, ubuntu-vm: 2, random-vm: 2 (OFF VM excluded by default)
        aggregator.assert_metric("nutanix.cluster.cpu.vcpus_allocated", value=10, tags=expected_tags)

    def test_cluster_memory_allocated_bytes(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total memory allocated to all VMs."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_cluster_name:datadog-nutanix-dev',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # NTNX-10-0-0-165-PCVM: 28GB, ubuntu-vm: 8GB, random-vm: 8GB (OFF VM excluded by default)
        aggregator.assert_metric("nutanix.cluster.memory.allocated_bytes", value=47244640256, tags=expected_tags)
