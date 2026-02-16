# (C) Datadog, Inc. 2025-present
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
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
            'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
            'ntnx_host_name:10-0-0-9-aws-us-east-1a',
            'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
            'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
            'ntnx_vm_name:PC-OptionName-1',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # VM "PC-OptionName-1" has numSockets=6
        aggregator.assert_metric("nutanix.vm.cpu.sockets", value=6, tags=expected_tags)

    def test_vm_cpu_cores_per_socket(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report cores per socket."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:vm',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
            'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
            'ntnx_host_name:10-0-0-9-aws-us-east-1a',
            'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
            'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
            'ntnx_vm_name:PC-OptionName-1',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # VM "PC-OptionName-1" has numCoresPerSocket=1
        aggregator.assert_metric("nutanix.vm.cpu.cores_per_socket", value=1, tags=expected_tags)

    def test_vm_cpu_vcpus_allocated(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report total vCPUs allocated (sockets * cores_per_socket)."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:vm',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
            'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
            'ntnx_host_name:10-0-0-9-aws-us-east-1a',
            'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
            'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
            'ntnx_vm_name:PC-OptionName-1',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # VM "PC-OptionName-1": 6 sockets * 1 core = 6 vCPUs
        aggregator.assert_metric("nutanix.vm.cpu.vcpus_allocated", value=6, tags=expected_tags)

    def test_vm_cpu_threads_per_core(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report threads per core."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:vm',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
            'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
            'ntnx_host_name:10-0-0-9-aws-us-east-1a',
            'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
            'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
            'ntnx_vm_name:PC-OptionName-1',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # VM "PC-OptionName-1" has numThreadsPerCore=1
        aggregator.assert_metric("nutanix.vm.cpu.threads_per_core", value=1, tags=expected_tags)

    def test_vm_memory_allocated(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """VM should report memory allocated in bytes."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:vm',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
            'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
            'ntnx_host_name:10-0-0-9-aws-us-east-1a',
            'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
            'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
            'ntnx_vm_name:PC-OptionName-1',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # VM "PC-OptionName-1" has memorySizeBytes=30064771072
        aggregator.assert_metric("nutanix.vm.memory.allocated_bytes", value=30064771072, tags=expected_tags)


class TestHostCapacityMetrics:
    """Test Host CPU and memory capacity metrics."""

    def test_host_cpu_sockets(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report number of CPU sockets."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:host',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-9-aws-us-east-1a',
            'ntnx_host_type:HYPER_CONVERGED',
            'ntnx_hypervisor_name:AHV 10.0.1.4',
            'ntnx_hypervisor_type:AHV',
            'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Host has numberOfCpuSockets=2
        aggregator.assert_metric(
            "nutanix.host.cpu.sockets", value=2, tags=expected_tags, hostname="10-0-0-9-aws-us-east-1a"
        )

    def test_host_cpu_cores(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report total CPU cores."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:host',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-9-aws-us-east-1a',
            'ntnx_host_type:HYPER_CONVERGED',
            'ntnx_hypervisor_name:AHV 10.0.1.4',
            'ntnx_hypervisor_type:AHV',
            'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Host has numberOfCpuCores=24
        aggregator.assert_metric(
            "nutanix.host.cpu.cores", value=24, tags=expected_tags, hostname="10-0-0-9-aws-us-east-1a"
        )

    def test_host_cpu_threads(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report total CPU threads."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:host',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-9-aws-us-east-1a',
            'ntnx_host_type:HYPER_CONVERGED',
            'ntnx_hypervisor_name:AHV 10.0.1.4',
            'ntnx_hypervisor_type:AHV',
            'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Host has numberOfCpuThreads=48
        aggregator.assert_metric(
            "nutanix.host.cpu.threads", value=48, tags=expected_tags, hostname="10-0-0-9-aws-us-east-1a"
        )

    def test_host_memory_bytes(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Host should report total memory in bytes."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_type:host',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_host_name:10-0-0-9-aws-us-east-1a',
            'ntnx_host_type:HYPER_CONVERGED',
            'ntnx_hypervisor_name:AHV 10.0.1.4',
            'ntnx_hypervisor_type:AHV',
            'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Host has memorySizeBytes=404835270656
        aggregator.assert_metric(
            "nutanix.host.memory.bytes", value=404835270656, tags=expected_tags, hostname="10-0-0-9-aws-us-east-1a"
        )


class TestClusterCapacityMetrics:
    """Test Cluster aggregated capacity metrics."""

    def test_cluster_cpu_total_cores(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total CPU cores (sum from all hosts)."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
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
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
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
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # Cluster has 1 host with 404835270656 bytes
        aggregator.assert_metric("nutanix.cluster.memory.total_bytes", value=404835270656, tags=expected_tags)

    def test_cluster_vcpus_allocated(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total vCPUs allocated to all VMs."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # All VMs in cluster (fixture returns 3 VMs):
        # - PC-OptionName-1: 6 sockets * 1 core = 6 vCPUs
        # - dd-vm: 2 sockets * 1 core = 2 vCPUs
        # - datadog-agent-cloned: 1 socket * 1 core = 1 vCPU
        # Total: 9 vCPUs
        aggregator.assert_metric("nutanix.cluster.cpu.vcpus_allocated", value=9, tags=expected_tags)

    def test_cluster_memory_allocated_bytes(self, dd_run_check, aggregator, mock_instance, mock_http_get):
        """Cluster should report total memory allocated to all VMs."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        expected_tags = [
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'nutanix',
            'prism_central:10.0.0.197',
        ]

        # All VMs in cluster (fixture returns 3 VMs):
        # - PC-OptionName-1: 30064771072 bytes (~28GB)
        # - dd-vm: 8589934592 bytes (8GB)
        # - datadog-agent-cloned: 4294967296 bytes (4GB)
        # Total: 42949672960 bytes (~40GB)
        aggregator.assert_metric("nutanix.cluster.memory.allocated_bytes", value=42949672960, tags=expected_tags)
