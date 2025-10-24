# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.metrics import CLUSTER_STATS_METRICS_REQUIRED, HOST_STATS_METRICS_REQUIRED

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
        'ntnx_cluster_name:datadoghq.com-Default-Org-dkhrzg',
        'prism_central:10.0.0.197',
    ]

    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.nbr_nodes", value=1, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.vm.count", value=2, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.vm.inefficient_count", value=0, tags=expected_tags)


def test_cluster_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadoghq.com-Default-Org-dkhrzg',
        'prism_central:10.0.0.197',
    ]

    for metric in CLUSTER_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)


def test_host_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadoghq.com-Default-Org-dkhrzg',
        'ntnx_host_name:10-0-0-9-aws-us-east-1a',
        'ntnx_host_type:HYPER_CONVERGED',
        'ntnx_hypervisor_name:AHV 10.0.1.4',
        'ntnx_hypervisor_type:AHV',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'prism_central:10.0.0.197',
    ]

    aggregator.assert_metric("nutanix.host.count", value=1, tags=expected_tags)


def test_host_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadoghq.com-Default-Org-dkhrzg',
        'ntnx_host_name:10-0-0-9-aws-us-east-1a',
        'ntnx_host_type:HYPER_CONVERGED',
        'ntnx_hypervisor_name:AHV 10.0.1.4',
        'ntnx_hypervisor_type:AHV',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'prism_central:10.0.0.197',
    ]

    for metric in HOST_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)
