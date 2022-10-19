# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.teamcity import TeamCityCheck
from datadog_checks.teamcity.constants import (
    SERVICE_CHECK_BUILD_PROBLEMS,
    SERVICE_CHECK_BUILD_STATUS,
    SERVICE_CHECK_OPENMETRICS,
    SERVICE_CHECK_TEST_RESULTS,
)

from .common import INSTANCE, USE_OPENMETRICS


@pytest.mark.e2e
def test_e2e(aggregator, dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, rate=True)
    aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_BUILD_STATUS), at_least=0)
    aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_BUILD_PROBLEMS), at_least=0)
    aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_TEST_RESULTS), at_least=0)


@pytest.mark.skipif(not USE_OPENMETRICS, reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.e2e
def test_omv2_e2e(aggregator, dd_agent_check, openmetrics_instance):
    aggregator = dd_agent_check(openmetrics_instance)
    aggregator.assert_service_check(SERVICE_CHECK_OPENMETRICS, status=TeamCityCheck.OK)
