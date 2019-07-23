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
    _assert_all_metrics(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    _assert_all_metrics(aggregator)


def _assert_all_metrics(aggregator):
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
