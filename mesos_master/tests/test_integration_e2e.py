# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.mesos_master import MesosMaster

from .common import BASIC_METRICS, CHECK_NAME, INSTANCE, OPTIONAL_METRICS, not_windows_ci

pytestmark = not_windows_ci


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check_integration(instance, aggregator):
    check = MesosMaster('mesos_master', {}, [instance])
    check.check(instance)

    assert_metric_coverage(aggregator)


@pytest.mark.e2e
def test_check_e2e(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, rate=True)
    assert_metric_coverage(aggregator)


def assert_metric_coverage(aggregator):
    check = MesosMaster(CHECK_NAME, {}, {})
    metrics = BASIC_METRICS
    for d in (
        check.ROLE_RESOURCES_METRICS,
        check.CLUSTER_TASKS_METRICS,
        check.CLUSTER_SLAVES_METRICS,
        check.CLUSTER_RESOURCES_METRICS,
        check.CLUSTER_FRAMEWORK_METRICS,
        check.STATS_METRICS,
    ):
        for m in d.values():
            metrics.append(m[0])

    for m in metrics:
        if m in OPTIONAL_METRICS:
            aggregator.assert_metric(m, at_least=0)
        else:
            aggregator.assert_metric(m)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('mesos_master.can_connect', status=check.OK)
