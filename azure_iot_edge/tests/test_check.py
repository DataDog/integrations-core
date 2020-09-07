# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.azure_iot_edge import AzureIotEdgeCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub

from . import common


@pytest.mark.usefixtures("mock_server")
def test_check(aggregator, mock_instance):
    # type: (AggregatorStub, dict) -> None
    check = AzureIotEdgeCheck('azure_iot_edge', {}, [mock_instance])
    check.check(mock_instance)

    for metric, metric_type, metric_tags in common.HUB_METRICS:
        tags = common.TAGS + metric_tags
        aggregator.assert_metric(metric, metric_type=metric_type, count=1, tags=tags)

    for metric, metric_type, metric_tags in common.AGENT_METRICS:
        tags = common.TAGS + metric_tags
        aggregator.assert_metric(metric, metric_type=metric_type, count=1, tags=tags)

    for metric, metric_type in common.MODULE_METRICS:
        for module_name in common.MODULES:
            tags = common.TAGS + ['module_name:{}'.format(module_name)]
            aggregator.assert_metric(metric, metric_type=metric_type, count=1, tags=tags)

    aggregator.assert_service_check(
        'azure_iot_edge.edge_hub.prometheus.health',
        AzureIotEdgeCheck.OK,
        count=1,
        tags=common.CUSTOM_TAGS + ['endpoint:{}'.format(common.MOCK_EDGE_HUB_PROMETHEUS_URL)],
    )
    aggregator.assert_service_check(
        'azure_iot_edge.edge_agent.prometheus.health',
        AzureIotEdgeCheck.OK,
        count=1,
        tags=common.CUSTOM_TAGS + ['endpoint:{}'.format(common.MOCK_EDGE_AGENT_PROMETHEUS_URL)],
    )
    # TODO
    # aggregator.assert_service_check(
    #     'azure_iot_edge.security_daemon.health', AzureIotEdgeCheck.OK, count=1, tags=common.CUSTOM_TAGS
    # )

    aggregator.assert_all_metrics_covered()
    # TODO
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())
