# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
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


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(discovery_min_instances=2)

    # Discovery finds both the coordinator and the broker container, each tagged by the
    # `druid.service` value returned in their own `/status/properties` response. Static
    # instance tags (e.g. `my:coordinator-instance-tag`) and exact `url:` tags can't be
    # asserted here since discovery has no way to set the former, and the latter differs
    # (container IP, not `localhost`) from the static config used by test_service_checks_e2e.
    for druid_service in ('druid/coordinator', 'druid/broker'):
        tag = 'druid_service:{}'.format(druid_service)
        aggregator.assert_service_check('druid.service.can_connect', AgentCheck.OK, at_least=1)
        aggregator.assert_service_check('druid.service.health', AgentCheck.OK, at_least=1)
        aggregator.assert_metric_has_tag('druid.service.health', tag)
        aggregator.assert_metric('druid.service.health', value=1, at_least=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, DruidCheck, compose_service='druid-broker')


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
        'druid_service:druid/coordinator',
    ]
    aggregator.assert_service_check('druid.service.health', AgentCheck.OK, tags=coordinator_tags, count=3)
    aggregator.assert_metric('druid.service.health', value=1, count=3, tags=coordinator_tags)

    broker_tags = ['url:http://localhost:8082/status/health', 'my:broker-instance-tag', 'druid_service:druid/broker']
    aggregator.assert_service_check('druid.service.health', AgentCheck.OK, tags=broker_tags, count=3)
    aggregator.assert_metric('druid.service.health', value=1, count=3, tags=broker_tags)

    aggregator.assert_all_metrics_covered()
