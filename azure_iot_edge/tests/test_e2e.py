# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable

import pytest

from datadog_checks.azure_iot_edge import AzureIotEdgeCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    # type: (Callable) -> None
    aggregator = dd_agent_check(rate=True)  # type: AggregatorStub

    for metric in common.E2E_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('azure_iot_edge.edge_hub.prometheus.health', AzureIotEdgeCheck.OK)
    aggregator.assert_service_check('azure_iot_edge.edge_agent.prometheus.health', AzureIotEdgeCheck.OK)
