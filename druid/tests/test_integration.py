# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.druid import DruidCheck

from .common import BROKER_URL


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_status_checks(aggregator):
    instance = {'process_url': BROKER_URL, 'tags': ['foo:bar']}
    check = DruidCheck('druid', {}, [instance])
    check.check(instance)

    aggregator.assert_service_check(
        'druid.process.can_connect', AgentCheck.OK, ['url:http://localhost:8082/status/properties', 'foo:bar']
    )
    aggregator.assert_service_check(
        'druid.process.health',
        AgentCheck.OK,
        ['url:http://localhost:8082/status/health', 'foo:bar', 'process:druid/broker'],
    )

    aggregator.assert_all_metrics_covered()
