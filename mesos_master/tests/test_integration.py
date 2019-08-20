# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import platform

import pytest
from six import iteritems

from .common import BASIC_METRICS


@pytest.mark.integration
# Linux only: https://github.com/docker/for-mac/issues/1031
@pytest.mark.skipif(platform.system() != 'Linux', reason="Only runs on Unix systems")
@pytest.mark.usefixtures("dd_environment")
def test_integration(check, instance, aggregator):
    check.check(instance)
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

    aggregator.assert_service_check('mesos_master.can_connect', count=1, status=check.OK)
