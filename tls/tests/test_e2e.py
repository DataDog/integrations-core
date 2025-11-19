# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.tls import TLSCheck
from datadog_checks.tls.const import (
    SERVICE_CHECK_CAN_CONNECT,
    SERVICE_CHECK_EXPIRATION,
    SERVICE_CHECK_VALIDATION,
    SERVICE_CHECK_VERSION,
)


@pytest.mark.e2e
def test_e2e(dd_environment, dd_agent_check, instance_e2e):
    aggregator = dd_agent_check(instance_e2e)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=TLSCheck.OK, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()
