# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.kube_proxy import KubeProxyCheck

instance = {'prometheus_url': 'http://localhost:10249/metrics'}
instance2 = {'prometheus_url': 'http://localhost:10249/metrics', 'health_url': 'http://1.2.3.4:5678/healthz'}

# Constants
CHECK_NAME = 'kube_proxy'
NAMESPACE = 'kubeproxy'


@pytest.fixture()
def mock_iptables():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics_iptables.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_iptables = mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    )
    yield mock_iptables.start()
    mock_iptables.stop()


@pytest.fixture()
def mock_userspace():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics_userspace.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_userspace = mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    )
    yield mock_userspace.start()
    mock_userspace.stop()


def test_check_iptables(aggregator, mock_iptables):
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


def test_check_userspace(aggregator, mock_userspace):
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


def test_service_check_ok(monkeypatch):
    instance_tags = []

    check = KubeProxyCheck(CHECK_NAME, {}, [instance])

    monkeypatch.setattr(check, 'service_check', mock.Mock())

    calls = [
        mock.call(NAMESPACE + '.up', AgentCheck.OK, tags=instance_tags),
        mock.call(NAMESPACE + '.up', AgentCheck.CRITICAL, tags=instance_tags, message='health check failed'),
    ]

    # successful health check
    with mock.patch("requests.get", return_value=mock.MagicMock(status_code=200)):
        check._perform_service_check(instance)

    # failed health check
    raise_error = mock.Mock()
    raise_error.side_effect = requests.HTTPError('health check failed')
    with mock.patch("requests.get", return_value=mock.MagicMock(raise_for_status=raise_error)):
        check._perform_service_check(instance)

    check.service_check.assert_has_calls(calls)
