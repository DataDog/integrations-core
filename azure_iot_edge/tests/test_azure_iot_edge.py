# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import pytest

from datadog_checks.azure_iot_edge import AzureIotEdgeCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics

from . import common


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = AzureIotEdgeCheck('azure_iot_edge', {}, [instance])
    check.check(instance)

    for metric, metric_type in common.METRICS:
        aggregator.assert_metric(metric, metric_type=metric_type, count=1, tags=common.TAGS)

    aggregator.assert_service_check(
        'azure_iot_edge.edge_hub.prometheus.health',
        AzureIotEdgeCheck.OK,
        count=1,
        tags=common.TAGS + ['endpoint:{}'.format(common.EDGE_HUB_PROMETHEUS_ENDPOINT)],
    )
    aggregator.assert_service_check(
        'azure_iot_edge.edge_agent.prometheus.health',
        AzureIotEdgeCheck.OK,
        count=1,
        tags=common.TAGS + ['endpoint:{}'.format(common.EDGE_AGENT_PROMETHEUS_ENDPOINT)],
    )
    aggregator.assert_service_check(
        'azure_iot_edge.security_daemon.health', AzureIotEdgeCheck.OK, count=1, tags=common.TAGS
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
