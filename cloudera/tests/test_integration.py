import pytest

from datadog_checks.cloudera import ClouderaCheck
from datadog_checks.cloudera.metrics import METRICS


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_given_bad_url_when_check_runs_then_service_check_critical(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
):
    with pytest.raises(Exception):
        # Given
        check = cloudera_check(instance)
        # When
        dd_run_check(check)
        # Then
        aggregator.assert_service_check('cloudera.can_connect', ClouderaCheck.CRITICAL)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_given_api_v48_endpoint_when_check_runs_then_service_check_ok_and_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
):
    # Given
    check = cloudera_check(instance)
    # When
    dd_run_check(check)
    # Then
    for category, metrics in METRICS.items():
        for metric in metrics:
            aggregator.assert_metric(f'cloudera.{category}.{metric}')
    aggregator.assert_service_check('cloudera.can_connect', ClouderaCheck.OK)
    # caddy test env is supposed to be in BAD_HEALTH
    aggregator.assert_service_check('cloudera.cluster.health', ClouderaCheck.CRITICAL, message="BAD_HEALTH")
    aggregator.assert_service_check('cloudera.host.health', ClouderaCheck.OK)
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_metadata(cloudera_check, instance, datadog_agent, dd_run_check):
    check = cloudera_check(instance)
    check.check_id = 'test:123'
    dd_run_check(check)

    raw_version = '7.2.15'
    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'cloudera',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
