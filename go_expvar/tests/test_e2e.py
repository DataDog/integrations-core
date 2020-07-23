# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging

import pytest

from . import common

log = logging.getLogger(__file__)

CHECK_RATES_CUSTOM = ['go_expvar.num_calls']


@pytest.mark.e2e
def test_check_e2e(dd_agent_check):
    aggregator = dd_agent_check(common.INSTANCE, times=3)

    shared_tags = ['my_tag', 'expvar_url:{0}{1}'.format(common.INSTANCE['expvar_url'], common.GO_EXPVAR_URL_PATH)]

    for gauge in common.CHECK_GAUGES:
        aggregator.assert_metric(gauge, count=3, tags=shared_tags)
    for gauge in common.MEMSTAT_PAUSE_HISTOGRAM:
        # metric submitted only when the GC has run
        aggregator.assert_metric(gauge, count=1, tags=shared_tags)
    for rate in common.CHECK_RATES + CHECK_RATES_CUSTOM:
        aggregator.assert_metric(rate, count=2, tags=shared_tags)
    for count in common.CHECK_COUNT:
        aggregator.assert_metric(count, count=2, tags=shared_tags)

    aggregator.assert_all_metrics_covered()
