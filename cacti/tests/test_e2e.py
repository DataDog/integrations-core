# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

#
# You can access cacti in localhost:8080/cacti and log in with admin/Admin23@
#


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    aggregator.assert_metric('cacti.rrd.count', value=5)
    aggregator.assert_metric('cacti.hosts.count', value=1)
    aggregator.assert_metric('cacti.metrics.count')
    aggregator.assert_all_metrics_covered()
