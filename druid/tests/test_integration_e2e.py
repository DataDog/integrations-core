# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.druid import DruidCheck

from .common import BROKER_URL, COORDINATOR_URL

CONFIG = {
    'instances': [
        {'url': COORDINATOR_URL, 'tags': ['my:coordinator-instance-tag']},
        {'url': BROKER_URL, 'tags': ['my:broker-instance-tag']},
    ],
    'init_config': {},
}


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_checks_integration(aggregator):
    for _ in range(3):
        for instance in CONFIG['instances']:
            check = DruidCheck('druid', CONFIG, [instance])
            check.check(instance)

    assert_service_checks(aggregator)


@pytest.mark.e2e
def test_service_checks_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG, times=3)

    assert_service_checks(aggregator)


def assert_service_checks(aggregator):
    aggregator.assert_service_check(
        'druid.service.can_connect',
        AgentCheck.OK,
        tags=['url:http://localhost:8081/status/properties', 'my:coordinator-instance-tag'],
        count=3,
    )
    aggregator.assert_service_check(
        'druid.service.can_connect',
        AgentCheck.OK,
        tags=['url:http://localhost:8082/status/properties', 'my:broker-instance-tag'],
        count=3,
    )

    coordinator_tags = [
        'url:http://localhost:8081/status/health',
        'my:coordinator-instance-tag',
        'service:druid/coordinator',
    ]
    aggregator.assert_service_check('druid.service.health', AgentCheck.OK, tags=coordinator_tags, count=3)
    aggregator.assert_metric('druid.service.health', value=1, count=3, tags=coordinator_tags)

    broker_tags = ['url:http://localhost:8082/status/health', 'my:broker-instance-tag', 'service:druid/broker']
    aggregator.assert_service_check('druid.service.health', AgentCheck.OK, tags=broker_tags, count=3)
    aggregator.assert_metric('druid.service.health', value=1, count=3, tags=broker_tags)

    aggregator.assert_all_metrics_covered()
