# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from six import itervalues

from datadog_checks.kyototycoon import KyotoTycoonCheck

from .common import DEFAULT_INSTANCE, TAGS


def test_check(aggregator, dd_environment):
    """
    Testing Kyototycoon check.
    """
    kt = KyotoTycoonCheck('kyototycoon', {}, {})

    # run the check
    kt.check(deepcopy(DEFAULT_INSTANCE))

    GAUGES = list(itervalues(KyotoTycoonCheck.GAUGES))
    DB_GAUGES = list(itervalues(KyotoTycoonCheck.DB_GAUGES))
    TOTALS = list(itervalues(KyotoTycoonCheck.TOTALS))
    RATES = list(itervalues(KyotoTycoonCheck.RATES))

    # all the RATE type metrics
    ALL_RATES = TOTALS + RATES

    # prefix every metric with check name (kyototycoon.)
    # no replications, so ignore kyototycoon.replication.delay
    for mname in GAUGES:
        if mname != 'replication.delay':
            aggregator.assert_metric('kyototycoon.{}'.format(mname), tags=TAGS, count=1)

    for mname in DB_GAUGES:
        aggregator.assert_metric('kyototycoon.{}'.format(mname), tags=TAGS + ['db:0'], count=1)

    for mname in ALL_RATES:
        aggregator.assert_metric('kyototycoon.{}_per_s'.format(mname), tags=TAGS, count=1)

    # service check
    aggregator.assert_service_check(KyotoTycoonCheck.SERVICE_CHECK_NAME, status=KyotoTycoonCheck.OK, tags=TAGS, count=1)

    aggregator.assert_all_metrics_covered()
