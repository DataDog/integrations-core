import pytest


@pytest.mark.e2e
def test_check_ok(dd_agent_check, instance):

    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_all_metrics_covered()
