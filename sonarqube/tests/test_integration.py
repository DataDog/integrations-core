import pytest

from .metrics import WEB_METRICS

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_integration_service_check_ok(aggregator, dd_run_check, sonarqube_check, web_instance_with_components):
    # Given
    check = sonarqube_check(web_instance_with_components)
    # When
    dd_run_check(check)
    # Then
    for metric in WEB_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_service_check('sonarqube.api_access', status=check.OK)
