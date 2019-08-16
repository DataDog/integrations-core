# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.druid import DruidCheck

from .common import BROKER_URL

INSTANCE = {'url': BROKER_URL, 'tags': ['foo:bar']}


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_checks_integration(aggregator):

    check = DruidCheck('druid', {}, [INSTANCE])
    check.check(INSTANCE)

    assert_service_checks(aggregator)


@pytest.mark.e2e
def test_service_checks_e2e(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE)

    assert_service_checks(aggregator)


def assert_service_checks(aggregator):
    aggregator.assert_service_check(
        'druid.process.can_connect', AgentCheck.OK, ['url:http://localhost:8082/status/properties', 'foo:bar']
    )
    aggregator.assert_service_check(
        'druid.process.health',
        AgentCheck.OK,
        ['url:http://localhost:8082/status/health', 'foo:bar', 'service:druid/broker'],
    )
    aggregator.assert_all_metrics_covered()
