# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.testing import requires_py3
from datadog_checks.exchange_server.metrics import METRICS_CONFIG


def get_exchange_server_metrics():
    exchange_server_metrics = []
    metric_namespace = 'exchange'
    for object_name, config in METRICS_CONFIG.items():
        if object_name.startswith("MSExchange"):
            metric_prefix = config.get('name', '')
            counters_config = config.get('counters', [])
            for _, entry in enumerate(counters_config, 1):
                for _, counter_config in entry.items():
                    metric_full_name = "{}.{}.{}".format(metric_namespace, metric_prefix, counter_config)
                    exchange_server_metrics.append(metric_full_name)
    return exchange_server_metrics


@pytest.mark.e2e
@requires_py3
def test_e2e_py3(dd_agent_check, aggregator, instance):
    aggregator = dd_agent_check(instance)
    aggregator.assert_service_check('exchange.windows.perf.health', AgentCheck.OK)
    for metric in get_exchange_server_metrics():
        aggregator.assert_metric(metric, count=0)
