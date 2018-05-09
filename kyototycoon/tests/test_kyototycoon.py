# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.kyototycoon import KyotoTycoonCheck

from .common import (
    URL
)


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

    # run the check
    kt.check(instance)

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
            aggregator.assert_metric('kyototycoon.{0}'.format(mname), tags=TAGS, count=1)

    for mname in DB_GAUGES:
        aggregator.assert_metric('kyototycoon.{0}'.format(mname), tags=TAGS + ['db:0'], count=1)

    for mname in ALL_RATES:
        aggregator.assert_metric('kyototycoon.{0}_per_s'.format(mname), tags=TAGS, count=1)

    # service check
    aggregator.assert_service_check(
        KyotoTycoonCheck.SERVICE_CHECK_NAME, status=KyotoTycoonCheck.OK, tags=TAGS, count=1)

    aggregator.assert_all_metrics_covered()
