# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable

import pytest

from datadog_checks.azure_iot_edge import AzureIoTEdgeCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    # type: (Callable) -> None
    aggregator = dd_agent_check(rate=True)  # type: AggregatorStub

    for metric in common.E2E_METRICS:
        aggregator.assert_metric(metric)
        m = aggregator._metrics[metric][0]
        assert set(m.tags) >= set(common.E2E_TAGS)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('azure.iot_edge.edge_agent.prometheus.health', AzureIoTEdgeCheck.OK)
    aggregator.assert_service_check('azure.iot_edge.edge_hub.prometheus.health', AzureIoTEdgeCheck.OK)
