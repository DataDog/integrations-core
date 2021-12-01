import pytest

from datadog_checks.envoy import Envoy

from .common import DEFAULT_INSTANCE, PROMETHEUS_METRICS, requires_new_environment

pytestmark = [requires_new_environment]


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(DEFAULT_INSTANCE, rate=True)
    for metric in PROMETHEUS_METRICS:
        aggregator.assert_metric("envoy.{}".format(metric))
    aggregator.assert_service_check('envoy.can_connect', Envoy.OK)
