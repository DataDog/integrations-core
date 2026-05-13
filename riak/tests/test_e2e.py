# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.riak import Riak

from . import common


@pytest.mark.e2e
def test_check(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    tags = ['my_tag']
    sc_tags = tags + ['url:' + instance['url']]

    for gauge in common.CHECK_GAUGES + common.CHECK_GAUGES_STATS:
        aggregator.assert_metric(gauge, tags=tags, at_least=1)

    aggregator.assert_service_check(common.SERVICE_CHECK_NAME, status=Riak.OK, tags=sc_tags)

    for gauge in common.GAUGE_OTHER:
        aggregator.assert_metric(gauge, at_least=0)

    aggregator.all_metrics_asserted()
