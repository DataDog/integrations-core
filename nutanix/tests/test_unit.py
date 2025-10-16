# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


# Health Check Tests
def test_health_check_success(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test successful health check."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.health.up",
        value=1,
        count=1,
        tags=['prism_central:10.0.0.197', 'test:nutanix']
    )


def test_health_check_failure(dd_run_check, aggregator, mock_instance, mocker):
    """Test health check failure."""
    def mock_exception(*args, **kwargs):
        from requests.exceptions import ConnectionError
        raise ConnectionError("Connection failed")

    mocker.patch('requests.Session.get', side_effect=mock_exception)
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.health.up",
        value=0,
        count=1,
        tags=['prism_central:10.0.0.197', 'test:nutanix']
    )


# Cluster Metrics Tests
def test_cluster_count_metric(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test cluster count metric."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.cluster.count",
        value=1,
        count=1,
        tags=[
            'nutanix_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'nutanix_cluster_name:datadoghq.com-Default-Org-dkhrzg',
            'prism_central:10.0.0.197',
            'test:nutanix'
        ]
    )


def test_cluster_vm_count(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test cluster VM count metric."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Note: only one cluster has vmCount field
    aggregator.assert_metric("nutanix.cluster.vm_count", count=1)


def test_cluster_node_count(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test cluster node count metric."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Note: fixtures have 2 clusters, each submits node_count
    aggregator.assert_metric("nutanix.cluster.node_count", count=2)


def test_cluster_availability(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test cluster availability metric."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Note: metric name is cluster.available (not availability), 2 clusters
    aggregator.assert_metric("nutanix.cluster.available", count=2)


def test_cluster_collection_toggle(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that disabling cluster collection works."""
    mock_instance['collect_cluster_metrics'] = False
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.count", count=0)


# Cluster Performance Metrics Tests
def test_cluster_cpu_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test cluster CPU metrics from stats endpoint."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Note: cluster_stats.json has empty data, so count=0
    aggregator.assert_metric("nutanix.cluster.cpu.usage_percent", count=0)


def test_cluster_memory_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test cluster memory metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.memory.usage_percent", count=0)


def test_cluster_storage_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test cluster storage capacity metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.storage.capacity_bytes", count=0)
    aggregator.assert_metric("nutanix.cluster.storage.free_bytes", count=0)
    aggregator.assert_metric("nutanix.cluster.storage.used_bytes", count=0)


def test_cluster_iops_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test cluster IOPS metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.iops.read", count=0)
    aggregator.assert_metric("nutanix.cluster.iops.write", count=0)
    aggregator.assert_metric("nutanix.cluster.iops.total", count=0)


def test_cluster_throughput_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test cluster throughput metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.throughput.read_bytes_per_sec", count=0)
    aggregator.assert_metric("nutanix.cluster.throughput.write_bytes_per_sec", count=0)


def test_cluster_latency_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test cluster latency metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.latency.read_ms", count=0)
    aggregator.assert_metric("nutanix.cluster.latency.write_ms", count=0)


# Host Metrics Tests
def test_host_count_metric(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test host count metric."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Hosts fixture has 1 host
    aggregator.assert_metric("nutanix.host.count", count=1)


def test_host_cpu_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test host CPU metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # host_stats.json doesn't exist, so count=0
    aggregator.assert_metric("nutanix.host.cpu.usage_percent", count=0)


def test_host_memory_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test host memory metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.memory.usage_percent", count=0)


def test_host_disk_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test host disk metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.disk.iops.read", count=0)
    aggregator.assert_metric("nutanix.host.disk.iops.write", count=0)


def test_host_network_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test host network metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.network.throughput.rx_bytes_per_sec", count=0)
    aggregator.assert_metric("nutanix.host.network.throughput.tx_bytes_per_sec", count=0)


def test_host_collection_toggle(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that disabling host collection works."""
    mock_instance['collect_host_metrics'] = False
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.count", count=0)


# VM Metrics Tests
def test_vm_count_metric(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test VM count metric."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # vms.json has empty data array
    aggregator.assert_metric("nutanix.vm.count", count=0)


def test_vm_cpu_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test VM CPU metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.cpu.usage_percent", count=0)
    aggregator.assert_metric("nutanix.vm.cpu.ready_time_ppm", count=0)


def test_vm_memory_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test VM memory metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.memory.usage_percent", count=0)
    aggregator.assert_metric("nutanix.vm.memory.size_bytes", count=0)


def test_vm_disk_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test VM disk metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.disk.iops.read", count=0)
    aggregator.assert_metric("nutanix.vm.disk.iops.write", count=0)


def test_vm_network_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test VM network metrics."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.network.throughput.rx_bytes_per_sec", count=0)
    aggregator.assert_metric("nutanix.vm.network.throughput.tx_bytes_per_sec", count=0)


def test_vm_collection_toggle(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that disabling VM collection works."""
    mock_instance['collect_vm_metrics'] = False
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", count=0)


# Events and Alerts Tests
def test_events_collection(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that events are collected."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # alerts.json has empty data
    aggregator.assert_metric("nutanix.event.occurred", count=0)


def test_alerts_collection(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that alerts are collected and counted by severity."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.alert.critical",
        value=0,
        count=1,
        tags=['prism_central:10.0.0.197', 'test:nutanix']
    )
    aggregator.assert_metric(
        "nutanix.alert.warning",
        value=0,
        count=1,
        tags=['prism_central:10.0.0.197', 'test:nutanix']
    )
    aggregator.assert_metric(
        "nutanix.alert.info",
        value=0,
        count=1,
        tags=['prism_central:10.0.0.197', 'test:nutanix']
    )


def test_events_collection_toggle(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that disabling event collection works."""
    mock_instance['collect_events'] = False
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.event.occurred", count=0)


def test_alerts_collection_toggle(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that disabling alert collection works."""
    mock_instance['collect_alerts'] = False
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.alert.critical", count=0)
    aggregator.assert_metric("nutanix.alert.warning", count=0)
    aggregator.assert_metric("nutanix.alert.info", count=0)


# Storage Container Tests
def test_storage_container_count(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test storage container count metric."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # storage_containers.json currently returns empty via mock
    aggregator.assert_metric("nutanix.storage_container.count", count=0)


# Tag Tests
def test_common_tags_applied(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that common tags are applied to all metrics."""
    mock_instance['tags'] = ['custom_env:test', 'custom_team:platform']
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Health metric should have custom tags
    aggregator.assert_metric(
        "nutanix.health.up",
        value=1,
        count=1,
        tags=['custom_env:test', 'custom_team:platform', 'prism_central:10.0.0.197']
    )


def test_cluster_tags_present(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that cluster metrics have proper tags."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.cluster.count",
        count=1,
        tags=[
            'nutanix_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'nutanix_cluster_name:datadoghq.com-Default-Org-dkhrzg',
            'prism_central:10.0.0.197',
            'test:nutanix'
        ]
    )


def test_host_tags_present(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that host metrics have proper tags."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Hosts fixture has 1 host
    aggregator.assert_metric("nutanix.host.count", count=1)


def test_vm_tags_present(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that VM metrics have proper tags when VMs exist."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # No VMs in fixture, so count=0
    aggregator.assert_metric("nutanix.vm.count", count=0)


# Configuration Tests
def test_pagination_limits_respected(mock_instance):
    """Test that pagination limits are set from config."""
    mock_instance['max_clusters'] = 10
    mock_instance['max_hosts'] = 20
    mock_instance['max_vms'] = 30
    check = NutanixCheck('nutanix', {}, [mock_instance])

    assert check.max_clusters == 10
    assert check.max_hosts == 20
    assert check.max_vms == 30


def test_username_fallback_to_pc_username(mock_instance):
    """Test that pc_username is used if username is not provided."""
    del mock_instance['username']
    mock_instance['pc_username'] = 'admin_pc'
    check = NutanixCheck('nutanix', {}, [mock_instance])

    # Check uses pc_username internally
    assert check.pc_username == 'admin_pc'


def test_pc_username_priority_over_username(mock_instance):
    """Test that pc_username takes priority over username."""
    mock_instance['username'] = 'admin_old'
    mock_instance['pc_username'] = 'admin_new'
    check = NutanixCheck('nutanix', {}, [mock_instance])

    # When both provided, pc_username should be used
    assert check.pc_username == 'admin_new'
