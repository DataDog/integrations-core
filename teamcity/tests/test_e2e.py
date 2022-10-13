# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.teamcity import TeamCityCheck
from datadog_checks.teamcity.constants import (
    SERVICE_CHECK_BUILD_PROBLEMS,
    SERVICE_CHECK_BUILD_STATUS,
    SERVICE_CHECK_OPENMETRICS,
    SERVICE_CHECK_TEST_RESULTS,
)

from .common import E2E_PROMETHEUS_METRICS, LEGACY_INSTANCE


@pytest.mark.e2e
def test_e2e(aggregator, dd_agent_check):
    aggregator = dd_agent_check(LEGACY_INSTANCE, rate=True)

    aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_BUILD_STATUS), at_least=0)
    aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_BUILD_PROBLEMS), at_least=0)
    aggregator.assert_service_check('teamcity.{}'.format(SERVICE_CHECK_TEST_RESULTS), at_least=0)


@pytest.mark.e2e
def test_omv2_e2e(aggregator, dd_agent_check, omv2_instance):
    aggregator = dd_agent_check(omv2_instance, rate=True)

    for metric in E2E_PROMETHEUS_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(SERVICE_CHECK_OPENMETRICS, status=TeamCityCheck.OK)
