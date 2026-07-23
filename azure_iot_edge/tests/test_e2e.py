# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import ssl
import urllib.error
from typing import Callable  # noqa: F401

import pytest

from datadog_checks.azure_iot_edge import AzureIoTEdgeCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.utils.http_exceptions import HTTPSSLError

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


@pytest.mark.e2e
def test_bad_url_e2e(e2e_instance, dd_agent_check):
    """
    When giving a wrong url to `edge_hub_prometheus_url`, the redirection might cause SSL exception
    Example: http://localhost:9601/metri -> https://localhost/metri
    """
    bad_url_hub_instance = copy.deepcopy(e2e_instance)
    bad_url_hub_instance['edge_hub_prometheus_url'] = bad_url_hub_instance['edge_hub_prometheus_url'][:-2]

    bad_url_agent_instance = copy.deepcopy(e2e_instance)
    bad_url_agent_instance['edge_agent_prometheus_url'] = bad_url_hub_instance['edge_agent_prometheus_url'][:-2]

    with pytest.raises((HTTPSSLError, urllib.error.URLError)) as exc_info:
        dd_agent_check(bad_url_hub_instance, rate=True)
    if isinstance(exc_info.value, urllib.error.URLError):
        assert isinstance(exc_info.value.reason, ssl.SSLError)

    aggregator = dd_agent_check(bad_url_agent_instance, rate=True)
    aggregator.assert_service_check('azure.iot_edge.edge_agent.prometheus.health', AzureIoTEdgeCheck.CRITICAL)
    aggregator.assert_service_check('azure.iot_edge.edge_hub.prometheus.health', AzureIoTEdgeCheck.OK)
