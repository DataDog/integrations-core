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
    'namespace': 'kubeproxy',
    'metrics': [
        {'kubeproxy_sync_proxy_rules_latency_microseconds': 'sync_rules.latency'},
        {'process_cpu_seconds_total': 'cpu.time'},
        {'process_resident_memory_bytes': 'mem.resident'},
        {'process_virtual_memory_bytes': 'mem.virtual'},
        {'rest_client_requests_total': 'client.http.requests'}
    ],
    'send_histograms_buckets': True
}

# Constants
CHECK_NAME = 'kube_proxy'
NAMESPACE = 'kubeproxy'
METRICS_COMMON = [
    NAMESPACE + '.cpu.time',
    NAMESPACE + '.mem.resident',
    NAMESPACE + '.mem.virtual',
    NAMESPACE + '.client.http.requests'
]
METRICS_IPTABLES = [
    NAMESPACE + '.sync_rules.latency.count',
    NAMESPACE + '.sync_rules.latency.sum'
]

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

    c = KubeProxyCheck('kube_proxy', None, {}, [instance])
    c.check(instance)
    for metric in METRICS_COMMON:
        aggregator.assert_metric(metric, tags=[])
    for metric in METRICS_IPTABLES:
        aggregator.assert_metric(metric, tags=[])

    assert aggregator.metrics_asserted_pct == 100.0


def test_check_userspace(aggregator, mock_userspace):
    """
    Testing Kube_proxy in userspace mode.
    """
    c = KubeProxyCheck('kube_proxy', None, {}, [instance])
    c.check(instance)
    for metric in METRICS_COMMON:
        aggregator.assert_metric(metric, tags=[])

    assert aggregator.metrics_asserted_pct == 100.0
