import pytest

from . import common


@pytest.mark.e2e
def test_check_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)
