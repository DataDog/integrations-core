# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.aerospike import AerospikeCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_PROMETHEUS_METRICS, EXPECTED_PROMETHEUS_METRICS_5_6, HERE, VERSION

pytestmark = [pytest.mark.unit]


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def test_openmetricsv2_check(aggregator, dd_run_check, instance_openmetrics_v2, mock_http_response):

    check = AerospikeCheck('aerospike', {}, [instance_openmetrics_v2])
    dd_run_check(check)

    version_parts = [int(p) for p in VERSION.split('.')]

    if version_parts[0] >= 7:
        # these tests will include metrics from aerospike server version 7 and above
        metrics_to_check = aggregator.metric_names
        _test_check_after_v7(aggregator, dd_run_check, instance_openmetrics_v2, mock_http_response, metrics_to_check)

    elif version_parts >= [5, 6]:
        metrics_to_check = EXPECTED_PROMETHEUS_METRICS + EXPECTED_PROMETHEUS_METRICS_5_6
        _test_check_before_v7(aggregator, dd_run_check, instance_openmetrics_v2, mock_http_response, metrics_to_check)

    else:  # run tests on same metrics set for any other aerospike version
        metrics_to_check = EXPECTED_PROMETHEUS_METRICS
        _test_check_before_v7(aggregator, dd_run_check, instance_openmetrics_v2, mock_http_response, metrics_to_check)


def _test_check_before_v7(aggregator, dd_run_check, instance_openmetrics_v2, mock_http_response, metrics_to_check):
    """
    run checks if aerospike server version is below 7, validates, mock prom metrics, labels and metadata.csv
    """
    mock_http_response(file_path=get_fixture_path('prometheus.txt'))

    for metric_name in metrics_to_check:
        aggregator.assert_metric(metric_name)

        aggregator.assert_metric_has_tag(
            metric_name, 'endpoint:{}'.format(instance_openmetrics_v2.get('openmetrics_endpoint'))
        )
        aggregator.assert_metric_has_tag(metric_name, 'aerospike_cluster:null')
        aggregator.assert_metric_has_tag_prefix(metric_name, 'aerospike_service')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(_get_metadata_metrics_before_7(), check_submission_type=True)


def _test_check_after_v7(aggregator, dd_run_check, instance_openmetrics_v2, mock_http_response, metrics_to_check):
    """
    run checks if aerospike server version is 7 or above, validates, mock prom metrics, labels and metadata.csv
    """

    mock_http_response(file_path=get_fixture_path('prometheus_7x.txt'))

    for metric_name in metrics_to_check:
        aggregator.assert_metric(metric_name)

        # no need to validate node-ticks for labels, as its a counter to check how many times exporter url is called
        #    node-ticks wiill not have any labels associated
        if metric_name != "aerospike.aerospike_node_ticks":
            aggregator.assert_metric_has_tag(
                metric_name, 'endpoint:{}'.format(instance_openmetrics_v2.get('openmetrics_endpoint'))
            )

            aggregator.assert_metric_has_tag_prefix(metric_name, 'aerospike_cluster')
            aggregator.assert_metric_has_tag_prefix(metric_name, 'aerospike_service')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(_get_metadata_metrics_after_7(), check_submission_type=True)


def _get_metadata_metrics_before_7():
    """
    Returns metrics from metadata.csv which are available in aerospike version below 7
    """

    all_metrics = get_metadata_metrics()
    filtered_metrics = {}
    for metric_name, line in all_metrics.items():
        if not metric_name.startswith("aerospike.aerospike_"):
            filtered_metrics[metric_name] = line

    return filtered_metrics


def _get_metadata_metrics_after_7():
    """
    Returns metrics from metadata.csv which are available in aerospike version 7 and above
    """

    all_metrics = get_metadata_metrics()
    filtered_metrics = {}
    for metric_name, line in all_metrics.items():
        if metric_name.startswith("aerospike.aerospike_"):
            filtered_metrics[metric_name] = line

    print("\t\t\t ==> len - filtered_metrics ", len(filtered_metrics))

    return filtered_metrics
