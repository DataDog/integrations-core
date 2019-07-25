# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import common

#
# To get the rrd metrics, once the dd environment is up go to localhost:8080/cacti and go through the
# setup wizard
#


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    check.check(instance)
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    aggregator.assert_metric('cacti.rrd.count', value=5)
    aggregator.assert_metric('cacti.hosts.count', value=1)
    aggregator.assert_metric('cacti.metrics.count')
    aggregator.assert_all_metrics_covered()
