# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.tls import TLSCheck


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance_e2e):
    aggregator = dd_agent_check(instance_e2e)

    aggregator.assert_service_check(TLSCheck.SERVICE_CHECK_CAN_CONNECT, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(TLSCheck.SERVICE_CHECK_VERSION, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(TLSCheck.SERVICE_CHECK_VALIDATION, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(TLSCheck.SERVICE_CHECK_EXPIRATION, status=TLSCheck.OK, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()
