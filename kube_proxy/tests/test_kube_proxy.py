# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest
import mock

# 3p

# project
from datadog_checks.kube_proxy import KubeProxyCheck

instance = {
    'prometheus_url': 'http://localhost:10249/metrics',
}

# Constants
CHECK_NAME = 'kube_proxy'
NAMESPACE = 'kubeproxy'

@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator

@pytest.fixture()
def mock_iptables():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics_iptables.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mock_iptables = mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain"}
        )
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
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain"}
        )
    )
    yield mock_userspace.start()
    mock_userspace.stop()

def test_check_iptables(aggregator, mock_iptables):
    """
    Testing Kube_proxy in iptables mode.
    """

    c = KubeProxyCheck(CHECK_NAME, None, {}, [instance])
    c.check(instance)
    aggregator.assert_metric(NAMESPACE + '.cpu.time')
    aggregator.assert_metric(NAMESPACE + '.mem.resident')
    aggregator.assert_metric(NAMESPACE + '.mem.virtual')
    aggregator.assert_metric(NAMESPACE + '.client.http.requests', tags=['method:GET', 'code:200', 'host:127.0.0.1:8080'])
    aggregator.assert_metric(NAMESPACE + '.client.http.requests', tags=['method:POST', 'code:201', 'host:127.0.0.1:8080'])
    aggregator.assert_metric(NAMESPACE + '.client.http.requests', tags=['method:GET', 'code:404', 'host:127.0.0.1:8080'])
    aggregator.assert_metric(NAMESPACE + '.sync_rules.latency.count')
    aggregator.assert_metric(NAMESPACE + '.sync_rules.latency.sum')
    aggregator.assert_all_metrics_covered()


def test_check_userspace(aggregator, mock_userspace):
    """
    Testing Kube_proxy in userspace mode.
    """
    c = KubeProxyCheck(CHECK_NAME, None, {}, [instance])
    c.check(instance)
    aggregator.assert_metric(NAMESPACE + '.cpu.time')
    aggregator.assert_metric(NAMESPACE + '.mem.resident')
    aggregator.assert_metric(NAMESPACE + '.mem.virtual')
    aggregator.assert_metric(NAMESPACE + '.client.http.requests', tags=['method:GET', 'host:127.0.0.1:8080', 'code:200'])
    aggregator.assert_metric(NAMESPACE + '.client.http.requests', tags=['method:POST', 'host:127.0.0.1:8080', 'code:201'])
    aggregator.assert_metric(NAMESPACE + '.client.http.requests', tags=['method:GET', 'host:127.0.0.1:8080', 'code:200'])
    aggregator.assert_metric(NAMESPACE + '.client.http.requests', tags=['method:POST', 'host:127.0.0.1:8080', 'code:201'])
    aggregator.assert_all_metrics_covered()
