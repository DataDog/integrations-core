# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


def test_health_check_success(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1, count=1, tags=['prism_central:10.0.0.197'])


def test_health_check_failure(dd_run_check, aggregator, mock_instance, mocker):
    def mock_exception(*args, **kwargs):
        from requests.exceptions import ConnectionError

        raise ConnectionError("Connection failed")

    mocker.patch('requests.Session.get', side_effect=mock_exception)
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=0, count=1, tags=['prism_central:10.0.0.197'])


def test_cluster_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'prism_central:10.0.0.197',
    ]

    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.nbr_nodes", value=1, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.vm.count", value=4, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.vm.inefficient_count", value=0, tags=expected_tags)


def test_cluster_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    from tests.metrics import CLUSTER_STATS_METRICS_REQUIRED

    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'prism_central:10.0.0.197',
    ]

    for metric in CLUSTER_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)


def test_pc_ip_with_port_raises_error(mock_instance):
    """Test that ConfigurationError is raised when pc_ip contains a port."""

    instance = mock_instance.copy()
    instance['pc_ip'] = '10.0.0.197:9440'

    with pytest.raises(ConfigurationError) as exc_info:
        NutanixCheck('nutanix', {}, [instance])

    assert "Conflicting configuration" in str(exc_info.value)


def test_pc_ip_without_port(mock_instance):
    """Test that pc_port is used when pc_ip has no port."""
    instance = mock_instance.copy()
    instance['pc_ip'] = '10.0.0.197'

    check = NutanixCheck('nutanix', {}, [instance])

    assert check.pc_ip == '10.0.0.197'
    assert check.pc_port == 9440
    assert check.base_url == 'https://10.0.0.197:9440'
