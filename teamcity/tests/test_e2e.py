# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2

from datadog_checks.base import AgentCheck
from datadog_checks.teamcity.constants import SERVICE_CHECK_OPENMETRICS

from .common import OPENMETRICS_INSTANCE, REST_INSTANCE, USE_OPENMETRICS


@pytest.mark.skipif(USE_OPENMETRICS, reason="Not available in OpenMetricsV2 check")
@pytest.mark.e2e
def test_e2e(aggregator, dd_agent_check):
    expected_error = '`projects` option is not supported for Python 2' if PY2 else '503 Server Error'
    with pytest.raises(Exception, match=expected_error):
        dd_agent_check(REST_INSTANCE, rate=True)

    assert not aggregator.service_check_names


@pytest.mark.skipif(not USE_OPENMETRICS, reason="Not available in REST check")
@pytest.mark.e2e
def test_e2e_openmetrics(aggregator, dd_agent_check):
    with pytest.raises(Exception, match='There was an error scraping endpoint'):
        dd_agent_check(OPENMETRICS_INSTANCE, rate=True)

    aggregator.assert_service_check(SERVICE_CHECK_OPENMETRICS, status=AgentCheck.CRITICAL)
