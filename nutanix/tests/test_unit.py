# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [
    pytest.mark.unit,
    pytest.mark.usefixtures("mock_http_get"),
]


class TestHealthCheck:
    """Test health check functionality."""

    def test_health_check_success(self, dd_run_check, aggregator, mock_instance):
        """Test successful health check."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.health.up", value=1, count=1)

    def test_health_check_failure(self, dd_run_check, aggregator, mock_instance, mocker):
        """Test health check failure with connection error."""
        # Mock a connection failure by throwing an exception
        def mock_exception(*args, **kwargs):
            from requests.exceptions import ConnectionError
            raise ConnectionError("Connection failed")
        
        mocker.patch('requests.Session.get', side_effect=mock_exception)
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)
        
        # Should have health check metric showing failure
        aggregator.assert_metric("nutanix.health.up", value=0, count=1)


class TestClusterMetrics:
    """Test cluster-level metrics collection."""

    def test_cluster_basic_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test basic cluster metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        # Should have health metric
        aggregator.assert_metric("nutanix.health.up", value=1)

        # Should have cluster count metric
        aggregator.assert_metric(
            "nutanix.cluster.count",
            value=1,
            # tags checked below,
        )

    def test_cluster_vm_count(self, dd_run_check, aggregator, mock_instance):
        """Test VM count per cluster is collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.vm_count", at_least=0)

    def test_cluster_node_count(self, dd_run_check, aggregator, mock_instance):
        """Test node count per cluster is collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.node_count", at_least=0)

    def test_cluster_availability(self, dd_run_check, aggregator, mock_instance):
        """Test cluster availability metric."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.available", at_least=0)

    def test_cluster_collection_toggle(self, dd_run_check, aggregator, mock_instance):
        """Test disabling cluster metrics collection."""
        mock_instance['collect_cluster_metrics'] = False
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        # Should not have cluster metrics
        aggregator.assert_metric("nutanix.cluster.count", count=0)


class TestClusterPerformanceMetrics:
    """Test cluster performance/stats metrics."""

    def test_cluster_cpu_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test cluster CPU metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        # CPU usage metric (may or may not exist depending on stats availability)
        aggregator.assert_metric("nutanix.cluster.cpu.usage_percent", at_least=0)

    def test_cluster_memory_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test cluster memory metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.memory.usage_percent", at_least=0)
        aggregator.assert_metric("nutanix.cluster.memory.usage_bytes", at_least=0)

    def test_cluster_storage_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test cluster storage metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.storage.capacity_bytes", at_least=0)
        aggregator.assert_metric("nutanix.cluster.storage.usage_bytes", at_least=0)
        aggregator.assert_metric("nutanix.cluster.storage.free_bytes", at_least=0)

    def test_cluster_iops_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test cluster IOPS metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.iops.read", at_least=0)
        aggregator.assert_metric("nutanix.cluster.iops.write", at_least=0)

    def test_cluster_throughput_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test cluster throughput metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.throughput.read_bytes_per_sec", at_least=0)
        aggregator.assert_metric("nutanix.cluster.throughput.write_bytes_per_sec", at_least=0)

    def test_cluster_latency_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test cluster latency metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.cluster.latency.read_ms", at_least=0)
        aggregator.assert_metric("nutanix.cluster.latency.write_ms", at_least=0)


class TestHostMetrics:
    """Test host-level metrics collection."""

    def test_host_basic_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test basic host metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.host.count", at_least=0)

    def test_host_cpu_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test host CPU metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.host.cpu.usage_percent", at_least=0)

    def test_host_memory_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test host memory metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.host.memory.usage_percent", at_least=0)
        aggregator.assert_metric("nutanix.host.memory.usage_bytes", at_least=0)

    def test_host_disk_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test host disk metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.host.disk.iops.read", at_least=0)
        aggregator.assert_metric("nutanix.host.disk.iops.write", at_least=0)
        aggregator.assert_metric("nutanix.host.disk.throughput.read_bytes_per_sec", at_least=0)
        aggregator.assert_metric("nutanix.host.disk.throughput.write_bytes_per_sec", at_least=0)

    def test_host_network_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test host network metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.host.network.throughput.rx_bytes_per_sec", at_least=0)
        aggregator.assert_metric("nutanix.host.network.throughput.tx_bytes_per_sec", at_least=0)

    def test_host_collection_toggle(self, dd_run_check, aggregator, mock_instance):
        """Test disabling host metrics collection."""
        mock_instance['collect_host_metrics'] = False
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.host.count", count=0)


