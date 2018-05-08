# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.kyototycoon import KyotoTycoonCheck

from .common import (
    URL
)


@pytest.mark.integration
def test_check(aggregator, kyototycoon):
    """
    Testing Kyototycoon check.
    """
    kt = KyotoTycoonCheck('kyototycoon', {}, {})

    TAGS = ['optional:tag1']

    instance = {
        'report_url': '{0}/rpc/report'.format(URL),
        'tags': TAGS
    }

    # run the check twice so we can get some rate metrics
    for i in range(2):
        kt.check(instance)

    # there are 2 instances of each metric because we run the check twice
    
    GAUGES = KyotoTycoonCheck.GAUGES.values()
    DB_GAUGES = KyotoTycoonCheck.DB_GAUGES.values()
    TOTALS = KyotoTycoonCheck.TOTALS.values()
    RATES = KyotoTycoonCheck.RATES.values()

    # all the RATE type metrics
    ALL_RATES = TOTALS + RATES

    # prefix every metric with check name (kyototycoon.)
    # no replications, so ignore kyototycoon.replication.delay
    for mname in GAUGES:
        if mname != 'replication.delay':
            aggregator.assert_metric('kyototycoon.{0}'.format(mname), tags=TAGS, count=2)

    for mname in DB_GAUGES:
        aggregator.assert_metric('kyototycoon.{0}'.format(mname), tags=TAGS + ['db:0'], count=2)
        
    # since the aggregator doesn't actually calculate the rate between two instances of a metric
    #   we actually end up with 2 counts of a RATE metric, rather than just 1
    for mname in ALL_RATES:
        aggregator.assert_metric('kyototycoon.{0}_per_s'.format(mname), tags=TAGS, count=2)

    # service check
    aggregator.assert_service_check(
        KyotoTycoonCheck.SERVICE_CHECK_NAME, status=KyotoTycoonCheck.OK, tags=TAGS, at_least=1)

    aggregator.assert_all_metrics_covered()
