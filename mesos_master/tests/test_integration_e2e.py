# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import platform

import pytest
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.mesos_master import MesosMaster

from .common import BASIC_METRICS, CHECK_NAME, INSTANCE


@pytest.mark.e2e
def test_check_e2e(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, rate=True)
    assert_metric_coverage(aggregator)


# Linux only: https://github.com/docker/for-mac/issues/1031
@pytest.mark.skipif(platform.system() != 'Linux', reason='Only runs on Unix systems')
@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check_integration(instance, aggregator):
    check = MesosMaster('mesos_master', {}, [instance])
    check.check(instance)

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
        for _, m in iteritems(d):
            metrics.append(m[0])

    for m in metrics:
        aggregator.assert_metric(m)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('mesos_master.can_connect', status=check.OK)
