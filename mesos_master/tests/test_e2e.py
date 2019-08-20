import pytest

from six import iteritems

from .common import BASIC_METRICS, INSTANCE


@pytest.mark.e2e
def test_check_ok(dd_agent_check, check):
    aggregator = dd_agent_check(INSTANCE, times=2)
    metrics = BASIC_METRICS

    for d in (
        check.ROLE_RESOURCES_METRICS,
        check.CLUSTER_TASKS_METRICS,
        check.CLUSTER_SLAVES_METRICS,
        check.CLUSTER_RESOURCES_METRICS,
        check.CLUSTER_FRAMEWORK_METRICS,
        check.STATS_METRICS,
    ):
        for _, m in iteritems(d):
            metrics.append(m[0])

    for m in metrics:
        aggregator.assert_metric(m)

    aggregator.assert_all_metrics_covered()
