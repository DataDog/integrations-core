# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from typing import Callable  # noqa: F401

import pytest
import requests

from datadog_checks.azure_iot_edge import AzureIoTEdgeCheck
from datadog_checks.azure_iot_edge.types import Instance  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics

from . import common


@pytest.mark.usefixtures("mock_server")
def test_check(aggregator, mock_instance, dd_run_check):
    # type: (AggregatorStub, Instance, Callable) -> None
    """
    Under normal conditions, metrics and service checks are collected as expected.
    """
    check = AzureIoTEdgeCheck('azure_iot_edge', {}, [mock_instance])
    dd_run_check(check)

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
        'azure.iot_edge.edge_hub.prometheus.health',
        AzureIoTEdgeCheck.OK,
        count=1,
        tags=common.CUSTOM_TAGS + ['endpoint:{}'.format(common.MOCK_EDGE_HUB_PROMETHEUS_URL)],
    )
    aggregator.assert_service_check(
        'azure.iot_edge.edge_agent.prometheus.health',
        AzureIoTEdgeCheck.OK,
        count=1,
        tags=common.CUSTOM_TAGS + ['endpoint:{}'.format(common.MOCK_EDGE_AGENT_PROMETHEUS_URL)],
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures("mock_server")
def test_version_metadata(datadog_agent, dd_run_check, mock_instance):
    # type: (DatadogAgentStub, Callable, Instance) -> None
    check = AzureIoTEdgeCheck('azure_iot_edge', {}, [mock_instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    major, minor, patch, raw = common.MOCK_EDGE_AGENT_VERSION
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw,
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.usefixtures("mock_server")
@pytest.mark.parametrize(
    "option, url, service_check",
    [
        pytest.param(
            "edge_agent_prometheus_url",
            common.MOCK_EDGE_AGENT_PROMETHEUS_URL,
            "azure.iot_edge.edge_agent.prometheus.health",
            id="edge-agent",
        ),
        pytest.param(
            "edge_hub_prometheus_url",
            common.MOCK_EDGE_HUB_PROMETHEUS_URL,
            "azure.iot_edge.edge_hub.prometheus.health",
            id="edge-hub",
        ),
    ],
)
def test_prometheus_endpoint_down(aggregator, mock_instance, option, url, service_check):
    # type: (AggregatorStub, dict, str, str, str) -> None
    """
    When a Prometheus endpoint is unreachable, service check reports as CRITICAL.
    """
    instance = copy.deepcopy(mock_instance)
    wrong_port = common.MOCK_SERVER_PORT + 1  # Will trigger exception.
    instance[option] = url.replace(str(common.MOCK_SERVER_PORT), str(wrong_port))

    check = AzureIoTEdgeCheck('azure_iot_edge', {}, [instance])

    with pytest.raises(requests.ConnectionError):
        check.check(instance)

    aggregator.assert_service_check(service_check, AzureIoTEdgeCheck.CRITICAL)
