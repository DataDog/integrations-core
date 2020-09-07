# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.azure_iot_edge import AzureIotEdgeCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub

from . import common


@pytest.mark.usefixtures("mock_server")
def test_check(aggregator, mock_instance):
    # type: (AggregatorStub, dict) -> None
    """
    Under normal conditions, metrics and service checks are collected as expected.
    """
    check = AzureIotEdgeCheck('azure_iot_edge', {}, [mock_instance])
    check.check(mock_instance)

    for metric, metric_type in common.HUB_METRICS:
        # Don't assert exact tags since they're very complex (many cross products).
        aggregator.assert_metric(metric, metric_type=metric_type)
        m = aggregator._metrics[metric][0]
        assert set(m.tags) >= set(common.TAGS)

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
    aggregator.assert_service_check(
        'azure_iot_edge.security_daemon.can_connect', AzureIotEdgeCheck.OK, count=1, tags=common.CUSTOM_TAGS
    )

    aggregator.assert_all_metrics_covered()

    # TODO
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures("mock_server")
def test_security_daemon_down(aggregator, mock_instance):
    # type: (AggregatorStub, dict) -> None
    """
    When the security daemon management API endpoint is unreachable, the security daemon service check
    reports as CRITICAL.
    """
    instance = copy.deepcopy(mock_instance)
    wrong_port = common.MOCK_SERVER_PORT + 1  # Will trigger exception.
    instance['security_daemon_management_api_url'] = 'http://localhost:{}/mgmt.json'.format(wrong_port)

    check = AzureIotEdgeCheck('azure_iot_edge', {}, [instance])
    check.check(instance)

    aggregator.assert_service_check('azure_iot_edge.security_daemon.can_connect', AzureIotEdgeCheck.CRITICAL)
    message = aggregator._service_checks['azure_iot_edge.security_daemon.can_connect'][0].message  # type: str
    assert 'Connection refused' in message
