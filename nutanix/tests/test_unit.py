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

    aggregator.assert_metric("nutanix.health.up", value=1, count=1, tags=['prism_central:10.0.0.197'])


def test_health_check_failure(dd_run_check, aggregator, mock_instance, mocker):
    """Test health check failure."""

    def mock_exception(*args, **kwargs):
        from requests.exceptions import ConnectionError

        raise ConnectionError("Connection failed")

    mocker.patch('requests.Session.get', side_effect=mock_exception)
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=0, count=1, tags=['prism_central:10.0.0.197'])


# Cluster Metrics Tests
def test_cluster_basic_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test basic cluster metrics with actual fixture data."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Cluster count - one cluster with full data
    aggregator.assert_metric(
        "nutanix.cluster.count",
        value=1,
        count=1,
        tags=[
            'nutanix_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'nutanix_cluster_name:datadoghq.com-Default-Org-dkhrzg',
            'prism_central:10.0.0.197',
        ],
    )

    # VM count - only one cluster has vmCount field
    aggregator.assert_metric("nutanix.cluster.vm_count", count=1)

    # Node count - both clusters have nodes
    aggregator.assert_metric("nutanix.cluster.node_count", count=2)

    # Availability - both clusters
    aggregator.assert_metric("nutanix.cluster.available", count=2)


def test_cluster_collection_toggle(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that disabling cluster collection works."""
    mock_instance['collect_cluster_metrics'] = False
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.count", count=0)


# Host Metrics Tests
def test_host_basic_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test basic host metrics with actual fixture data."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Hosts fixture has 1 host
    aggregator.assert_metric("nutanix.host.count", count=1)


def test_host_collection_toggle(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that disabling host collection works."""
    mock_instance['collect_host_metrics'] = False
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.count", count=0)


# VM Metrics Tests
def test_vm_collection_toggle(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that disabling VM collection works."""
    mock_instance['collect_vm_metrics'] = False
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", count=0)


# Events and Alerts Tests
def test_alerts_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that alert severity counts are always submitted."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Alert severity counts should always be submitted (even when 0)
    aggregator.assert_metric("nutanix.alert.critical", value=0, count=1, tags=['prism_central:10.0.0.197'])
    aggregator.assert_metric("nutanix.alert.warning", value=0, count=1, tags=['prism_central:10.0.0.197'])
    aggregator.assert_metric("nutanix.alert.info", value=0, count=1, tags=['prism_central:10.0.0.197'])


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
        tags=['custom_env:test', 'custom_team:platform', 'prism_central:10.0.0.197'],
    )


def test_resource_specific_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that cluster and host metrics have proper resource-specific tags."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Cluster tags
    aggregator.assert_metric(
        "nutanix.cluster.count",
        count=1,
        tags=[
            'nutanix_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'nutanix_cluster_name:datadoghq.com-Default-Org-dkhrzg',
            'prism_central:10.0.0.197',
        ],
    )

    # Host tags - verify at least one host metric exists
    aggregator.assert_metric("nutanix.host.count", count=1)
