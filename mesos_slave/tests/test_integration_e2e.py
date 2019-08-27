# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import platform

import pytest
from six import iteritems

from datadog_checks.mesos_slave import MesosSlave

from .common import CHECK_NAME


@pytest.mark.integration
# Linux only: https://github.com/docker/for-mac/issues/1031
@pytest.mark.skipif(platform.system() != 'Linux', reason="Only runs on Unix systems")
@pytest.mark.usefixtures("dd_environment")
def test_integration(instance, aggregator):
    check = MesosSlave('mesos_slave', {}, [instance])
    check.check(instance)
    check.check(instance)
    assert_metrics_covered(aggregator)


@pytest.mark.e2e
# Linux only: https://github.com/docker/for-mac/issues/1031
@pytest.mark.skipif(platform.system() != 'Linux', reason="Only runs on Unix systems")
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    assert_metrics_covered(aggregator)


def assert_metrics_covered(aggregator):
    check = MesosSlave(CHECK_NAME, {}, [{}])
    metrics = {}
    for d in (
        check.SLAVE_TASKS_METRICS,
        check.SYSTEM_METRICS,
        check.SLAVE_RESOURCE_METRICS,
        check.SLAVE_EXECUTORS_METRICS,
        check.STATS_METRICS,
    ):
        metrics.update(d)

    for _, v in iteritems(metrics):
        aggregator.assert_metric(v[0])

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('mesos_slave.can_connect', status=check.OK, count=2)
