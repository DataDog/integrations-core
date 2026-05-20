# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.kube_proxy import KubeProxyCheck

from .common import make_mock_metrics

instance = {'prometheus_url': 'http://localhost:10249/metrics'}
instance2 = {'prometheus_url': 'http://localhost:10249/metrics', 'health_url': 'http://1.2.3.4:5678/healthz'}

# Constants
CHECK_NAME = 'kube_proxy'
NAMESPACE = 'kubeproxy'


@pytest.fixture()
def mock_iptables(mock_openmetrics_http):
    return make_mock_metrics(mock_openmetrics_http, 'metrics_iptables.txt')


@pytest.fixture()
def mock_userspace(mock_openmetrics_http):
    return make_mock_metrics(mock_openmetrics_http, 'metrics_userspace.txt')


def test_check_iptables(aggregator, mock_iptables, mock_healthcheck_wrapper):
    """
    Testing Kube_proxy in iptables mode.
    """
    c = KubeProxyCheck(CHECK_NAME, {}, [instance])
    c.check(instance)
    aggregator.assert_metric(NAMESPACE + '.cpu.time')
    aggregator.assert_metric(NAMESPACE + '.mem.resident')
    aggregator.assert_metric(NAMESPACE + '.mem.virtual')
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['method:GET', 'code:200', 'host:127.0.0.1:8080']
    )
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['method:POST', 'code:201', 'host:127.0.0.1:8080']
    )
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['method:GET', 'code:404', 'host:127.0.0.1:8080']
    )
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.latency.count')
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.latency.sum')
    aggregator.assert_all_metrics_covered()


def test_check_userspace(aggregator, mock_userspace, mock_healthcheck_wrapper):
    """
    Testing Kube_proxy in userspace mode.
    """
    c = KubeProxyCheck(CHECK_NAME, {}, [instance])
    c.check(instance)
    aggregator.assert_metric(NAMESPACE + '.cpu.time')
    aggregator.assert_metric(NAMESPACE + '.mem.resident')
    aggregator.assert_metric(NAMESPACE + '.mem.virtual')
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['method:GET', 'host:127.0.0.1:8080', 'code:200']
    )
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['method:POST', 'host:127.0.0.1:8080', 'code:201']
    )
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['method:GET', 'host:127.0.0.1:8080', 'code:200']
    )
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['method:POST', 'host:127.0.0.1:8080', 'code:201']
    )
    aggregator.assert_all_metrics_covered()


def test_service_check_default_url():
    c = KubeProxyCheck(CHECK_NAME, {}, [instance])
    assert c.instance['health_url'] == 'http://localhost:10256/healthz'


def test_service_check_custom_url():
    c = KubeProxyCheck(CHECK_NAME, {}, [instance2])
    assert c.instance['health_url'] == 'http://1.2.3.4:5678/healthz'


@pytest.mark.parametrize(
    'side_effect, expected_status, expected_message',
    [
        (None, AgentCheck.OK, None),
        (requests.HTTPError('health check failed'), AgentCheck.CRITICAL, 'health check failed'),
    ],
    ids=['ok', 'http_error'],
)
def test_service_check(monkeypatch, side_effect, expected_status, expected_message):
    instance_tags = []
    check = KubeProxyCheck(CHECK_NAME, {}, [instance])
    monkeypatch.setattr(check, 'service_check', mock.Mock())

    healthcheck_url = check.instance['health_url']
    handler = mock.MagicMock()
    handler.get.return_value.raise_for_status = mock.Mock(side_effect=side_effect)
    check._http_handlers[healthcheck_url] = handler

    check._perform_service_check(instance)

    if expected_message is None:
        check.service_check.assert_called_with(NAMESPACE + '.up', expected_status, tags=instance_tags)
    else:
        check.service_check.assert_called_with(
            NAMESPACE + '.up', expected_status, tags=instance_tags, message=expected_message
        )
