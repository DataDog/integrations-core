# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from . import common, metrics
from datadog_checks.twemproxy import Twemproxy


SC_TAGS = ['host:{}'.format(common.HOST), 'port:{}'.format(common.PORT), 'optional:tag1']


def test_check(check, dd_environment, setup_request, aggregator):
    check.check(common.INSTANCE)

    for stat in metrics.GLOBAL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), at_least=0)
    for stat in metrics.POOL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=1)
    for stat in metrics.SERVER_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=2)

    # Test service check
    aggregator.assert_service_check('twemproxy.can_connect', status=Twemproxy.OK,
                                    tags=SC_TAGS, count=1)

    # Raises when COVERAGE=true and coverage < 100%
    aggregator.assert_all_metrics_covered()
