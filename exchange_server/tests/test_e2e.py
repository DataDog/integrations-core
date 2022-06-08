# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.testing import requires_py3
from datadog_checks.exchange_server.metrics import METRICS_CONFIG


@pytest.mark.e2e
@requires_py3
def test_e2e_py3(dd_agent_check, aggregator, instance):
    metric_namespace = 'exchange'
    aggregator = dd_agent_check(instance)
    aggregator.assert_service_check('exchange.windows.perf.health', AgentCheck.OK)
    for object_name, config in METRICS_CONFIG.items():
        if object_name.startswith("MSExchange"):
            metric_prefix = config.get('name', '')
            counters_config = config.get('counters', [])
            for _, entry in enumerate(counters_config, 1):
                for _, counter_config in entry.items():
                    metric_full_name = f"{metric_namespace}.{metric_prefix}.{counter_config}"
                    aggregator.assert_metric(metric_full_name, count=0)
