# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.avi_vantage import AviVantageCheck
from datadog_checks.dev.utils import get_metadata_metrics


def test_check(mock_client, expected_metrics, aggregator, unit_instance, dd_run_check):
    check = AviVantageCheck('avi_vantage', {}, [unit_instance])
    dd_run_check(check)
    for metric in expected_metrics:
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_integration(dd_environment, expected_metrics, aggregator, integration_instance, dd_run_check):
    check = AviVantageCheck('avi_vantage', {}, [integration_instance])
    dd_run_check(check)
    for metric in expected_metrics:
        tags = [t.replace('https://34.123.32.255/', 'http://localhost:5000/') for t in metric['tags']]
        aggregator.assert_metric(metric['name'], metric['value'], tags, metric_type=metric['type'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
