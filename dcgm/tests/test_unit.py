# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.dcgm import DcgmCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_METRICS

pytestmark = [pytest.mark.unit]


def test_critical_service_check(dd_run_check, aggregator):
    """
    When we can't connect to dcgm-exporter for whatever reason we should only submit a CRITICAL service check.
    """
    check = DcgmCheck(
        'dcgm',
        {},
        [
            {
                'openmetrics_endpoint': 'http://localhost:5555/metrics',
            }
        ],
    )
    with pytest.raises(Exception, match="requests.exceptions.ConnectionError"):
        dd_run_check(check)
    aggregator.assert_service_check('dcgm.openmetrics.health', status=check.CRITICAL)


@pytest.mark.usefixtures("mock_metrics")
def test_successful_run(dd_run_check, aggregator, check):
    dd_run_check(check)
    aggregator.assert_service_check('dcgm.openmetrics.health', DcgmCheck.OK)
    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(name=f"dcgm.{metric}")
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_invalid_config():
    """
    Config with unknown fields should raise an exception.
    """
    check = DcgmCheck('dcgm', {}, [{'bad_config_option': 'test'}])
    with pytest.raises(ConfigurationError):
        check.load_configuration_models()
