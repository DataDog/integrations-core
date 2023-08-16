# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2

from datadog_checks.base import AgentCheck
from datadog_checks.teamcity.constants import SERVICE_CHECK_OPENMETRICS

from .common import (
    LEGACY_REST_INSTANCE,
    OPENMETRICS_INSTANCE,
    REST_INSTANCE,
    REST_INSTANCE_ALL_PROJECTS,
    REST_METRICS,
    USE_OPENMETRICS,
)


@pytest.mark.skipif(USE_OPENMETRICS or not PY2, reason="Not available in OpenMetricsV2 check")
@pytest.mark.e2e
def test_e2e_legacy(aggregator, dd_agent_check):
    dd_agent_check(LEGACY_REST_INSTANCE)
    for metric in REST_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_service_check('teamcity.build.status', status=AgentCheck.OK)
    aggregator.assert_service_check('teamcity.build.problems', count=2)
    aggregator.assert_service_check('teamcity.test.results', count=6)


@pytest.mark.skipif(USE_OPENMETRICS or PY2, reason="Not available in OpenMetricsV2 check")
@pytest.mark.e2e
def test_e2e(aggregator, dd_agent_check):
    dd_agent_check(REST_INSTANCE)
    for metric in REST_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_service_check('teamcity.build.status', status=AgentCheck.OK)
    aggregator.assert_service_check('teamcity.build.problems', count=2)
    aggregator.assert_service_check('teamcity.test.results', count=6)


@pytest.mark.skipif(USE_OPENMETRICS or PY2, reason="Not available in OpenMetricsV2 check")
@pytest.mark.e2e
def test_e2e_all_projects(aggregator, dd_agent_check):
    dd_agent_check(REST_INSTANCE_ALL_PROJECTS)
    for metric in REST_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_service_check('teamcity.build.status', status=AgentCheck.OK)
    aggregator.assert_service_check('teamcity.build.problems', count=2)
    aggregator.assert_service_check('teamcity.test.results', count=6)


@pytest.mark.skipif(not USE_OPENMETRICS, reason="Not available in REST check")
@pytest.mark.e2e
def test_e2e_openmetrics(aggregator, dd_agent_check):
    dd_agent_check(OPENMETRICS_INSTANCE)
    aggregator.assert_service_check(SERVICE_CHECK_OPENMETRICS, status=AgentCheck.OK)
