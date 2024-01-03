# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.base import AgentCheck
from tests.legacy.common import DEFAULT_METRICS

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.environ.get('OPENSTACK_E2E_LEGACY') is None or os.environ.get('OPENSTACK_E2E_LEGACY') == 'false',
        reason='Legacy test',
    ),
]


def test_check(dd_agent_check):
    aggregator = dd_agent_check()

    # assert default metrics
    for metric in DEFAULT_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()

    # assert service checks
    aggregator.assert_service_check('openstack.neutron.api.up', AgentCheck.OK, count=1)
    aggregator.assert_service_check('openstack.nova.api.up', AgentCheck.OK, count=1)
    aggregator.assert_service_check('openstack.keystone.api.up', AgentCheck.OK, count=1)
    aggregator.assert_service_check('openstack.nova.hypervisor.up', AgentCheck.OK, count=10)
    aggregator.assert_service_check('openstack.neutron.network.up', AgentCheck.OK, count=2)
