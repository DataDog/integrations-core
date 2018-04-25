# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import sys
from collections import namedtuple

import mock
import pytest
from datadog_checks.kubelet import KubeletCheck

# Skip the whole tests module on Windows
pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='tests for linux only')

# Constants
HERE = os.path.abspath(os.path.dirname(__file__))
QUANTITIES = {
    '12k': 12 * 1000,
    '12M': 12 * (1000 * 1000),
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

EXPECTED_METRICS_COMMON = [
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
    'kubernetes.network.rx_bytes',
    'kubernetes.network.tx_bytes'
]

EXPECTED_METRICS_PROMETHEUS = [
    'kubernetes.memory.usage_pct',
    'kubernetes.network.rx_dropped',
    'kubernetes.network.rx_errors',
    'kubernetes.network.tx_dropped',
    'kubernetes.network.tx_errors',
    'kubernetes.io.write_bytes',
    'kubernetes.io.read_bytes'
]

Label = namedtuple('Label', 'name value')


class MockMetric(object):
    def __init__(self, name, labels=None, value=None):
        self.name = name
        self.label = labels if labels else []
        self.value = value


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


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


def test_kubelet_check_prometheus(monkeypatch, aggregator):
    check = KubeletCheck('kubelet', None, {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods.json'))))
    monkeypatch.setattr(check, '_retrieve_node_spec', mock.Mock(return_value=NODE_SPEC))
    monkeypatch.setattr(check, '_perform_kubelet_check', mock.Mock(return_value=None))
    monkeypatch.setattr(check, 'process_cadvisor', mock.Mock(return_value=None))

    attrs = {
        'close.return_value': True,
        'iter_lines.return_value': mock_from_file('metrics.txt').split('\n')
    }
    mock_resp = mock.Mock(headers={'Content-Type': 'text/plain'}, **attrs)
    monkeypatch.setattr(check, 'poll', mock.Mock(return_value=mock_resp))

    check.check({})

    assert check.cadvisor_legacy_url is None
    check.retrieve_pod_list.assert_called_once()
    check._retrieve_node_spec.assert_called_once()
    check._perform_kubelet_check.assert_called_once()
    check.poll.assert_called_once()
    check.process_cadvisor.assert_not_called()

    # called twice so pct metrics are guaranteed to be there
    check.check({})
    for metric in EXPECTED_METRICS_COMMON:
        aggregator.assert_metric(metric)
    for metric in EXPECTED_METRICS_PROMETHEUS:
        aggregator.assert_metric(metric)
    assert aggregator.metrics_asserted_pct == 100.0


def test_kubelet_check_neither(monkeypatch, aggregator):
    check = KubeletCheck('kubelet', None, {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods.json'))))
    monkeypatch.setattr(check, '_retrieve_node_spec', mock.Mock(return_value=NODE_SPEC))
    monkeypatch.setattr(check, '_perform_kubelet_check', mock.Mock(return_value=None))

    monkeypatch.setattr(check, 'process', mock.Mock(return_value=None))
    monkeypatch.setattr(check, 'process_cadvisor', mock.Mock(return_value=None))

    check.check({"cadvisor_port": 0, "metrics_endpoint": ""})

    assert check.cadvisor_legacy_url is None
    check.retrieve_pod_list.assert_called_once()
    check._retrieve_node_spec.assert_called_once()
    check._perform_kubelet_check.assert_called_once()
    check.process_cadvisor.assert_not_called()
    check.process.assert_not_called()


def test_is_container_metric():
    false_metrics = [
        MockMetric('foo', []),
        MockMetric(
            'bar',
            [
                Label(name='container_name', value='POD'),  # POD --> False
                Label(name='namespace', value='default'),
                Label(name='pod_name', value='pod0'),
                Label(name='name', value='foo'),
                Label(name='image', value='foo'),
                Label(name='id', value='deadbeef'),
            ]
        ),
        MockMetric(  # missing container_name
            'foobar',
            [
                Label(name='namespace', value='default'),
                Label(name='pod_name', value='pod0'),
                Label(name='name', value='foo'),
                Label(name='image', value='foo'),
                Label(name='id', value='deadbeef'),
            ]
        ),
    ]
    for metric in false_metrics:
        assert KubeletCheck._is_container_metric(metric) is False

    true_metric = MockMetric(
        'foo',
        [
            Label(name='container_name', value='ctr0'),
            Label(name='namespace', value='default'),
            Label(name='pod_name', value='pod0'),
            Label(name='name', value='foo'),
            Label(name='image', value='foo'),
            Label(name='id', value='deadbeef'),
        ]
    )
    assert KubeletCheck._is_container_metric(true_metric) is True


def test_is_pod_metric():
    false_metrics = [
        MockMetric('foo', []),
        MockMetric('bar', [Label(name='container_name', value='ctr0')]),
        MockMetric('foobar', [Label(name='container_name', value='ctr0'), Label(name='id', value='deadbeef')]),
    ]

    true_metrics = [
        MockMetric('foo', [Label(name='container_name', value='POD')]),
        MockMetric('bar', [Label(name='id', value='/kubepods/burstable/pod531c80d9-9fc4-11e7-ba8b-42010af002bb')]),
        MockMetric('foobar', [
            Label(name='container_name', value='POD'),
            Label(name='id', value='/kubepods/burstable/pod531c80d9-9fc4-11e7-ba8b-42010af002bb')]),
    ]

    for metric in false_metrics:
        assert KubeletCheck._is_pod_metric(metric) is False

    for metric in true_metrics:
        assert KubeletCheck._is_pod_metric(metric) is True


def test_get_container_label():
    labels = [
        Label("container_name", value="POD"),
        Label("id", value="/kubepods/burstable/pod531c80d9-9fc4-11e7-ba8b-42010af002bb"),
    ]
    assert KubeletCheck._get_container_label(labels, "container_name") == "POD"
    assert KubeletCheck._get_container_label([], "not-in") is None


def test_get_container_id():
    labels = [
        Label("container_name", value="datadog-agent"),
        Label("id",
              value="/kubepods/burstable/"
                    "podc2319815-10d0-11e8-bd5a-42010af00137/"
                    "a335589109ce5506aa69ba7481fc3e6c943abd23c5277016c92dac15d0f40479"),
    ]
    assert KubeletCheck._get_container_id(labels) == "a335589109ce5506aa69ba7481fc3e6c943abd23c5277016c92dac15d0f40479"
    assert KubeletCheck._get_container_id([]) is None


def test_get_pod_uid():
    labels = [
        Label("container_name", value="POD"),
        Label("id",
              value="/kubepods/burstable/"
                    "pod260c2b1d43b094af6d6b4ccba082c2db/"
                    "0bce0ef7e6cd073e8f9cec3027e1c0057ce1baddce98113d742b816726a95ab1"),
    ]
    assert KubeletCheck._get_pod_uid(labels) == "260c2b1d43b094af6d6b4ccba082c2db"
    assert KubeletCheck._get_pod_uid([]) is None


def test_is_pod_host_networked(monkeypatch):
    check = KubeletCheck('kubelet', None, {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods.json'))))
    check.pod_list = check.retrieve_pod_list()

    assert len(check.pod_list) == 4
    assert check._is_pod_host_networked("not-here") is False
    assert check._is_pod_host_networked('260c2b1d43b094af6d6b4ccba082c2db') is True
    assert check._is_pod_host_networked('2edfd4d9-10ce-11e8-bd5a-42010af00137') is False


def test_get_pod_by_metric_label(monkeypatch):
    check = KubeletCheck('kubelet', None, {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods.json'))))
    check.pod_list = check.retrieve_pod_list()

    assert len(check.pod_list) == 4
    kube_proxy = check._get_pod_by_metric_label([
        Label("container_name", value="POD"),
        Label("id",
              value="/kubepods/burstable/"
                    "pod260c2b1d43b094af6d6b4ccba082c2db/"
                    "0bce0ef7e6cd073e8f9cec3027e1c0057ce1baddce98113d742b816726a95ab1"),
    ])
    fluentd = check._get_pod_by_metric_label([
        Label("container_name", value="POD"),
        Label("id",
              value="/kubepods/burstable/"
                    "pod2edfd4d9-10ce-11e8-bd5a-42010af00137/"
                    "7990c0e549a1a578b1313475540afc53c91081c32e735564da6244ddf0b86030"),
    ])
    assert kube_proxy["metadata"]["name"] == "kube-proxy-gke-haissam-default-pool-be5066f1-wnvn"
    assert fluentd["metadata"]["name"] == "fluentd-gcp-v2.0.10-9q9t4"


def test_get_kube_container_name():
    tags = KubeletCheck._get_kube_container_name([
        Label("container_name", value="datadog-agent"),
        Label("id",
              value="/kubepods/burstable/"
                    "podc2319815-10d0-11e8-bd5a-42010af00137/"
                    "a335589109ce5506aa69ba7481fc3e6c943abd23c5277016c92dac15d0f40479"),
        Label("image",
              value="datadog/agent-dev@sha256:894fb66f89be0332a47388d7219ab8b365520ff0e3bbf597bd0a378b19efa7ee"),
        Label("name", value="k8s_datadog-agent_datadog-agent-jbm2k_default_c2319815-10d0-11e8-bd5a-42010af00137_0"),
        Label("namespace", value="default"),
        Label("pod_name", value="datadog-agent-jbm2k"),
    ])
    assert tags == ["kube_container_name:datadog-agent"]

    tags = KubeletCheck._get_kube_container_name([])
    assert tags == []


def mocked_get_tags(entity, _):
    tag_store = {
        "kubernetes_pod://2edfd4d9-10ce-11e8-bd5a-42010af00137": [
            "pod_name:fluentd-gcp-v2.0.10-9q9t4"
        ],
        'docker://5741ed2471c0e458b6b95db40ba05d1a5ee168256638a0264f08703e48d76561': [
            'fluentd-gcp-v2.0.10-9q9t4'
        ]
    }
    return tag_store.get(entity, [])


def test_report_pods_running(monkeypatch):
    check = KubeletCheck('kubelet', None, {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods.json'))))
    monkeypatch.setattr(check, 'gauge', mock.Mock())
    pod_list = check.retrieve_pod_list()

    with mock.patch("datadog_checks.kubelet.kubelet.get_tags", side_effect=mocked_get_tags):
        check._report_pods_running(pod_list, [])

    calls = [mock.call('kubernetes.pods.running', 1, ["pod_name:fluentd-gcp-v2.0.10-9q9t4"])]
    check.gauge.assert_has_calls(calls, any_order=True)


def test_report_container_spec_metrics(monkeypatch):
    check = KubeletCheck('kubelet', None, {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods.json'))))
    monkeypatch.setattr(check, 'gauge', mock.Mock())
    pod_list = check.retrieve_pod_list()

    instance_tags = ["one:1", "two:2"]
    with mock.patch("datadog_checks.kubelet.kubelet.get_tags", side_effect=mocked_get_tags):
        check._report_container_spec_metrics(pod_list, instance_tags)

    calls = [
        mock.call('kubernetes.cpu.requests', 0.1, ['fluentd-gcp-v2.0.10-9q9t4'] + instance_tags),
        mock.call('kubernetes.memory.requests', 209715200.0, ['fluentd-gcp-v2.0.10-9q9t4'] + instance_tags),
        mock.call('kubernetes.memory.limits', 314572800.0, ['fluentd-gcp-v2.0.10-9q9t4'] + instance_tags),
        mock.call('kubernetes.cpu.requests', 0.1, instance_tags),
        mock.call('kubernetes.cpu.requests', 0.1, instance_tags),
        mock.call('kubernetes.memory.requests', 134217728.0, instance_tags),
        mock.call('kubernetes.cpu.limits', 0.25, instance_tags),
        mock.call('kubernetes.memory.limits', 536870912.0, instance_tags),
        mock.call('kubernetes.cpu.requests', 0.1, instance_tags),
    ]
    check.gauge.assert_has_calls(calls, any_order=True)


class MockResponse(mock.Mock):
    @staticmethod
    def iter_lines():
        return []


def test_perform_kubelet_check(monkeypatch):
    check = KubeletCheck('kubelet', None, {}, [{}])
    check.kube_health_url = "http://127.0.0.1:10255/healthz"
    check.kubelet_conn_info = {}
    monkeypatch.setattr(check, 'service_check', mock.Mock())

    instance_tags = ["one:1"]
    get = MockResponse()
    with mock.patch("requests.get", side_effect=get):
        check._perform_kubelet_check(instance_tags)

    get.assert_has_calls([
        mock.call('http://127.0.0.1:10255/healthz', cert=None, headers=None, params={'verbose': True}, timeout=10,
                  verify=None)])
    calls = [mock.call('kubernetes.kubelet.check', 0, tags=instance_tags)]
    check.service_check.assert_has_calls(calls)


def test_report_node_metrics(monkeypatch):
    check = KubeletCheck('kubelet', None, {}, [{}])
    monkeypatch.setattr(check, '_retrieve_node_spec', mock.Mock(return_value={'num_cores': 4, 'memory_capacity': 512}))
    monkeypatch.setattr(check, 'gauge', mock.Mock())
    check._report_node_metrics(['foo:bar'])
    calls = [
        mock.call('kubernetes.cpu.capacity', 4.0, ['foo:bar']),
        mock.call('kubernetes.memory.capacity', 512.0, ['foo:bar'])
    ]
    check.gauge.assert_has_calls(calls, any_order=False)
