# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

import pytest

from datadog_checks.azure_iot_edge import AzureIoTEdgeCheck
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError, HTTPClientReadTimeoutError

from . import common

pytestmark = pytest.mark.unit


def test_hub_and_agent_metrics(dd_run_check, aggregator, mock_instance, fake_http, fake_http_response):
    endpoints = [common.MOCK_EDGE_HUB_PROMETHEUS_URL, common.MOCK_EDGE_AGENT_PROMETHEUS_URL]
    for endpoint, name in zip(endpoints, ['edge_hub.txt', 'edge_agent.txt']):
        content = Path(common.HERE, 'compose', 'mock_server', 'data', 'metrics', name).read_bytes()
        fake_http_response(endpoint, content, headers={'Content-Type': 'text/plain'})
    check = AzureIoTEdgeCheck('azure_iot_edge', {}, [mock_instance])
    dd_run_check(check)
    for metric, metric_type in common.HUB_METRICS:
        aggregator.assert_metric(metric, metric_type=metric_type)
    for metric, metric_type, _ in common.AGENT_METRICS:
        aggregator.assert_metric(metric, metric_type=metric_type)
    aggregator.assert_service_check('azure.iot_edge.edge_hub.prometheus.health', check.OK)
    aggregator.assert_service_check('azure.iot_edge.edge_agent.prometheus.health', check.OK)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint) for endpoint in endpoints]


@pytest.mark.parametrize('error', [HTTPClientConnectionError, HTTPClientReadTimeoutError])
def test_hub_failure_reports_critical(aggregator, mock_instance, fake_http, error):
    endpoint = common.MOCK_EDGE_HUB_PROMETHEUS_URL
    fake_http.register_response('GET', endpoint, error('hub unavailable'))
    check = AzureIoTEdgeCheck('azure_iot_edge', {}, [mock_instance])
    with pytest.raises(error, match='hub unavailable'):
        check.check(mock_instance)
    aggregator.assert_service_check('azure.iot_edge.edge_hub.prometheus.health', check.CRITICAL)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]
