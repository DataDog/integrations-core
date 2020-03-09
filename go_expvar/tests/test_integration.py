# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging

import pytest
from six import iteritems

from . import common

log = logging.getLogger(__file__)

CHECK_RATES_CUSTOM = {'go_expvar.num_calls': 10}


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_go_expvar(check, aggregator):
    check.check(common.INSTANCE)

    shared_tags = ['my_tag', 'expvar_url:{0}{1}'.format(common.INSTANCE['expvar_url'], common.GO_EXPVAR_URL_PATH)]

    for gauge in common.CHECK_GAUGES + common.CHECK_GAUGES_DEFAULT:
        aggregator.assert_metric(gauge, count=1, tags=shared_tags)
    for rate in common.CHECK_RATES:
        aggregator.assert_metric(rate, count=1, tags=shared_tags)
    for rate, value in iteritems(CHECK_RATES_CUSTOM):
        aggregator.assert_metric(rate, count=1, value=value, tags=shared_tags)

    aggregator.assert_all_metrics_covered()
