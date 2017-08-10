# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys
import os

import mock
import pytest
import json

from datadog_checks.kubelet import KubeletCheck

# Skip the whole tests module on Windows
pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='tests for linux only')

# Constants
HERE = os.path.abspath(os.path.dirname(__file__))
QUANTITIES = {
    '12k': 12 * 1000,
    '12M': 12 * (1000*1000),
    '12Ki': 12. * 1024,
    '12K': 12.,
    '12test': 12.,
}

NODE_SPEC = {
    u'cloud_provider': u'GCE',
    u'instance_type': u'n1-standard-1',
    u'num_cores': 1,
    u'system_uuid': u'5556DC4F-C198-07C8-BE37-ACB98B1BA490',
    u'network_devices': [{u'mtu': 1460, u'speed': 0, u'name': u'eth0', u'mac_address': u'42:01:0a:84:00:04'}],
    u'hugepages': [{u'num_pages': 0, u'page_size': 2048}],
    u'memory_capacity': 3885424640,
    u'instance_id': u'8153046835786593062',
    u'boot_id': u'789bf9ff-77be-4f43-8352-62f84d5e4356',
    u'cpu_frequency_khz': 2600000,
    u'machine_id': u'5556dc4fc19807c8be37acb98b1ba490'
}

EXPECTED_METRICS = [
    'kubernetes.cpu.capacity',
    'kubernetes.cpu.usage.total',
    'kubernetes.cpu.limits',
    'kubernetes.cpu.requests',
    'kubernetes.filesystem.usage',
    'kubernetes.filesystem.usage_pct',
    'kubernetes.memory.capacity',
    'kubernetes.memory.limits',
    'kubernetes.memory.requests',
    'kubernetes.memory.usage',
    'kubernetes.memory.usage_pct',
    'kubernetes.network.rx_bytes',
    'kubernetes.network.rx_dropped',
    'kubernetes.network.rx_errors',
    'kubernetes.network.tx_bytes',
    'kubernetes.network.tx_dropped',
    'kubernetes.network.tx_errors'
]


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


# @pytest.fixture
# def get_tags(entity):
#     return []


def mock_from_file(fname):
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return f.read()


def test_bad_config():
    with pytest.raises(Exception):
        KubeletCheck('kubelet', None, {}, [{}, {}])


def test_default_options():
    check = KubeletCheck('kubelet', None, {}, [{}])
    assert check.NAMESPACE == 'kubernetes'
    assert check.kube_node_labels == {}
    assert check.fs_usage_bytes == {}
    assert check.mem_usage_bytes == {}
    assert check.metrics_mapper == {'kubelet_runtime_operations_errors': 'kubelet.runtime.errors'}


def test_parse_quantity():
    for raw, res in QUANTITIES.iteritems():
        assert KubeletCheck.parse_quantity(raw) == res


@mock.patch.object(KubeletCheck, 'retrieve_pod_list')
def test_kubelet_check(aggregator, monkeypatch):
    check = KubeletCheck('kubelet', None, {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', lambda: json.loads(mock_from_file('pods.txt')))
    monkeypatch.setattr(check, 'retrieve_node_spec', lambda: NODE_SPEC)
    monkeypatch.setattr(check, '_perform_kubelet_check', lambda x: None)
    attrs = {
        'close.return_value': True,
        'iter_lines.return_value': mock_from_file('metrics.txt').split('\n')
    }
    mock_resp = mock.Mock(headers={'Content-Type': 'text/plain'}, **attrs)
    monkeypatch.setattr(check, 'poll', lambda x: mock_resp)
# TODO: implement these in the poll response mock
# 'text/plain' in response.headers['Content-Type']:
# text_fd_to_metric_families(response.iter_lines(chunk_size=self.REQUESTS_CHUNK_SIZE)):
    check.check({})

    check.retrieve_pod_list.assert_called_once()
    check.retrieve_node_spec.assert_called_once()

    check.poll.assert_called_once()
    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)
    assert aggregator.metrics_asserted_pct == 100.0


# def test_is_container_metric():


# def test_is_pod_metric():
# def test_get_container_label():
# def test_get_container_id():
# def test_get_pod_uid():
# def test_is_pod_host_networked():
