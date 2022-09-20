# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.avi_vantage import AviVantageCheck
from datadog_checks.dev.utils import get_metadata_metrics


def test_check(mock_client, get_expected_metrics, aggregator, unit_instance, dd_run_check):
    check = AviVantageCheck('avi_vantage', {}, [unit_instance])
    dd_run_check(check)
    aggregator.assert_service_check("avi_vantage.can_connect", AviVantageCheck.OK)
    for metric in get_expected_metrics():
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_integration(
    dd_environment, get_expected_metrics, aggregator, integration_instance, dd_run_check, datadog_agent
):
    check = AviVantageCheck('avi_vantage', {}, [integration_instance])
    check.check_id = 'test:123'
    dd_run_check(check)
    aggregator.assert_service_check("avi_vantage.can_connect", AviVantageCheck.OK)
    for metric in get_expected_metrics(endpoint='http://localhost:5000/'):
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    version_metadata = {
        'version.major': '20',
        'version.minor': '1',
        'version.patch': '5',
        'version.raw': '20.1.5',
        'version.scheme': 'semver',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.e2e
def test_e2e(dd_agent_check, integration_instance, get_expected_metrics):
    aggregator = dd_agent_check(integration_instance)

    aggregator.assert_service_check("avi_vantage.can_connect", AviVantageCheck.OK)
    for metric in get_expected_metrics(endpoint='http://localhost:5000/'):
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
