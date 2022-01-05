import platform

import pytest

from .common import METRICS, METRICS_V2


@pytest.mark.e2e
def test_check_ok(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(platform.python_version() < "3", reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.e2e
def test_om_check_ok(dd_agent_check, omv2_instance):
    aggregator = dd_agent_check(omv2_instance, rate=True)
    for metric in METRICS_V2:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
