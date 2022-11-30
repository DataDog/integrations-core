import pytest

from datadog_checks.cloudera import ClouderaCheck
from datadog_checks.cloudera.metrics import METRICS


@pytest.mark.integration
def test_given_bad_url_when_check_runs_then_service_check_critical(
    aggregator,
    dd_run_check,
    cloudera_check,
):
    # Given
    instance = {
        'api_url': 'bad_url',
    }
    check = cloudera_check(instance)
    # When
    dd_run_check(check)
    # Then
    aggregator.assert_service_check('cloudera.can_connect', ClouderaCheck.CRITICAL)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_given_api_v12_endpoint_when_check_runs_then_service_check_ok_and_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
):
    # Given
    instance = {
        'username': 'cloudera',
        'password': 'cloudera',
        'api_url': 'http://localhost:7180/api/v12',
    }
    check = cloudera_check(instance)
    # When
    dd_run_check(check)
    # Then
    for category, metrics in METRICS.items():
        for metric in metrics:
            aggregator.assert_metric(f'cloudera.{category}.{metric}')
    aggregator.assert_service_check('cloudera.can_connect', ClouderaCheck.OK)


@pytest.mark.integration
def test_given_api_v48_endpoint_when_check_runs_then_service_check_ok_and_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
):
    # Given
    instance = {
        'username': 'cloudera',
        'password': 'cloudera',
        'api_url': 'http://localhost:7180/api/v12',
    }
    check = cloudera_check(instance)
    # When
    dd_run_check(check)
    # Then
    for category, metrics in METRICS.items():
        for metric in metrics:
            aggregator.assert_metric(f'cloudera.{category}.{metric}')
    aggregator.assert_service_check('cloudera.can_connect', ClouderaCheck.OK)
    assert False
