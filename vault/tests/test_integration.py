# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.vault import Vault


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_integration(aggregator, check, instance):
    check.check(instance)
    _test_check(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    _test_check(aggregator)


def _test_check(aggregator):
    aggregator.assert_metric('vault.is_leader', value=1, tags=['instance:foobar', 'is_leader:true'], count=1)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, AgentCheck.OK)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, AgentCheck.OK)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, AgentCheck.OK)
