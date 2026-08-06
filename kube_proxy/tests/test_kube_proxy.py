# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPConnectionError, HTTPStatusError
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
    'side_effect, expected_status, extra_kwargs',
    [
        (None, AgentCheck.OK, {}),
        (HTTPStatusError('health check failed'), AgentCheck.CRITICAL, {'message': 'health check failed'}),
        (HTTPConnectionError('connection refused'), AgentCheck.CRITICAL, {'message': 'connection refused'}),
    ],
    ids=['ok', 'http_error', 'http_connection_error'],
)
def test_service_check(monkeypatch, side_effect, expected_status, extra_kwargs):
    instance_tags = []
    check = KubeProxyCheck(CHECK_NAME, {}, [instance])
    monkeypatch.setattr(check, 'service_check', mock.Mock())

    healthcheck_url = check.instance['health_url']
    handler = mock.MagicMock()
    handler.get.return_value.raise_for_status = mock.Mock(side_effect=side_effect)
    check._http_handlers[healthcheck_url] = handler

    check._perform_service_check(instance)

    check.service_check.assert_called_with(NAMESPACE + '.up', expected_status, tags=instance_tags, **extra_kwargs)


@pytest.mark.parametrize(
    ('instance_overrides', 'expected_verify', 'expected_ignore_warning'),
    [
        pytest.param({}, False, True, id='no ca cert'),
        pytest.param({'ssl_ca_cert': '/etc/ca.crt'}, '/etc/ca.crt', False, id='ca cert configured'),
    ],
)
def test_healthcheck_client_carries_instance_tls_config(instance_overrides, expected_verify, expected_ignore_warning):
    """The healthcheck builds its own client, so the instance TLS settings have to reach it.

    With no CA certificate configured it falls back to an unverified connection with the warning
    suppressed, which is what an endpoint serving a self-signed certificate depends on.
    """
    check = KubeProxyCheck(CHECK_NAME, {}, [{**instance, **instance_overrides}])
    health_url = check.instance['health_url']

    handler = check._healthcheck_http_handler(check.instance, health_url)

    assert handler.options['verify'] == expected_verify
    assert handler.ignore_tls_warning is expected_ignore_warning
    # Cached per endpoint, so repeated healthchecks reuse one client rather than building each time.
    assert check._healthcheck_http_handler(check.instance, health_url) is handler
