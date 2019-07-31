# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.twemproxy import Twemproxy

from . import common, metrics

SC_TAGS = ['host:{}'.format(common.HOST), 'port:{}'.format(common.PORT), 'optional:tag1']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_integration(check, dd_environment, setup_request, aggregator):
    check.check(common.INSTANCE)
    _test_check(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    _test_check(aggregator)


def _test_check(aggregator):
    for stat in metrics.GLOBAL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), at_least=0)
    for stat in metrics.POOL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=1)
    for stat in metrics.SERVER_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=2)

    # Test service check
    aggregator.assert_service_check('twemproxy.can_connect', status=Twemproxy.OK, tags=SC_TAGS, count=1)

    # Raises when COVERAGE=true and coverage < 100%
    aggregator.assert_all_metrics_covered()
