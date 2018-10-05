# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import logging

from . import common

log = logging.getLogger(__file__)

CHECK_RATES_CUSTOM = {'go_expvar.num_calls': 10}


@pytest.mark.integration
def test_go_expvar(check, spin_up_go_expvar, aggregator):
    check.check(common.INSTANCE)

    shared_tags = [
        'my_tag',
        'expvar_url:{0}{1}'.format(common.INSTANCE['expvar_url'], common.GO_EXPVAR_URL_PATH)
    ]

    for gauge in common.CHECK_GAUGES + common.CHECK_GAUGES_DEFAULT:
        aggregator.assert_metric(gauge, count=1, tags=shared_tags)
    for rate in common.CHECK_RATES:
        aggregator.assert_metric(rate, count=1, tags=shared_tags)
    for rate, value in CHECK_RATES_CUSTOM.iteritems():
        aggregator.assert_metric(rate, count=1, value=value, tags=shared_tags)

    aggregator.assert_all_metrics_covered()