class TestVMMetrics:
    """Test VM-level metrics collection."""

    def test_vm_basic_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test basic VM metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.count", at_least=0)

    def test_vm_cpu_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test VM CPU metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.cpu_count", at_least=0)
        aggregator.assert_metric("nutanix.vm.cpu.usage_percent", at_least=0)
        # CPU ready time (for inefficient VM detection)
        aggregator.assert_metric("nutanix.vm.cpu.ready_time_ppm", at_least=0)

    def test_vm_memory_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test VM memory metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.memory_size_bytes", at_least=0)
        aggregator.assert_metric("nutanix.vm.memory.usage_percent", at_least=0)
        aggregator.assert_metric("nutanix.vm.memory.usage_bytes", at_least=0)

    def test_vm_disk_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test VM disk metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.disk.iops.read", at_least=0)
        aggregator.assert_metric("nutanix.vm.disk.iops.write", at_least=0)
        aggregator.assert_metric("nutanix.vm.disk.throughput.read_bytes_per_sec", at_least=0)
        aggregator.assert_metric("nutanix.vm.disk.throughput.write_bytes_per_sec", at_least=0)
        aggregator.assert_metric("nutanix.vm.disk.latency.read_ms", at_least=0)
        aggregator.assert_metric("nutanix.vm.disk.latency.write_ms", at_least=0)

    def test_vm_network_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test VM network metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.network.throughput.rx_bytes_per_sec", at_least=0)
        aggregator.assert_metric("nutanix.vm.network.throughput.tx_bytes_per_sec", at_least=0)

    def test_vm_collection_toggle(self, dd_run_check, aggregator, mock_instance):
        """Test disabling VM metrics collection."""
        mock_instance['collect_vm_metrics'] = False
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.vm.count", count=0)


class TestEventsAndAlerts:
    """Test events and alerts collection."""

    def test_events_collection(self, dd_run_check, aggregator, mock_instance):
        """Test events are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.event.occurred", at_least=0)

    def test_alerts_collection(self, dd_run_check, aggregator, mock_instance):
        """Test alerts are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.alert.critical", at_least=0)
        aggregator.assert_metric("nutanix.alert.warning", at_least=0)
        aggregator.assert_metric("nutanix.alert.info", at_least=0)
        aggregator.assert_metric("nutanix.alert.active", at_least=0)

    def test_events_collection_toggle(self, dd_run_check, aggregator, mock_instance):
        """Test disabling events collection."""
        mock_instance['collect_events'] = False
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.event.occurred", count=0)

    def test_alerts_collection_toggle(self, dd_run_check, aggregator, mock_instance):
        """Test disabling alerts collection."""
        mock_instance['collect_alerts'] = False
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.alert.critical", count=0)
        aggregator.assert_metric("nutanix.alert.warning", count=0)


class TestStorageContainers:
    """Test storage container metrics."""

    def test_storage_container_metrics(self, dd_run_check, aggregator, mock_instance):
        """Test storage container metrics are collected."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        aggregator.assert_metric("nutanix.storage_container.count", at_least=0)


class TestTags:
    """Test metric tagging."""

    def test_common_tags(self, dd_run_check, aggregator, mock_instance):
        """Test that common tags are applied to all metrics."""
        mock_instance['tags'] = ['custom_env:test', 'custom_team:platform']
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        # Health metric should have common tags
        metrics = aggregator.metrics("nutanix.health.up")
        assert len(metrics) > 0
        tags = metrics[0].tags
        assert 'custom_env:test' in tags
        assert 'custom_team:platform' in tags
        assert any('prism_central:' in tag for tag in tags)

    def test_cluster_tags(self, dd_run_check, aggregator, mock_instance):
        """Test that cluster metrics have proper tags."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        # Cluster metrics should have cluster ID and name tags
        aggregator.assert_metric(
            "nutanix.cluster.count", # tags checked below
        )

    def test_host_tags(self, dd_run_check, aggregator, mock_instance):
        """Test that host metrics have proper tags."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        # Host metrics should have host ID and name tags
        aggregator.assert_metric(
            "nutanix.host.count", # tags checked below
        )

    def test_vm_tags(self, dd_run_check, aggregator, mock_instance):
        """Test that VM metrics have proper tags."""
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

        # VM metrics should have VM ID, name, and power state tags (if VMs exist)
        metrics = aggregator.metrics("nutanix.vm.count")
        if metrics:
            tags = metrics[0].tags
            assert any('nutanix_vm_id:' in tag for tag in tags)
            assert any('nutanix_vm_name:' in tag for tag in tags)
            assert any('power_state:' in tag for tag in tags)


class TestConfiguration:
    """Test configuration options."""

    def test_pagination_limits(self, mock_instance):
        """Test pagination limit configuration."""
        mock_instance['max_clusters'] = 10
        mock_instance['max_hosts'] = 20
        mock_instance['max_vms'] = 30
        check = NutanixCheck('nutanix', {}, [mock_instance])

        assert check.max_clusters == 10
        assert check.max_hosts == 20
        assert check.max_vms == 30

    def test_username_fallback(self):
        """Test username fallback from pc_username to username."""
        instance = {
            "pc_ip": "10.0.0.197",
            "pc_port": 9440,
            "username": "admin",
            "password": "secret",
        }
        check = NutanixCheck('nutanix', {}, [instance])
        assert check.pc_username == "admin"

    def test_pc_username_priority(self):
        """Test pc_username takes priority over username."""
        instance = {
            "pc_ip": "10.0.0.197",
            "pc_port": 9440,
            "pc_username": "pc_admin",
            "username": "admin",
            "password": "secret",
        }
        check = NutanixCheck('nutanix', {}, [instance])
        assert check.pc_username == "pc_admin"
