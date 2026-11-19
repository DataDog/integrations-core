# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.kyototycoon import KyotoTycoonCheck

from .common import DEFAULT_INSTANCE, TAGS

GAUGES = list(KyotoTycoonCheck.GAUGES.values())
DB_GAUGES = list(KyotoTycoonCheck.DB_GAUGES.values())
TOTALS = list(KyotoTycoonCheck.TOTALS.values())
RATES = list(KyotoTycoonCheck.RATES.values())

# all the RATE type metrics
ALL_RATES = TOTALS + RATES


def test_check(aggregator, dd_environment):
    kt = KyotoTycoonCheck('kyototycoon', {}, {})
    kt.check(deepcopy(DEFAULT_INSTANCE))
    kt.check(deepcopy(DEFAULT_INSTANCE))

    _assert_check(aggregator)


@pytest.mark.unit
def test_error_status_reports_critical(aggregator, fake_http_response):
    fake_http_response(DEFAULT_INSTANCE['report_url'], status_code=503)
    kt = KyotoTycoonCheck('kyototycoon', {}, {})

    with pytest.raises(HTTPClientStatusError):
        kt.check(deepcopy(DEFAULT_INSTANCE))

    aggregator.assert_service_check(
        KyotoTycoonCheck.SERVICE_CHECK_NAME, status=KyotoTycoonCheck.CRITICAL, tags=TAGS, message='503 Server Error'
    )


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(DEFAULT_INSTANCE, rate=True)

    _assert_check(aggregator, rate_metric_count=1)


def _assert_check(aggregator, rate_metric_count=2):
    # prefix every metric with check name (kyototycoon.)
    # no replications, so ignore kyototycoon.replication.delay
    for mname in GAUGES:
        if mname != 'replication.delay':
            aggregator.assert_metric('kyototycoon.{}'.format(mname), tags=TAGS, count=2)

    for mname in DB_GAUGES:
        aggregator.assert_metric('kyototycoon.{}'.format(mname), tags=TAGS + ['db:0'], count=2)

    for mname in ALL_RATES:
        # serv_conn_count can decrease between check runs causing the agent to skip the rate
        if mname == 'connections':
            aggregator.assert_metric('kyototycoon.connections_per_s', tags=TAGS, at_least=0)
        else:
            aggregator.assert_metric('kyototycoon.{}_per_s'.format(mname), tags=TAGS, count=rate_metric_count)

    # service check
    aggregator.assert_service_check(KyotoTycoonCheck.SERVICE_CHECK_NAME, status=KyotoTycoonCheck.OK, tags=TAGS, count=2)

    aggregator.assert_all_metrics_covered()
