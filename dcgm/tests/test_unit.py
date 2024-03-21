# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.dcgm import DcgmCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_METRICS


def test_critical_service_check(dd_run_check, aggregator, mock_http_response, check):
    """
    When we can't connect to dcgm-exporter for whatever reason we should only submit a CRITICAL service check.
    """
    mock_http_response(status_code=404)
    with pytest.raises(Exception, match="requests.exceptions.HTTPError"):
        dd_run_check(check)
    aggregator.assert_service_check('dcgm.openmetrics.health', status=check.CRITICAL)


@pytest.mark.usefixtures("mock_metrics")
def test_successful_run(dd_run_check, aggregator, check):
    dd_run_check(check)
    aggregator.assert_service_check('dcgm.openmetrics.health', DcgmCheck.OK)
    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(name=metric)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_invalid_config():
    """
    Config with unknown fields should raise an exception.
    """
    check = DcgmCheck('dcgm', {}, [{'bad_config_option': 'test'}])
    with pytest.raises(ConfigurationError):
        check.load_configuration_models()
