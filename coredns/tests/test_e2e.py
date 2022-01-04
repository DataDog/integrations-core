import platform

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import METRICS


@pytest.mark.e2e
def test_check_ok(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(platform.python_version() < "3", reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.e2e
def test_om_check_ok(dd_agent_check, openmetrics_instance):
    aggregator = dd_agent_check(openmetrics_instance, rate=True)
    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()
