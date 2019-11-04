# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from datadog_checks.cilium import CiliumCheck

from .common import AGENT_METRICS


@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    agent_instance = {'agent_endpoint': 'localhost:9090/metrics', 'tags': ['pod_test']}
    aggregator = dd_agent_check(agent_instance, rate=True)
    for metric in AGENT_METRICS:
        aggregator.assert_metric(metric)