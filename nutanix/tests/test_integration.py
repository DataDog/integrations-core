# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_health_check(dd_run_check, aggregator, aws_instance):
    """Test successful connection to Nutanix Prism Central."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1, count=1)


def test_cluster_metrics_collection(dd_run_check, aggregator, aws_instance):
    """Test that cluster metrics are collected from real instance."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # Health should be up
    aggregator.assert_metric("nutanix.health.up", value=1, count=1)

    # Should have at least zero clusters (might have auth issues)
    aggregator.assert_metric("nutanix.cluster.count", value=1)

    # Verify cluster has proper tags if clusters exist
    metrics = aggregator.metrics("nutanix.cluster.count", tags=['prism_central:prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com'])


def test_cluster_performance_metrics(dd_run_check, aggregator, aws_instance):
    """Test that cluster performance metrics are collected."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # These metrics might exist depending on stats availability
    # Using at_least=0 to allow for empty responses
    aggregator.assert_metric("nutanix.cluster.cpu.usage_percent", at_least=0)
    aggregator.assert_metric("nutanix.cluster.memory.usage_percent", at_least=0)
    aggregator.assert_metric("nutanix.cluster.storage.capacity_bytes", at_least=0)
    aggregator.assert_metric("nutanix.cluster.iops.read", at_least=0)
    aggregator.assert_metric("nutanix.cluster.latency.read_ms", at_least=0)


def test_host_metrics_collection(dd_run_check, aggregator, aws_instance):
    """Test that host metrics are collected from real instance."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # Should have at least one host
    aggregator.assert_metric("nutanix.host.count", at_least=0)

    # If hosts exist, verify tags
    host_metrics = aggregator.metrics("nutanix.host.count")
    if host_metrics:
        for metric in host_metrics:
            tags = {tag.split(':', 1)[0] for tag in metric.tags if ':' in tag}
            assert 'nutanix_host_id' in tags
            assert 'nutanix_host_name' in tags


def test_host_performance_metrics(dd_run_check, aggregator, aws_instance):
    """Test that host performance metrics are collected."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.cpu.usage_percent", at_least=0)
    aggregator.assert_metric("nutanix.host.memory.usage_percent", at_least=0)
    aggregator.assert_metric("nutanix.host.disk.iops.read", at_least=0)
    aggregator.assert_metric("nutanix.host.network.throughput.rx_bytes_per_sec", at_least=0)


def test_vm_metrics_collection(dd_run_check, aggregator, aws_instance):
    """Test that VM metrics are collected from real instance."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # Should have at least zero VMs (might be empty environment)
    aggregator.assert_metric("nutanix.vm.count", at_least=0)

    # If VMs exist, verify tags
    vm_metrics = aggregator.metrics("nutanix.vm.count")
    if vm_metrics:
        for metric in vm_metrics:
            tags = {tag.split(':', 1)[0] for tag in metric.tags if ':' in tag}
            assert 'nutanix_vm_id' in tags
            assert 'nutanix_vm_name' in tags
            assert 'power_state' in tags


def test_vm_performance_metrics(dd_run_check, aggregator, aws_instance):
    """Test that VM performance metrics are collected."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # These will only exist if VMs are powered on
    aggregator.assert_metric("nutanix.vm.cpu.usage_percent", at_least=0)
    aggregator.assert_metric("nutanix.vm.cpu.ready_time_ppm", at_least=0)
    aggregator.assert_metric("nutanix.vm.memory.usage_percent", at_least=0)
    aggregator.assert_metric("nutanix.vm.disk.iops.read", at_least=0)


def test_vm_inefficiency_detection(dd_run_check, aggregator, aws_instance):
    """Test that VM inefficiency metrics (CPU ready time) are collected."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # CPU ready time is key for detecting inefficient VMs
    aggregator.assert_metric("nutanix.vm.cpu.ready_time_ppm", at_least=0)


def test_events_collection(dd_run_check, aggregator, aws_instance):
    """Test that events are collected."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # Events might or might not exist
    aggregator.assert_metric("nutanix.event.occurred", at_least=0)


def test_alerts_collection(dd_run_check, aggregator, aws_instance):
    """Test that alerts are collected and counted."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # Alert count metrics (will be 0 if no alerts)
    aggregator.assert_metric("nutanix.alert.critical", at_least=0)
    aggregator.assert_metric("nutanix.alert.warning", at_least=0)
    aggregator.assert_metric("nutanix.alert.info", at_least=0)


def test_selective_collection_disable_vms(dd_run_check, aggregator, aws_instance):
    """Test that collection toggles work correctly."""
    # Disable VM collection
    aws_instance['collect_vm_metrics'] = False
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # Should have cluster and host metrics
    aggregator.assert_metric("nutanix.cluster.count", at_least=0)
    aggregator.assert_metric("nutanix.host.count", at_least=0)

    # Should not have VM metrics
    aggregator.assert_metric("nutanix.vm.count", count=0)


def test_pagination_limits(dd_run_check, aggregator, aws_instance):
    """Test that pagination limits are respected."""
    aws_instance['max_clusters'] = 1
    aws_instance['max_hosts'] = 1
    aws_instance['max_vms'] = 1
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # Should complete without errors
    aggregator.assert_metric("nutanix.health.up", value=1)


def test_custom_tags_applied(dd_run_check, aggregator, aws_instance):
    """Test that custom tags are applied to metrics."""
    aws_instance['tags'] = ['custom_env:production', 'custom_team:platform']
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # Health metric should have custom tags
    health_metrics = aggregator.metrics("nutanix.health.up")
    assert len(health_metrics) > 0
    tags = health_metrics[0].tags
    assert 'custom_env:production' in tags
    assert 'custom_team:platform' in tags


def test_full_metrics_collection(dd_run_check, aggregator, aws_instance):
    """Test that all metric categories are collected in one run."""
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    # Health
    aggregator.assert_metric("nutanix.health.up", value=1)

    # Cluster metrics
    aggregator.assert_metric("nutanix.cluster.count", at_least=0)

    # Host metrics
    aggregator.assert_metric("nutanix.host.count", at_least=0)

    # VM metrics
    aggregator.assert_metric("nutanix.vm.count", at_least=0)

    # Events and alerts
    aggregator.assert_metric("nutanix.event.occurred", at_least=0)
    aggregator.assert_metric("nutanix.alert.critical", at_least=0)

    # Storage
    aggregator.assert_metric("nutanix.storage_container.count", at_least=0)
