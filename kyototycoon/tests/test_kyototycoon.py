# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.kyototycoon import KyotoTycoonCheck

from .common import DEFAULT_INSTANCE, TAGS

GAUGES = KyotoTycoonCheck.GAUGES.values()
DB_GAUGES = KyotoTycoonCheck.DB_GAUGES.values()
TOTALS = KyotoTycoonCheck.TOTALS.values()
RATES = KyotoTycoonCheck.RATES.values()

# all the RATE type metrics
ALL_RATES = TOTALS + RATES


def test_check(aggregator, dd_environment):
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    kt.check(deepcopy(DEFAULT_INSTANCE))
    kt.check(deepcopy(DEFAULT_INSTANCE))

    _assert_check(aggregator, 2)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(DEFAULT_INSTANCE, rate=True)

    _assert_check(aggregator, 1)


def _assert_check(aggregator, rate_metric_count):
    # prefix every metric with check name (kyototycoon.)
    # no replications, so ignore kyototycoon.replication.delay
    for mname in GAUGES:
        if mname != 'replication.delay':
            aggregator.assert_metric('kyototycoon.{}'.format(mname), tags=TAGS, count=2)

    for mname in DB_GAUGES:
        aggregator.assert_metric('kyototycoon.{}'.format(mname), tags=TAGS + ['db:0'], count=2)

    for mname in ALL_RATES:
        aggregator.assert_metric('kyototycoon.{}_per_s'.format(mname), tags=TAGS, count=rate_metric_count)

    # service check
    aggregator.assert_service_check(KyotoTycoonCheck.SERVICE_CHECK_NAME, status=KyotoTycoonCheck.OK, tags=TAGS, count=2)

    aggregator.assert_all_metrics_covered()
