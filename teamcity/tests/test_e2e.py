# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.teamcity.constants import (
    SERVICE_CHECK_BUILD_PROBLEMS,
    SERVICE_CHECK_BUILD_STATUS,
    SERVICE_CHECK_TEST_RESULTS,
)

from .common import INSTANCE


@pytest.mark.e2e
def test_e2e(aggregator, dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, rate=True)
    aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_BUILD_STATUS), at_least=0)
    aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_BUILD_PROBLEMS), at_least=0)
    aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_TEST_RESULTS), at_least=0)
