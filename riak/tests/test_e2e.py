# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.riak import Riak

from . import common


@pytest.mark.e2e
def test_riak_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    tags = ['my_tag']
    sc_tags = tags + ['url:' + instance['url']]

    for gauge in common.CHECK_GAUGES + common.CHECK_GAUGES_STATS:
        aggregator.assert_metric(gauge, tags=tags, count=2)

    aggregator.assert_service_check(common.SERVICE_CHECK_NAME, status=Riak.OK, tags=sc_tags)

    for gauge in common.GAUGE_OTHER:
        aggregator.assert_metric(gauge, count=1)

    aggregator.all_metrics_asserted()
