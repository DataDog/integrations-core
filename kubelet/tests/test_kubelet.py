# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import os
import sys
from collections import defaultdict

import mock
import pytest
import requests
import requests_mock
from six import iteritems

from datadog_checks.base.checks.kubelet_base.base import KubeletCredentials
from datadog_checks.base.utils.date import parse_rfc3339
from datadog_checks.dev.http import MockResponse
from datadog_checks.kubelet import KubeletCheck, PodListUtils

# Skip the whole tests module on Windows
pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='tests for linux only')

# Constants
HERE = os.path.abspath(os.path.dirname(__file__))
QUANTITIES = {'12k': 12 * 1000, '12M': 12 * (1000 * 1000), '12Ki': 12.0 * 1024, '12K': 12.0, '12test': 12.0}

# Kubernetes versions, used to differentiate cadvisor payloads after the label change
KUBE_POST_1_16 = '1.16'
KUBE_1_14 = '1.14'
KUBE_PRE_1_14 = '1.13'
KUBE_1_21 = '1.21'

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
    u'machine_id': u'5556dc4fc19807c8be37acb98b1ba490',
}

EXPECTED_METRICS_COMMON = [
    'kubernetes.pods.running',
    'kubernetes.containers.running',
    'kubernetes.containers.restarts',
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
    'kubernetes.memory.working_set',
    'kubernetes.memory.cache',
    'kubernetes.memory.rss',
    'kubernetes.memory.swap',
    'kubernetes.network.rx_bytes',
    'kubernetes.network.tx_bytes',
    'kubernetes.ephemeral_storage.usage',
    'kubernetes.runtime.cpu.usage',
    'kubernetes.runtime.memory.usage',
    'kubernetes.runtime.memory.rss',
    'kubernetes.kubelet.cpu.usage',
    'kubernetes.kubelet.memory.usage',
    'kubernetes.kubelet.memory.rss',
]

EXPECTED_METRICS_PROMETHEUS = [
    'kubernetes.cpu.load.10s.avg',
    'kubernetes.cpu.system.total',
    'kubernetes.cpu.user.total',
    'kubernetes.cpu.cfs.periods',
    'kubernetes.cpu.cfs.throttled.periods',
    'kubernetes.cpu.cfs.throttled.seconds',
    'kubernetes.memory.usage_pct',
    'kubernetes.memory.sw_limit',
    'kubernetes.network.rx_dropped',
    'kubernetes.network.rx_errors',
    'kubernetes.network.tx_dropped',
    'kubernetes.network.tx_errors',
    'kubernetes.io.write_bytes',
    'kubernetes.io.read_bytes',
    'kubernetes.apiserver.certificate.expiration.count',
    'kubernetes.apiserver.certificate.expiration.sum',
    'kubernetes.rest.client.requests',
    'kubernetes.rest.client.latency.count',
    'kubernetes.rest.client.latency.sum',
    'kubernetes.kubelet.runtime.operations',
    'kubernetes.kubelet.runtime.errors',
    'kubernetes.kubelet.runtime.operations.duration.sum',
    'kubernetes.kubelet.runtime.operations.duration.count',
    'kubernetes.kubelet.runtime.operations.duration.quantile',
    'kubernetes.kubelet.docker.operations',
    'kubernetes.kubelet.docker.errors',
    'kubernetes.kubelet.docker.operations.duration.sum',
    'kubernetes.kubelet.docker.operations.duration.count',
    'kubernetes.kubelet.docker.operations.duration.quantile',
    'kubernetes.kubelet.network_plugin.latency.sum',
    'kubernetes.kubelet.network_plugin.latency.count',
    'kubernetes.kubelet.volume.stats.available_bytes',
    'kubernetes.kubelet.volume.stats.capacity_bytes',
    'kubernetes.kubelet.volume.stats.used_bytes',
    'kubernetes.kubelet.volume.stats.inodes',
    'kubernetes.kubelet.volume.stats.inodes_free',
    'kubernetes.kubelet.volume.stats.inodes_used',
    'kubernetes.kubelet.evictions',
    'kubernetes.kubelet.pod.start.duration.sum',
    'kubernetes.kubelet.pod.start.duration.count',
    'kubernetes.kubelet.pod.worker.start.duration.sum',
    'kubernetes.kubelet.pod.worker.start.duration.count',
    'kubernetes.go_threads',
    'kubernetes.go_goroutines',
]

EXPECTED_METRICS_PROMETHEUS_1_14 = EXPECTED_METRICS_PROMETHEUS + [
    'kubernetes.kubelet.container.log_filesystem.used_bytes',
    'kubernetes.kubelet.pod.worker.duration.sum',
    'kubernetes.kubelet.pod.worker.duration.count',
    'kubernetes.kubelet.pleg.relist_duration.count',
    'kubernetes.kubelet.pleg.relist_duration.sum',
    'kubernetes.kubelet.pleg.relist_interval.count',
    'kubernetes.kubelet.pleg.relist_interval.sum',
]

EXPECTED_METRICS_PROMETHEUS_PRE_1_14 = EXPECTED_METRICS_PROMETHEUS + [
    'kubernetes.kubelet.network_plugin.latency.quantile',
    'kubernetes.kubelet.pod.start.duration.quantile',
    'kubernetes.kubelet.pod.worker.start.duration.quantile',
]

EXPECTED_METRICS_PROMETHEUS_1_21 = [
    'kubernetes.apiserver.certificate.expiration.count',
    'kubernetes.apiserver.certificate.expiration.sum',
    'kubernetes.containers.restarts',
    'kubernetes.containers.running',
    'kubernetes.cpu.capacity',
    'kubernetes.cpu.limits',
    'kubernetes.cpu.requests',
    'kubernetes.ephemeral_storage.usage',
    'kubernetes.go_goroutines',
    'kubernetes.go_threads',
    'kubernetes.kubelet.container.log_filesystem.used_bytes',
    'kubernetes.kubelet.cpu.usage',
    'kubernetes.kubelet.memory.usage',
    'kubernetes.kubelet.memory.rss',
    'kubernetes.kubelet.network_plugin.latency.count',
    'kubernetes.kubelet.network_plugin.latency.sum',
    'kubernetes.kubelet.pleg.discard_events',
    'kubernetes.kubelet.pleg.last_seen',
    'kubernetes.kubelet.pleg.relist_duration.count',
    'kubernetes.kubelet.pleg.relist_duration.sum',
    'kubernetes.kubelet.pleg.relist_interval.count',
    'kubernetes.kubelet.pleg.relist_interval.sum',
    'kubernetes.kubelet.pod.start.duration.count',
    'kubernetes.kubelet.pod.start.duration.sum',
    'kubernetes.kubelet.pod.worker.start.duration.count',
    'kubernetes.kubelet.pod.worker.start.duration.sum',
    'kubernetes.kubelet.runtime.errors',
    'kubernetes.kubelet.runtime.operations',
    'kubernetes.kubelet.runtime.operations.duration.count',
    'kubernetes.kubelet.runtime.operations.duration.sum',
    'kubernetes.memory.capacity',
    'kubernetes.memory.limits',
    'kubernetes.memory.requests',
    'kubernetes.pods.running',
    'kubernetes.rest.client.latency.count',
    'kubernetes.rest.client.latency.sum',
    'kubernetes.rest.client.requests',
    'kubernetes.runtime.cpu.usage',
    'kubernetes.runtime.memory.usage',
    'kubernetes.runtime.memory.rss',
]

COMMON_TAGS = {
    "kubernetes_pod_uid://c2319815-10d0-11e8-bd5a-42010af00137": ["pod_name:datadog-agent-jbm2k"],
    "kubernetes_pod_uid://2edfd4d9-10ce-11e8-bd5a-42010af00137": ["pod_name:fluentd-gcp-v2.0.10-9q9t4"],
    "kubernetes_pod_uid://2fdfd4d9-10ce-11e8-bd5a-42010af00137": ["pod_name:fluentd-gcp-v2.0.10-p13r3"],
    'container_id://5741ed2471c0e458b6b95db40ba05d1a5ee168256638a0264f08703e48d76561': [
        'kube_container_name:fluentd-gcp',
        'kube_deployment:fluentd-gcp-v2.0.10',
    ],
    "container_id://580cb469826a10317fd63cc780441920f49913ae63918d4c7b19a72347645b05": [
        'kube_container_name:prometheus-to-sd-exporter',
        'kube_deployment:fluentd-gcp-v2.0.10',
    ],
    'container_id://6941ed2471c0e458b6b95db40ba05d1a5ee168256638a0264f08703e48d76561': [
        'kube_container_name:fluentd-gcp',
        'kube_deployment:fluentd-gcp-v2.0.10',
    ],
    "container_id://690cb469826a10317fd63cc780441920f49913ae63918d4c7b19a72347645b05": [
        'kube_container_name:prometheus-to-sd-exporter',
        'kube_deployment:fluentd-gcp-v2.0.10',
    ],
    "container_id://5f93d91c7aee0230f77fbe9ec642dd60958f5098e76de270a933285c24dfdc6f": [
        "pod_name:demo-app-success-c485bc67b-klj45"
    ],
    "kubernetes_pod_uid://d2e71e36-10d0-11e8-bd5a-42010af00137": ['pod_name:dd-agent-q6hpw'],
    "kubernetes_pod_uid://260c2b1d43b094af6d6b4ccba082c2db": [
        'pod_name:kube-proxy-gke-haissam-default-pool-be5066f1-wnvn'
    ],
    "kubernetes_pod_uid://24d6daa3-10d8-11e8-bd5a-42010af00137": ['pod_name:demo-app-success-c485bc67b-klj45'],
    "container_id://f69aa93ce78ee11e78e7c75dc71f535567961740a308422dafebdb4030b04903": ['pod_name:pi-kff76'],
    "kubernetes_pod_uid://12ceeaa9-33ca-11e6-ac8f-42010af00003": ['pod_name:dd-agent-ntepl'],
    "container_id://32fc50ecfe24df055f6d56037acb966337eef7282ad5c203a1be58f2dd2fe743": ['pod_name:dd-agent-ntepl'],
    "container_id://a335589109ce5506aa69ba7481fc3e6c943abd23c5277016c92dac15d0f40479": [
        'kube_container_name:datadog-agent'
    ],
    "container_id://326b384481ca95204018e3e837c61e522b64a3b86c3804142a22b2d1db9dbd7b": [
        'kube_container_name:datadog-agent'
    ],
    "container_id://6d8c6a05731b52195998c438fdca271b967b171f6c894f11ba59aa2f4deff10c": ['pod_name:cassandra-0'],
    "kubernetes_pod_uid://639980e5-2e6c-11ea-8bb1-42010a800074": [
        'kube_namespace:default',
        'kube_service:nginx',
        'kube_stateful_set:web',
        'namespace:default',
        'persistentvolumeclaim:www-web-2',
        'pod_phase:running',
    ],
    "kubernetes_pod_uid://639980e5-2e6c-11ea-8bb1-42010a800075": [
        'kube_namespace:default',
        'kube_service:nginx',
        'kube_stateful_set:web',
        'namespace:default',
        'persistentvolumeclaim:www-web-2',
        'persistentvolumeclaim:www2-web-3',
        'pod_phase:running',
    ],
}

WINDOWS_TAGS = {
    'kubernetes_pod_uid://4740a3ec-392f-435f-80a4-b407a37463db': [
        'kube_namespace:default',
        'pod_name:windows-server-iis-6c68545d57-gwtn9',
    ],
    'container_id://43dfa29d17d358cbdd0bfb290cf27ce82c4de0c88d22d7cac4b88c85de87efba': [
        'kube_namespace:default',
        'pod_name:windows-server-iis-6c68545d57-gwtn9',
        'kube_container_name:windows-server-iis',
    ],
    'kubernetes_pod_uid://8ddf0e3f-ac6c-4d44-87d7-0bc41f6729ec': [
        'kube_namespace:default',
        'pod_name:dd-datadog-lbvkl',
    ],
    'container_id://a26b9c2c92e4ab03f34b84d03d91bed92259c859576535a3167aa32d39206dc2': [
        'kube_namespace:default',
        'pod_name:dd-datadog-lbvkl',
        'kube_container_name:agent',
    ],
    'container_id://98fb504eb0fab22ce9089d8b1cc172ccb2095ee11a00bacd244419b5c02ee635': [
        'kube_namespace:default',
        'pod_name:dd-datadog-lbvkl',
        'kube_container_name:process-agent',
    ],
}

PROBE_TAGS = {
    'container_id://2c3f5608164033a850c9acbbfdb7fffa6ce1f68feedb1b8dad99777373c35b16': [
        'kube_namespace:kube-system',
        'pod_name:kube-dns-c598bd956-wgf4n',
        'kube_container_name:sidecar',
    ],
    'container_id://b13f7638c80c98946900bdeabec06be564d203330f5bb706a40e6fa7466a674d': [
        'kube_namespace:kube-system',
        'pod_name:kube-dns-c598bd956-wgf4n',
        'kube_container_name:kubedns',
    ],
    'container_id://3102f0d9499c5cd0875225208e3d048e3a9d829f5cdd74758b2d79a429a579fa': [
        'kube_namespace:kube-system',
        'pod_name:fluentbit-gke-45gvm',
        'kube_container_name:fluentbit-gke',
    ],
    'container_id://efa5b57cc110de6d2ca3b4a0e12c0a378090530e5e2d0ba0882dffe9c5846067': [
        'kube_namespace:kube-system',
        'pod_name:fluentbit-gke-45gvm',
        'kube_container_name:fluentbit',
    ],
    'container_id://0d8eea0b23688a4c3fbc29828b455734b323d6aac085c88f8f112e296cd5b521': [
        'kube_namespace:kube-system',
        'pod_name:kube-dns-c598bd956-wgf4n',
        'kube_container_name:dnsmasq',
    ],
    'container_id://1669a6277ebb44aedd2790ba8bce83d21899ba85b1afde4330caf4a4161eee26': [
        'kube_namespace:kube-system',
        'pod_name:calico-node-9qkw7',
        'kube_container_name:calico-node',
    ],
    'container_id://c81dfc25dd24b538a880bfd0f807ba9ec1ff4541e8b8eb49a8d1afcdecc5ef59': [
        'kube_namespace:default',
        'pod_name:datadog-t9f28',
        'kube_container_name:agent',
    ],
}

METRICS_WITH_DEVICE_TAG = {
    'kubernetes.filesystem.usage': '/dev/sda1',
    'kubernetes.io.read_bytes': '/dev/sda',
    'kubernetes.io.write_bytes': '/dev/sda',
}

METRICS_WITH_INTERFACE_TAG = {
    'kubernetes.network.rx_bytes': 'eth0',
    'kubernetes.network.tx_bytes': 'eth0',
    'kubernetes.network.rx_errors': 'eth0',
    'kubernetes.network.tx_errors': 'eth0',
    'kubernetes.network.rx_dropped': 'eth0',
    'kubernetes.network.tx_dropped': 'eth0',
}


@pytest.fixture
def tagger():
    from datadog_checks.base.stubs import tagger

    tagger.reset()
    tagger.set_tags(COMMON_TAGS)
    return tagger


def mock_kubelet_check(
    monkeypatch,
    instances,
    kube_version=KUBE_1_14,
    stats_summary_fail=False,
    pod_list='pods.json',
    probes_available=None,
):
    """
    Returns a check that uses mocked data for responses from prometheus endpoints, pod list,
    and node spec.
    """
    check = KubeletCheck('kubelet', {}, instances)
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file(pod_list))))
    mock_resp = mock.Mock(status_code=200, raise_for_status=mock.Mock(), json=mock.Mock(return_value=NODE_SPEC))
    monkeypatch.setattr(check, '_retrieve_node_spec', mock.Mock(return_value=mock_resp))
    if stats_summary_fail:
        monkeypatch.setattr(check, '_retrieve_stats', mock.Mock(return_value={}))
    else:
        monkeypatch.setattr(
            check, '_retrieve_stats', mock.Mock(return_value=json.loads(mock_from_file('stats_summary.json')))
        )
    monkeypatch.setattr(check, '_perform_kubelet_check', mock.Mock(return_value=None))
    monkeypatch.setattr(check, 'compute_pod_expiration_datetime', mock.Mock(return_value=None))
    if probes_available:
        monkeypatch.setattr(check, '_probes_available', mock.Mock(return_value=True))

    def mocked_poll(cadvisor_response, kubelet_response):
        def _mocked_poll(*args, **kwargs):
            scraper_config = args[0]
            prometheus_url = scraper_config['prometheus_url']

            if prometheus_url.endswith('/metrics/cadvisor'):
                # Mock response for "/metrics/cadvisor"
                content = mock_from_file(cadvisor_response)
            elif prometheus_url.endswith('/metrics'):
                # Mock response for "/metrics"
                content = mock_from_file(kubelet_response)
            elif prometheus_url.endswith('/metrics/probes'):
                # Mock response for "/metrics/probes"
                content = mock_from_file('probes.txt')
            else:
                raise Exception("Must be a valid endpoint")

            attrs = {'close.return_value': True, 'iter_lines.return_value': content.split('\n'), 'content': content}
            return mock.Mock(headers={'Content-Type': 'text/plain'}, **attrs)

        return _mocked_poll

    if kube_version == KUBE_POST_1_16:
        monkeypatch.setattr(
            check,
            'poll',
            mock.Mock(
                side_effect=mocked_poll(
                    cadvisor_response='cadvisor_metrics_post_1_16.txt', kubelet_response='kubelet_metrics_1_14.txt'
                )
            ),
        )
    elif kube_version == KUBE_1_14:
        monkeypatch.setattr(
            check,
            'poll',
            mock.Mock(
                side_effect=mocked_poll(
                    cadvisor_response='cadvisor_metrics_pre_1_16.txt', kubelet_response='kubelet_metrics_1_14.txt'
                )
            ),
        )
    elif kube_version == KUBE_PRE_1_14:
        monkeypatch.setattr(
            check,
            'poll',
            mock.Mock(
                side_effect=mocked_poll(
                    cadvisor_response='cadvisor_metrics_pre_1_16.txt', kubelet_response='kubelet_metrics.txt'
                )
            ),
        )
    elif kube_version == KUBE_1_21:
        monkeypatch.setattr(
            check,
            'poll',
            mock.Mock(
                side_effect=mocked_poll(
                    cadvisor_response='cadvisor_metrics_1_21.txt', kubelet_response='kubelet_metrics_1_21.txt'
                )
            ),
        )

    return check


def mock_from_file(fname):
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return f.read()


def test_bad_config():
    with pytest.raises(Exception):
        KubeletCheck('kubelet', {}, [{}, {}])


def test_parse_quantity():
    for raw, res in iteritems(QUANTITIES):
        assert KubeletCheck.parse_quantity(raw) == res


def test_kubelet_default_options():
    check = KubeletCheck('kubelet', {}, [{}])
    assert check.cadvisor_scraper_config['namespace'] == 'kubernetes'
    assert check.kubelet_scraper_config['namespace'] == 'kubernetes'
    assert check.probes_scraper_config['namespace'] == 'kubernetes'

    assert isinstance(check.cadvisor_scraper_config, dict)
    assert isinstance(check.kubelet_scraper_config, dict)
    assert isinstance(check.probes_scraper_config, dict)


def test_kubelet_check_prometheus_instance_tags(monkeypatch, aggregator, tagger):
    _test_kubelet_check_prometheus(
        monkeypatch, aggregator, tagger, kube_version=KUBE_1_14, instance_tags=["instance:tag"]
    )


def test_kubelet_check_prometheus_no_instance_tags(monkeypatch, aggregator, tagger):
    _test_kubelet_check_prometheus(monkeypatch, aggregator, tagger, kube_version=KUBE_1_14, instance_tags=None)


def test_kubelet_check_prometheus_instance_tags_pre_1_14(monkeypatch, aggregator, tagger):
    _test_kubelet_check_prometheus(
        monkeypatch, aggregator, tagger, kube_version=KUBE_PRE_1_14, instance_tags=["instance:tag"]
    )


def test_kubelet_check_prometheus_no_instance_tags_pre_1_14(monkeypatch, aggregator, tagger):
    _test_kubelet_check_prometheus(monkeypatch, aggregator, tagger, kube_version=KUBE_PRE_1_14, instance_tags=None)


def test_kubelet_check_prometheus_instance_tags_1_21(monkeypatch, aggregator, tagger):
    _test_kubelet_check_prometheus(
        monkeypatch, aggregator, tagger, kube_version=KUBE_1_21, instance_tags=["instance:tag"]
    )


def test_kubelet_check_prometheus_no_instance_tags_1_21(monkeypatch, aggregator, tagger):
    _test_kubelet_check_prometheus(monkeypatch, aggregator, tagger, kube_version=KUBE_1_21, instance_tags=None)


def _test_kubelet_check_prometheus(monkeypatch, aggregator, tagger, kube_version, instance_tags):
    instance = {}
    if instance_tags:
        instance["tags"] = instance_tags

    check = mock_kubelet_check(monkeypatch, [instance], kube_version=kube_version)
    monkeypatch.setattr(check, 'process_cadvisor', mock.Mock(return_value=None))

    check.check(instance)
    assert check.cadvisor_legacy_url is None
    check.retrieve_pod_list.assert_called_once()
    check._retrieve_node_spec.assert_called_once()
    check._retrieve_stats.assert_called_once()
    check._perform_kubelet_check.assert_called_once()
    check.process_cadvisor.assert_not_called()

    # called twice so pct metrics are guaranteed to be there
    check.check(instance)
    if kube_version != KUBE_1_21:
        for metric in EXPECTED_METRICS_COMMON:
            aggregator.assert_metric(metric)
            if instance_tags:
                for tag in instance_tags:
                    aggregator.assert_metric_has_tag(metric, tag)

    if kube_version == KUBE_PRE_1_14:
        prom_metrics = EXPECTED_METRICS_PROMETHEUS_PRE_1_14

    if kube_version == KUBE_1_14:
        prom_metrics = EXPECTED_METRICS_PROMETHEUS_1_14

    if kube_version == KUBE_1_21:
        prom_metrics = EXPECTED_METRICS_PROMETHEUS_1_21

    for metric in prom_metrics:
        aggregator.assert_metric(metric)
        if instance_tags:
            for tag in instance_tags:
                aggregator.assert_metric_has_tag(metric, tag)

    assert aggregator.metrics_asserted_pct == 100.0


def test_kubelet_credentials_update(monkeypatch, aggregator):
    instance = {
        'kubelet_metrics_endpoint': 'http://10.8.0.1:10255/metrics',
        'cadvisor_metrics_endpoint': 'http://10.8.0.1:10255/metrics/cadvisor',
    }
    check = mock_kubelet_check(monkeypatch, [instance], kube_version=None)

    get = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: mock_from_file('kubelet_metrics_1_14.txt').splitlines()
    )
    with mock.patch('requests.get', return_value=get):
        check.check(instance)

    assert check._http_handlers[instance['kubelet_metrics_endpoint']].options['verify'] is True
    assert check._http_handlers[instance['cadvisor_metrics_endpoint']].options['verify'] is True

    get = mock.MagicMock(
        status_code=200, iter_lines=lambda **kwargs: mock_from_file('kubelet_metrics_1_14.txt').splitlines()
    )
    kubelet_conn_info = {'url': 'http://127.0.0.1:10255', 'ca_cert': False}
    with mock.patch('requests.get', return_value=get), mock.patch(
        'datadog_checks.kubelet.kubelet.get_connection_info', return_value=kubelet_conn_info
    ):
        check.check(instance)

    assert check._http_handlers[instance['kubelet_metrics_endpoint']].options['verify'] is False
    assert check._http_handlers[instance['cadvisor_metrics_endpoint']].options['verify'] is False


def test_prometheus_cpu_summed(monkeypatch, aggregator, tagger):
    check = mock_kubelet_check(monkeypatch, [{}])
    monkeypatch.setattr(check, 'rate', mock.Mock())
    check.check({"cadvisor_metrics_endpoint": "http://dummy/metrics/cadvisor", "kubelet_metrics_endpoint": ""})

    # Make sure we submit the summed rates correctly for containers:
    # - fluentd-gcp-v2.0.10-9q9t4 uses two cpus, we need to sum (1228.32 + 825.32) * 10**9 = 2053640000000
    # - demo-app-success-c485bc67b-klj45 is mono-threaded, we submit 7.756358313 * 10**9 = 7756358313
    #
    calls = [
        mock.call(
            'kubernetes.cpu.usage.total',
            2053640000000.0,
            ['kube_container_name:fluentd-gcp', 'kube_deployment:fluentd-gcp-v2.0.10'],
        ),
        mock.call('kubernetes.cpu.usage.total', 7756358313.0, ['pod_name:demo-app-success-c485bc67b-klj45']),
    ]
    check.rate.assert_has_calls(calls, any_order=True)

    # Make sure the per-core metrics are not submitted
    bad_calls = [
        mock.call(
            'kubernetes.cpu.usage.total',
            1228320000000.0,
            ['kube_container_name:fluentd-gcp', 'kube_deployment:fluentd-gcp-v2.0.10'],
        ),
        mock.call(
            'kubernetes.cpu.usage.total',
            825320000000.0,
            ['kube_container_name:fluentd-gcp', 'kube_deployment:fluentd-gcp-v2.0.10'],
        ),
    ]
    for c in bad_calls:
        assert c not in check.rate.mock_calls


def test_prometheus_net_summed(monkeypatch, aggregator, tagger):
    check = mock_kubelet_check(monkeypatch, [{}])
    monkeypatch.setattr(check, 'rate', mock.Mock())
    check.check({"cadvisor_metrics_endpoint": "http://dummy/metrics/cadvisor", "kubelet_metrics_endpoint": ""})

    # Make sure we submit the summed rates correctly for pods:
    # - dd-agent-q6hpw has two interfaces, we need to sum (1.2638051777 + 2.2638051777) * 10**10 = 35276103554
    # - fluentd-gcp-v2.0.10-9q9t4 has one interface only, we submit 5.8107648 * 10**07 = 58107648
    #
    calls = [
        mock.call('kubernetes.network.rx_bytes', 35276103554.0, ['pod_name:dd-agent-q6hpw', 'interface:eth0']),
        mock.call('kubernetes.network.rx_bytes', 58107648.0, ['pod_name:fluentd-gcp-v2.0.10-9q9t4', 'interface:eth0']),
    ]
    check.rate.assert_has_calls(calls, any_order=True)

    bad_calls = [
        # Make sure the per-interface metrics are not submitted
        mock.call('kubernetes.network.rx_bytes', 12638051777.0, ['pod_name:dd-agent-q6hpw']),
        mock.call('kubernetes.network.rx_bytes', 22638051777.0, ['pod_name:dd-agent-q6hpw']),
        # Make sure hostNetwork pod metrics are not submitted, test with and without sum to be sure
        mock.call(
            'kubernetes.network.rx_bytes',
            (4917138204.0 + 698882782.0),
            ['pod_name:kube-proxy-gke-haissam-default-pool-be5066f1-wnvn'],
        ),
        mock.call(
            'kubernetes.network.rx_bytes', 4917138204.0, ['pod_name:kube-proxy-gke-haissam-default-pool-be5066f1-wnvn']
        ),
        mock.call(
            'kubernetes.network.rx_bytes', 698882782.0, ['pod_name:kube-proxy-gke-haissam-default-pool-be5066f1-wnvn']
        ),
    ]
    for c in bad_calls:
        assert c not in check.rate.mock_calls


def test_prometheus_filtering(monkeypatch, aggregator):
    # Let's intercept the container_cpu_usage_seconds_total
    # metric to make sure no sample with an empty pod (k8s >= 1.16)
    # or pod_name (k8s < 1.16) label goes through input filtering
    # 12 out of the 45 samples should pass through the filter for k8s < 1.16
    # 27 out of 31 for k8s >= 1.16
    method_name = "datadog_checks.kubelet.prometheus.CadvisorPrometheusScraperMixin.container_cpu_usage_seconds_total"
    with mock.patch(method_name) as mock_method:
        # k8s >= 1.16
        check = mock_kubelet_check(monkeypatch, [{}], kube_version=KUBE_POST_1_16)
        check.check({"cadvisor_metrics_endpoint": "http://dummy/metrics/cadvisor", "kubelet_metrics_endpoint": ""})

        mock_method.assert_called_once()
        metric = mock_method.call_args[0][0]
        assert len(metric.samples) == 27
        for sample in metric.samples:
            assert sample.name == "container_cpu_usage_seconds_total"
            assert sample.labels["pod"] != ""

    with mock.patch(method_name) as mock_method:
        # k8s < 1.16
        check = mock_kubelet_check(monkeypatch, [{}])
        check.check({"cadvisor_metrics_endpoint": "http://dummy/metrics/cadvisor", "kubelet_metrics_endpoint": ""})

        mock_method.assert_called_once()
        metric = mock_method.call_args[0][0]
        assert len(metric.samples) == 12
        for sample in metric.samples:
            assert sample.name == "container_cpu_usage_seconds_total"
            assert sample.labels["pod_name"] != ""


def test_ignore_metrics(monkeypatch, aggregator):
    check = mock_kubelet_check(monkeypatch, [{"ignore_metrics": ["container_network_[Aa-zZ]*_bytes_total"]}])
    check.check({"cadvisor_metrics_endpoint": "http://dummy/metrics/cadvisor", "kubelet_metrics_endpoint": ""})
    check._perform_kubelet_check.assert_called_once()

    aggregator.assert_metric('kubernetes.network.tx_dropped')  # this metric is not filtered out by the regex
    assert len(aggregator.metrics('kubernetes.network.rx_bytes')) == 0  # this metric is disabled
    assert len(aggregator.metrics('kubernetes.network.tx_bytes')) == 0  # this metric is disabled


def test_kubelet_check_instance_config(monkeypatch):
    def mock_kubelet_check_no_prom():
        check = mock_kubelet_check(monkeypatch, [{}])

        monkeypatch.setattr(check, 'process', mock.Mock(return_value=None))
        monkeypatch.setattr(check, 'process_cadvisor', mock.Mock(return_value=None))

        return check

    check = mock_kubelet_check_no_prom()
    check.check({"cadvisor_port": 0, "cadvisor_metrics_endpoint": "", "kubelet_metrics_endpoint": ""})

    assert check.cadvisor_legacy_url is None
    check.retrieve_pod_list.assert_called_once()
    check._retrieve_node_spec.assert_called_once()
    check._perform_kubelet_check.assert_called_once()
    check.process_cadvisor.assert_not_called()

    check = mock_kubelet_check_no_prom()
    check.check({"cadvisor_port": 0, "metrics_endpoint": "", "kubelet_metrics_endpoint": "http://dummy"})


def test_report_pods_running(monkeypatch, tagger):
    check = KubeletCheck('kubelet', {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods.json'))))
    monkeypatch.setattr(check, 'gauge', mock.Mock())
    pod_list = check.retrieve_pod_list()

    check._report_pods_running(pod_list, [])

    calls = [
        mock.call('kubernetes.pods.running', 1, ["pod_name:fluentd-gcp-v2.0.10-9q9t4"]),
        mock.call('kubernetes.pods.running', 1, ["pod_name:fluentd-gcp-v2.0.10-p13r3"]),
        mock.call('kubernetes.pods.running', 1, ['pod_name:demo-app-success-c485bc67b-klj45']),
        mock.call(
            'kubernetes.containers.running',
            2,
            ["kube_container_name:fluentd-gcp", "kube_deployment:fluentd-gcp-v2.0.10"],
        ),
        mock.call(
            'kubernetes.containers.running',
            2,
            ["kube_container_name:prometheus-to-sd-exporter", "kube_deployment:fluentd-gcp-v2.0.10"],
        ),
        mock.call('kubernetes.containers.running', 1, ['pod_name:demo-app-success-c485bc67b-klj45']),
    ]
    check.gauge.assert_has_calls(calls, any_order=True)
    # Make sure non running container/pods are not sent
    bad_calls = [
        mock.call('kubernetes.pods.running', 1, ['pod_name:dd-agent-q6hpw']),
        mock.call('kubernetes.containers.running', 1, ['pod_name:dd-agent-q6hpw']),
    ]
    for c in bad_calls:
        assert c not in check.gauge.mock_calls


def test_report_pods_running_none_ids(monkeypatch, tagger):
    # Make sure the method is resilient to inconsistent podlists
    podlist = json.loads(mock_from_file('pods.json'))
    podlist["items"][0]['metadata']['uid'] = None
    podlist["items"][1]['status']['containerStatuses'][0]['containerID'] = None

    check = KubeletCheck('kubelet', {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=podlist))
    monkeypatch.setattr(check, 'gauge', mock.Mock())
    pod_list = check.retrieve_pod_list()

    check._report_pods_running(pod_list, [])

    calls = [
        mock.call('kubernetes.pods.running', 1, ["pod_name:fluentd-gcp-v2.0.10-9q9t4"]),
        mock.call(
            'kubernetes.containers.running',
            2,
            ["kube_container_name:prometheus-to-sd-exporter", "kube_deployment:fluentd-gcp-v2.0.10"],
        ),
    ]
    check.gauge.assert_has_calls(calls, any_order=True)


def test_report_container_spec_metrics(monkeypatch, tagger):
    check = KubeletCheck('kubelet', {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods.json'))))
    monkeypatch.setattr(check, 'gauge', mock.Mock())

    attrs = {'is_excluded.return_value': False}
    check.pod_list_utils = mock.Mock(**attrs)

    pod_list = check.retrieve_pod_list()
    instance_tags = ["one:1", "two:2"]
    check._report_container_spec_metrics(pod_list, instance_tags)

    calls = [
        mock.call(
            'kubernetes.cpu.requests',
            0.1,
            ['kube_container_name:fluentd-gcp', 'kube_deployment:fluentd-gcp-v2.0.10'] + instance_tags,
        ),
        mock.call(
            'kubernetes.memory.requests',
            209715200.0,
            ['kube_container_name:fluentd-gcp', 'kube_deployment:fluentd-gcp-v2.0.10'] + instance_tags,
        ),
        mock.call(
            'kubernetes.memory.limits',
            314572800.0,
            ['kube_container_name:fluentd-gcp', 'kube_deployment:fluentd-gcp-v2.0.10'] + instance_tags,
        ),
        mock.call('kubernetes.cpu.requests', 0.1, ['kube_container_name:datadog-agent'] + instance_tags),
        mock.call('kubernetes.cpu.requests', 0.1, ['kube_container_name:datadog-agent'] + instance_tags),
        mock.call('kubernetes.memory.requests', 134217728.0, ['kube_container_name:datadog-agent'] + instance_tags),
        mock.call('kubernetes.cpu.limits', 0.25, ['kube_container_name:datadog-agent'] + instance_tags),
        mock.call('kubernetes.memory.limits', 536870912.0, ['kube_container_name:datadog-agent'] + instance_tags),
        mock.call('kubernetes.cpu.requests', 0.1, ["pod_name:demo-app-success-c485bc67b-klj45"] + instance_tags),
    ]
    if any(('pod_name:pi-kff76' in e for e in [x[0][2] for x in check.gauge.call_args_list])):
        raise AssertionError("kubernetes.cpu.requests was submitted for a non-running pod")
    check.gauge.assert_has_calls(calls, any_order=True)


def test_report_container_state_metrics(monkeypatch, tagger):
    check = KubeletCheck('kubelet', {}, [{}])
    check.pod_list_url = "dummyurl"
    monkeypatch.setattr(
        check,
        'perform_kubelet_query',
        mock.Mock(return_value=MockResponse(file_path=os.path.join(HERE, 'fixtures', 'pods_crashed.json'))),
    )
    monkeypatch.setattr(check, 'compute_pod_expiration_datetime', mock.Mock(return_value=None))
    monkeypatch.setattr(check, 'gauge', mock.Mock())

    attrs = {'is_excluded.return_value': False}
    check.pod_list_utils = mock.Mock(**attrs)

    pod_list = check.retrieve_pod_list()

    instance_tags = ["one:1", "two:2"]
    check._report_container_state_metrics(pod_list, instance_tags)

    calls = [
        mock.call(
            'kubernetes.containers.last_state.terminated',
            1,
            ['kube_container_name:fluentd-gcp', 'kube_deployment:fluentd-gcp-v2.0.10']
            + instance_tags
            + ['reason:OOMKilled'],
        ),
        mock.call(
            'kubernetes.containers.state.waiting',
            1,
            ['kube_container_name:prometheus-to-sd-exporter', 'kube_deployment:fluentd-gcp-v2.0.10']
            + instance_tags
            + ['reason:CrashLoopBackOff'],
        ),
        mock.call(
            'kubernetes.containers.restarts',
            1,
            ['kube_container_name:fluentd-gcp', 'kube_deployment:fluentd-gcp-v2.0.10'] + instance_tags,
        ),
        mock.call(
            'kubernetes.containers.restarts',
            0,
            ['kube_container_name:prometheus-to-sd-exporter', 'kube_deployment:fluentd-gcp-v2.0.10'] + instance_tags,
        ),
        mock.call('kubernetes.containers.restarts', 0, ['kube_container_name:datadog-agent'] + instance_tags),
        mock.call('kubernetes.containers.restarts', 0, ['kube_container_name:datadog-agent'] + instance_tags),
    ]
    check.gauge.assert_has_calls(calls, any_order=True)

    container_state_gauges = [
        x[0][2] for x in check.gauge.call_args_list if x[0][0].startswith('kubernetes.containers.state')
    ]
    if any(('reason:TransientReason' in e for e in container_state_gauges)):
        raise AssertionError('kubernetes.containers.state.* was submitted with a transient reason')
    if any((not any(x for x in e if x.startswith('reason:')) for e in container_state_gauges)):
        raise AssertionError('kubernetes.containers.state.* was submitted without a reason')


def test_no_tags_no_metrics(monkeypatch, aggregator, tagger):
    # Reset tagger without tags
    tagger.reset()
    tagger.set_tags({})

    check = mock_kubelet_check(monkeypatch, [{}])
    check.check({"cadvisor_metrics_endpoint": "http://dummy/metrics/cadvisor", "kubelet_metrics_endpoint": ""})

    # Test that we get only the node related metrics (no calls to the tagger for these ones)
    aggregator.assert_metric('kubernetes.memory.capacity')
    aggregator.assert_metric('kubernetes.cpu.capacity')
    aggregator.assert_metric('kubernetes.runtime.cpu.usage')
    aggregator.assert_metric('kubernetes.runtime.memory.usage')
    aggregator.assert_metric('kubernetes.runtime.memory.rss')
    aggregator.assert_metric('kubernetes.kubelet.cpu.usage')
    aggregator.assert_metric('kubernetes.kubelet.memory.usage')
    aggregator.assert_metric('kubernetes.kubelet.memory.rss')
    aggregator.assert_metric('kubernetes.apiserver.certificate.expiration.count')
    aggregator.assert_metric('kubernetes.apiserver.certificate.expiration.sum')
    aggregator.assert_metric('kubernetes.go_goroutines')
    aggregator.assert_metric('kubernetes.go_threads')
    aggregator.assert_metric('kubernetes.kubelet.container.log_filesystem.used_bytes')
    aggregator.assert_metric('kubernetes.kubelet.docker.errors')
    aggregator.assert_metric('kubernetes.kubelet.docker.operations')
    aggregator.assert_metric('kubernetes.kubelet.docker.operations.duration.count')
    aggregator.assert_metric('kubernetes.kubelet.docker.operations.duration.quantile')
    aggregator.assert_metric('kubernetes.kubelet.docker.operations.duration.sum')
    aggregator.assert_metric('kubernetes.kubelet.evictions')
    aggregator.assert_metric('kubernetes.kubelet.network_plugin.latency.count')
    aggregator.assert_metric('kubernetes.kubelet.network_plugin.latency.sum')
    aggregator.assert_metric('kubernetes.kubelet.pleg.relist_duration.count')
    aggregator.assert_metric('kubernetes.kubelet.pleg.relist_duration.sum')
    aggregator.assert_metric('kubernetes.kubelet.pleg.relist_interval.count')
    aggregator.assert_metric('kubernetes.kubelet.pleg.relist_interval.sum')
    aggregator.assert_metric('kubernetes.kubelet.pod.start.duration.count')
    aggregator.assert_metric('kubernetes.kubelet.pod.start.duration.sum')
    aggregator.assert_metric('kubernetes.kubelet.pod.worker.duration.count')
    aggregator.assert_metric('kubernetes.kubelet.pod.worker.duration.sum')
    aggregator.assert_metric('kubernetes.kubelet.pod.worker.start.duration.count')
    aggregator.assert_metric('kubernetes.kubelet.pod.worker.start.duration.sum')
    aggregator.assert_metric('kubernetes.kubelet.runtime.errors')
    aggregator.assert_metric('kubernetes.kubelet.runtime.operations')
    aggregator.assert_metric('kubernetes.kubelet.runtime.operations.duration.count')
    aggregator.assert_metric('kubernetes.kubelet.runtime.operations.duration.quantile')
    aggregator.assert_metric('kubernetes.kubelet.runtime.operations.duration.sum')
    aggregator.assert_metric('kubernetes.kubelet.volume.stats.available_bytes')
    aggregator.assert_metric('kubernetes.kubelet.volume.stats.capacity_bytes')
    aggregator.assert_metric('kubernetes.kubelet.volume.stats.inodes')
    aggregator.assert_metric('kubernetes.kubelet.volume.stats.inodes_free')
    aggregator.assert_metric('kubernetes.kubelet.volume.stats.inodes_used')
    aggregator.assert_metric('kubernetes.kubelet.volume.stats.used_bytes')
    aggregator.assert_metric('kubernetes.rest.client.latency.count')
    aggregator.assert_metric('kubernetes.rest.client.latency.sum')
    aggregator.assert_metric('kubernetes.rest.client.requests')
    aggregator.assert_all_metrics_covered()


def test_static_pods(monkeypatch, aggregator, tagger):
    tagger.reset()
    tagger.set_tags(
        {
            "kubernetes_pod_uid://260c2b1d43b094af6d6b4ccba082c2db": [
                'pod_name:kube-proxy-gke-haissam-default-pool-be5066f1-wnvn'
            ]
        }
    )

    check = mock_kubelet_check(monkeypatch, [{}])
    check.check({"cadvisor_metrics_endpoint": "http://dummy/metrics/cadvisor", "kubelet_metrics_endpoint": ""})

    # Test that we get metrics for this static pod
    aggregator.assert_metric(
        'kubernetes.cpu.user.total',
        109.76,
        ['kube_container_name:kube-proxy', 'pod_name:kube-proxy-gke-haissam-default-pool-be5066f1-wnvn'],
    )


def test_pod_expiration(monkeypatch, aggregator, tagger):
    check = KubeletCheck('kubelet', {}, [{}])
    check.pod_list_url = "dummyurl"

    # Fixtures contains four pods:
    #   - dd-agent-ntepl old but running
    #   - hello1-1550504220-ljnzx succeeded and old enough to expire
    #   - hello5-1550509440-rlgvf succeeded but not old enough
    #   - hello8-1550505780-kdnjx has one old container and a recent container, don't expire
    monkeypatch.setattr(
        check,
        'perform_kubelet_query',
        mock.Mock(return_value=MockResponse(file_path=os.path.join(HERE, 'fixtures', 'pods_expired.json'))),
    )
    monkeypatch.setattr(
        check, 'compute_pod_expiration_datetime', mock.Mock(return_value=parse_rfc3339("2019-02-18T16:00:06Z"))
    )

    attrs = {'is_excluded.return_value': False}
    check.pod_list_utils = mock.Mock(**attrs)

    pod_list = check.retrieve_pod_list()
    assert pod_list['expired_count'] == 1

    expected_names = ['dd-agent-ntepl', 'hello5-1550509440-rlgvf', 'hello8-1550505780-kdnjx']
    collected_names = [p['metadata']['name'] for p in pod_list['items']]
    assert collected_names == expected_names

    # Test .pods.expired gauge is submitted
    check._report_container_state_metrics(pod_list, ["custom:tag"])
    aggregator.assert_metric("kubernetes.pods.expired", value=1, tags=["custom:tag"])

    # Ensure we can iterate twice over the podlist
    check._report_pods_running(pod_list, [])
    aggregator.assert_metric("kubernetes.pods.running", value=1, tags=["pod_name:dd-agent-ntepl"])
    aggregator.assert_metric("kubernetes.containers.running", value=1, tags=["pod_name:dd-agent-ntepl"])


class MockedResponse(mock.Mock):
    @staticmethod
    def iter_lines(**kwargs):
        return []


def test_perform_kubelet_check(monkeypatch):
    check = KubeletCheck('kubelet', {}, [{}])
    check.kube_health_url = "http://127.0.0.1:10255/healthz"
    check.kubelet_credentials = KubeletCredentials({})
    monkeypatch.setattr(check, 'service_check', mock.Mock())

    instance_tags = ["one:1"]
    get = MockedResponse()
    with mock.patch("requests.get", side_effect=get):
        check._perform_kubelet_check(instance_tags)

    get.assert_has_calls(
        [
            mock.call(
                'http://127.0.0.1:10255/healthz',
                auth=None,
                cert=None,
                headers=None,
                params={'verbose': True},
                proxies=None,
                stream=False,
                timeout=(10.0, 10.0),
                verify=None,
                allow_redirects=True,
            )
        ]
    )
    calls = [mock.call('kubernetes.kubelet.check', 0, tags=instance_tags)]
    check.service_check.assert_has_calls(calls)


def test_report_node_metrics(monkeypatch):
    check = KubeletCheck('kubelet', {}, [{}])
    mock_resp = mock.Mock(status_code=200, raise_for_status=mock.Mock())
    mock_resp.json = mock.Mock(return_value={'num_cores': 4, 'memory_capacity': 512})
    monkeypatch.setattr(check, '_retrieve_node_spec', mock.Mock(return_value=mock_resp))
    monkeypatch.setattr(check, 'gauge', mock.Mock())
    check._report_node_metrics(['foo:bar'])
    calls = [
        mock.call('kubernetes.cpu.capacity', 4.0, ['foo:bar']),
        mock.call('kubernetes.memory.capacity', 512.0, ['foo:bar']),
    ]
    check.gauge.assert_has_calls(calls, any_order=False)


def test_report_node_metrics_kubernetes1_18(monkeypatch, aggregator):
    check = KubeletCheck('kubelet', {}, [{}])
    check.kubelet_credentials = KubeletCredentials({'verify_tls': 'false'})
    check.node_spec_url = "http://localhost:10255/spec"

    get = mock.MagicMock(status_code=404, iter_lines=lambda **kwargs: "Error Code")
    get.raise_for_status.side_effect = requests.HTTPError('error')
    with mock.patch('requests.get', return_value=get):
        check._report_node_metrics(['foo:bar'])
        aggregator.assert_all_metrics_covered()


def test_add_labels_to_tags(monkeypatch, aggregator):
    check = mock_kubelet_check(monkeypatch, [{}])
    check.check({"cadvisor_metrics_endpoint": "http://dummy/metrics/cadvisor", "kubelet_metrics_endpoint": ""})

    for metric in METRICS_WITH_DEVICE_TAG:
        tag = 'device:%s' % METRICS_WITH_DEVICE_TAG[metric]
        aggregator.assert_metric_has_tag(metric, tag)

    for metric in METRICS_WITH_INTERFACE_TAG:
        tag = 'interface:%s' % METRICS_WITH_INTERFACE_TAG[metric]
        aggregator.assert_metric_has_tag(metric, tag)


def test_report_container_requests_limits(monkeypatch, tagger):
    check = KubeletCheck('kubelet', {}, [{}])
    monkeypatch.setattr(
        check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods_requests_limits.json')))
    )
    monkeypatch.setattr(check, 'gauge', mock.Mock())

    attrs = {'is_excluded.return_value': False}
    check.pod_list_utils = mock.Mock(**attrs)

    pod_list = check.retrieve_pod_list()
    tags = ['kube_container_name:cassandra']
    check._report_container_spec_metrics(pod_list, tags)

    calls = [
        mock.call('kubernetes.cpu.requests', 0.5, ['pod_name:cassandra-0'] + tags),
        mock.call('kubernetes.memory.requests', 1073741824.0, ['pod_name:cassandra-0'] + tags),
        mock.call('kubernetes.ephemeral-storage.requests', 0.5, ['pod_name:cassandra-0'] + tags),
        mock.call('kubernetes.cpu.limits', 0.5, ['pod_name:cassandra-0'] + tags),
        mock.call('kubernetes.memory.limits', 1073741824.0, ['pod_name:cassandra-0'] + tags),
        mock.call('kubernetes.ephemeral-storage.limits', 2147483648.0, ['pod_name:cassandra-0'] + tags),
    ]
    check.gauge.assert_has_calls(calls, any_order=True)


def test_kubelet_stats_summary_not_available(monkeypatch, aggregator, tagger):
    instance = {"tags": ["instance:tag"]}

    check = mock_kubelet_check(monkeypatch, [instance], stats_summary_fail=True)

    check.check(instance)
    check._retrieve_stats.assert_called_once()


def test_process_stats_summary_not_source_windows(monkeypatch, aggregator, tagger):
    check = KubeletCheck('kubelet', {}, [{}])
    pod_list_utils = PodListUtils(json.loads(mock_from_file('pods_windows.json')))
    stats = json.loads(mock_from_file('stats_summary_windows.json'))

    tagger.reset()
    tagger.set_tags(WINDOWS_TAGS)

    tags = ["instance:tag"]
    check.process_stats_summary(pod_list_utils, stats, tags, False)

    # As we did not activate `use_stats_summary_as_source`, we only have ephemeral storage metrics
    # Kubelet stats not present as they are not returned on Windows
    aggregator.assert_metric(
        'kubernetes.ephemeral_storage.usage', 919980.0, tags + ['kube_namespace:default', 'pod_name:dd-datadog-lbvkl']
    )


def test_process_stats_summary_not_source_linux(monkeypatch, aggregator, tagger):
    check = KubeletCheck('kubelet', {}, [{}])
    pod_list_utils = PodListUtils(json.loads(mock_from_file('pods.json')))
    stats = json.loads(mock_from_file('stats_summary.json'))

    tagger.reset()
    tagger.set_tags(COMMON_TAGS)

    tags = ["instance:tag"]
    check.process_stats_summary(pod_list_utils, stats, tags, False)

    # As we did not activate `use_stats_summary_as_source`,
    # we only have ephemeral storage metrics and kubelet stats
    aggregator.assert_metric(
        'kubernetes.ephemeral_storage.usage', 69406720.0, ['instance:tag', 'pod_name:fluentd-gcp-v2.0.10-9q9t4']
    )
    aggregator.assert_metric(
        'kubernetes.ephemeral_storage.usage', 49152.0, ['instance:tag', 'pod_name:datadog-agent-jbm2k']
    )
    aggregator.assert_metric('kubernetes.runtime.cpu.usage', 19442853.0, ['instance:tag'])
    aggregator.assert_metric('kubernetes.kubelet.cpu.usage', 36755862.0, ['instance:tag'])
    aggregator.assert_metric('kubernetes.runtime.memory.rss', 101273600.0, ['instance:tag'])
    aggregator.assert_metric('kubernetes.kubelet.memory.rss', 88477696.0, ['instance:tag'])


def test_process_stats_summary_as_source(monkeypatch, aggregator, tagger):
    check = KubeletCheck('kubelet', {}, [{}])
    pod_list_utils = PodListUtils(json.loads(mock_from_file('pods_windows.json')))
    stats = json.loads(mock_from_file('stats_summary_windows.json'))

    tagger.reset()
    tagger.set_tags(WINDOWS_TAGS)

    tags = ["instance:tag"]
    check.process_stats_summary(pod_list_utils, stats, tags, True)

    aggregator.assert_metric(
        'kubernetes.ephemeral_storage.usage', 919980.0, tags + ['kube_namespace:default', 'pod_name:dd-datadog-lbvkl']
    )
    aggregator.assert_metric(
        'kubernetes.network.tx_bytes', 163670.0, tags + ['kube_namespace:default', 'pod_name:dd-datadog-lbvkl']
    )
    aggregator.assert_metric(
        'kubernetes.network.rx_bytes', 694636.0, tags + ['kube_namespace:default', 'pod_name:dd-datadog-lbvkl']
    )
    aggregator.assert_metric(
        'kubernetes.network.tx_bytes',
        258157.0,
        tags + ['kube_namespace:default', 'pod_name:windows-server-iis-6c68545d57-gwtn9'],
    )
    aggregator.assert_metric(
        'kubernetes.network.rx_bytes',
        509185.0,
        tags + ['kube_namespace:default', 'pod_name:windows-server-iis-6c68545d57-gwtn9'],
    )
    aggregator.assert_metric(
        'kubernetes.cpu.usage.total',
        13796875000.0,
        tags + ['kube_container_name:agent', 'kube_namespace:default', 'pod_name:dd-datadog-lbvkl'],
    )
    aggregator.assert_metric(
        'kubernetes.cpu.usage.total',
        9359375000.0,
        tags + ['kube_container_name:process-agent', 'kube_namespace:default', 'pod_name:dd-datadog-lbvkl'],
    )
    aggregator.assert_metric(
        'kubernetes.cpu.usage.total',
        70140625000.0,
        tags
        + [
            'kube_container_name:windows-server-iis',
            'kube_namespace:default',
            'pod_name:windows-server-iis-6c68545d57-gwtn9',
        ],
    )
    aggregator.assert_metric(
        'kubernetes.memory.working_set',
        136089600.0,
        tags + ['kube_container_name:agent', 'kube_namespace:default', 'pod_name:dd-datadog-lbvkl'],
    )
    aggregator.assert_metric(
        'kubernetes.memory.working_set',
        65474560.0,
        tags + ['kube_container_name:process-agent', 'kube_namespace:default', 'pod_name:dd-datadog-lbvkl'],
    )
    aggregator.assert_metric(
        'kubernetes.memory.working_set',
        136814592.0,
        tags
        + [
            'kube_container_name:windows-server-iis',
            'kube_namespace:default',
            'pod_name:windows-server-iis-6c68545d57-gwtn9',
        ],
    )
    aggregator.assert_metric(
        'kubernetes.filesystem.usage',
        0.0,
        tags + ['kube_container_name:agent', 'kube_namespace:default', 'pod_name:dd-datadog-lbvkl'],
    )
    aggregator.assert_metric(
        'kubernetes.filesystem.usage',
        0.0,
        tags + ['kube_container_name:process-agent', 'kube_namespace:default', 'pod_name:dd-datadog-lbvkl'],
    )
    aggregator.assert_metric(
        'kubernetes.filesystem.usage',
        0.0,
        tags
        + [
            'kube_container_name:windows-server-iis',
            'kube_namespace:default',
            'pod_name:windows-server-iis-6c68545d57-gwtn9',
        ],
    )
    aggregator.assert_metric(
        'kubernetes.filesystem.usage_pct',
        0.0,
        tags + ['kube_container_name:agent', 'kube_namespace:default', 'pod_name:dd-datadog-lbvkl'],
    )
    aggregator.assert_metric(
        'kubernetes.filesystem.usage_pct',
        0.0,
        tags + ['kube_container_name:process-agent', 'kube_namespace:default', 'pod_name:dd-datadog-lbvkl'],
    )
    aggregator.assert_metric(
        'kubernetes.filesystem.usage_pct',
        0.0,
        tags
        + [
            'kube_container_name:windows-server-iis',
            'kube_namespace:default',
            'pod_name:windows-server-iis-6c68545d57-gwtn9',
        ],
    )


def test_process_stats_summary_as_source_filtering_by_namespace(monkeypatch):
    check = KubeletCheck('kubelet', {}, [{}])
    monkeypatch.setattr(check, 'gauge', mock.Mock())
    monkeypatch.setattr(check, 'rate', mock.Mock())
    pod_list_utils = PodListUtils(json.loads(mock_from_file('pods_windows.json')))
    stats = json.loads(mock_from_file('stats_summary_windows.json'))

    # Namespace is excluded, so it shouldn't report any metrics
    monkeypatch.setattr(pod_list_utils, 'is_namespace_excluded', mock.Mock(return_value=True))
    check.process_stats_summary(pod_list_utils, stats, [], True)
    assert len(check.gauge.mock_calls) == 0 and len(check.rate.mock_calls) == 0


def test_kubelet_check_disable_summary_rates(monkeypatch, aggregator):
    check = KubeletCheck('kubelet', {}, [{'enabled_rates': ['*unsupported_regex*']}])
    pod_list_utils = PodListUtils(json.loads(mock_from_file('pods_windows.json')))
    stats = json.loads(mock_from_file('stats_summary_windows.json'))

    check.process_stats_summary(pod_list_utils, stats, [], True)  # windows/non-cadvisor case

    assert len(aggregator.metrics('kubernetes.network.tx_bytes')) == 0  # rate disabled
    assert len(aggregator.metrics('kubernetes.filesystem.usage_pct')) > 0  # gauge enabled


def test_silent_tls_warning(caplog, monkeypatch, aggregator):
    check = KubeletCheck('kubelet', {}, [{}])
    check.kube_health_url = "https://example.com/"
    check.kubelet_credentials = KubeletCredentials({'verify_tls': 'false'})

    with caplog.at_level(logging.DEBUG):
        check._perform_kubelet_check([])

    expected_message = 'An unverified HTTPS request is being made to https://example.com/'
    for _, _, message in caplog.record_tuples:
        assert message != expected_message


def test_create_pod_tags_by_pvc(monkeypatch, tagger):
    check = KubeletCheck('kubelet', {}, [{}])
    monkeypatch.setattr(check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods.json'))))
    pod_list = check.retrieve_pod_list()

    pod_tags_by_pvc = check._create_pod_tags_by_pvc(pod_list)

    expected_result = {
        'default/www-web-2': {
            'kube_namespace:default',
            'kube_service:nginx',
            'kube_stateful_set:web',
            'namespace:default',
        },
        'default/www2-web-3': {
            'kube_namespace:default',
            'kube_service:nginx',
            'kube_stateful_set:web',
            'namespace:default',
        },
    }
    assert pod_tags_by_pvc == expected_result

    # Test empty case
    empty = defaultdict(set)
    pod_tags_by_pvc = check._create_pod_tags_by_pvc({})
    assert pod_tags_by_pvc == empty


def test_ignore_namespace_for_volume_metrics(monkeypatch):
    instance = {}
    check = mock_kubelet_check(monkeypatch, [instance])
    monkeypatch.setattr(check, 'gauge', mock.Mock())

    volume_metrics = [
        'kubernetes.kubelet.volume.stats.available_bytes',
        'kubernetes.kubelet.volume.stats.capacity_bytes',
        'kubernetes.kubelet.volume.stats.inodes',
        'kubernetes.kubelet.volume.stats.inodes_free',
        'kubernetes.kubelet.volume.stats.inodes_used',
        'kubernetes.kubelet.volume.stats.used_bytes',
    ]

    # Call excluding all namespaces. Volume metrics should not be reported.
    c_is_excluded = mock.Mock(return_value=True)
    monkeypatch.setattr('datadog_checks.kubelet.common.c_is_excluded', c_is_excluded)
    check.check(instance)
    metrics_reported = [call.args[0] for call in check.gauge.mock_calls]

    for metric in volume_metrics:
        assert metric not in metrics_reported

    # Call without excluding namespaces. Volume metrics should be reported.
    c_is_excluded = mock.Mock(return_value=False)
    monkeypatch.setattr('datadog_checks.kubelet.common.c_is_excluded', c_is_excluded)
    check.check(instance)
    metrics_reported = [call.args[0] for call in check.gauge.mock_calls]

    for metric in volume_metrics:
        assert metric in metrics_reported


def test_filter_and_send_gauge_sample_included(monkeypatch, aggregator):
    check = mock_kubelet_check(monkeypatch, [{}])
    attrs = {'is_excluded.return_value': False, 'get_cid_by_labels.return_value': 'id'}
    check.pod_list_utils = mock.Mock(**attrs)
    check.instance_tags = ['k:v']

    check._filter_and_send_gauge_sample('kubernetes.gauge', ('gauge_name', {"lk": "lv"}, 1))

    aggregator.assert_metric('kubernetes.gauge', 1, ['k:v'])


def test_filter_and_send_gauge_sample_excluded(monkeypatch, aggregator):
    check = mock_kubelet_check(monkeypatch, [{}])
    attrs = {'is_excluded.return_value': True, 'get_cid_by_labels.return_value': 'id'}
    check.pod_list_utils = mock.Mock(**attrs)
    check.instance_tags = ['k:v']

    check._filter_and_send_gauge_sample('kubernetes.gauge', ('gauge_name', {"lk": "lv"}, 1))

    assert 'kubernetes.gauge' not in aggregator.metric_names


def test__filter_and_send_gauge_sample_tagger(monkeypatch, aggregator, tagger):
    tagger.reset()
    tagger.set_tags({'id': ['container_tag_k:container_tag_v']})

    check = mock_kubelet_check(monkeypatch, [{}])
    attrs = {'is_excluded.return_value': False, 'get_cid_by_labels.return_value': 'id'}
    check.pod_list_utils = mock.Mock(**attrs)
    check.instance_tags = ['instance_tags_k:instance_tags_v']

    check._filter_and_send_gauge_sample('kubernetes.gauge', ('gauge_name', {"lk": "lv"}, 1))

    aggregator.assert_metric(
        'kubernetes.gauge', 1, ['container_tag_k:container_tag_v', 'instance_tags_k:instance_tags_v']
    )


def test_probe_metrics(monkeypatch, aggregator, tagger):
    tagger.reset()
    tagger.set_tags(PROBE_TAGS)

    check = mock_kubelet_check(monkeypatch, [{}], pod_list='pod_list_probes.json', probes_available=True)
    check.check({'cadvisor_metrics_endpoint': '', 'kubelet_metrics_endpoint': ''})
    check._perform_kubelet_check.assert_called_once()

    aggregator.assert_metric(
        'kubernetes.liveness_probe.success.total',
        3,
        ['kube_namespace:default', 'pod_name:datadog-t9f28', 'kube_container_name:agent'],
    )

    aggregator.assert_metric(
        'kubernetes.readiness_probe.success.total',
        3,
        ['kube_namespace:default', 'pod_name:datadog-t9f28', 'kube_container_name:agent'],
    )

    aggregator.assert_metric(
        'kubernetes.liveness_probe.success.total',
        281049,
        ['kube_container_name:fluentbit', 'kube_namespace:kube-system', 'pod_name:fluentbit-gke-45gvm'],
    )

    aggregator.assert_metric(
        'kubernetes.liveness_probe.success.total',
        281049,
        ['kube_container_name:fluentbit-gke', 'kube_namespace:kube-system', 'pod_name:fluentbit-gke-45gvm'],
    )

    aggregator.assert_metric(
        'kubernetes.liveness_probe.success.total',
        1686298,
        ['kube_container_name:kubedns', 'kube_namespace:kube-system', 'pod_name:kube-dns-c598bd956-wgf4n'],
    )

    aggregator.assert_metric(
        'kubernetes.readiness_probe.success.total',
        1686303,
        ['kube_container_name:kubedns', 'kube_namespace:kube-system', 'pod_name:kube-dns-c598bd956-wgf4n'],
    )

    aggregator.assert_metric(
        'kubernetes.readiness_probe.failure.total',
        180,
        ['kube_container_name:calico-node', 'kube_namespace:kube-system', 'pod_name:calico-node-9qkw7'],
    )

    aggregator.assert_metric(
        'kubernetes.liveness_probe.failure.total',
        100,
        ['kube_container_name:calico-node', 'kube_namespace:kube-system', 'pod_name:calico-node-9qkw7'],
    )

    aggregator.assert_metric(
        'kubernetes.liveness_probe.success.total',
        1686306,
        ['kube_container_name:calico-node', 'kube_namespace:kube-system', 'pod_name:calico-node-9qkw7'],
    )

    aggregator.assert_metric(
        'kubernetes.readiness_probe.success.total',
        1686127,
        ['kube_container_name:calico-node', 'kube_namespace:kube-system', 'pod_name:calico-node-9qkw7'],
    )

    aggregator.assert_metric(
        'kubernetes.liveness_probe.success.total',
        1686298,
        ['kube_container_name:sidecar', 'kube_namespace:kube-system', 'pod_name:kube-dns-c598bd956-wgf4n'],
    )

    aggregator.assert_metric(
        'kubernetes.liveness_probe.success.total',
        1686298,
        ['kube_container_name:dnsmasq', 'kube_namespace:kube-system', 'pod_name:kube-dns-c598bd956-wgf4n'],
    )


@pytest.fixture()
def mock_request():
    with requests_mock.Mocker() as m:
        yield m


def test_detect_probes(monkeypatch, mock_request):
    mock_request.head('http://kubelet:10250/metrics/probes', status_code=200)
    instance = dict({'prometheus_url': 'http://kubelet:10250', 'namespace': 'kubernetes'})
    check = mock_kubelet_check(monkeypatch, [instance])
    scraper_config = check.get_scraper_config(instance)
    http_handler = check.get_http_handler(scraper_config)
    available = check.detect_probes(http_handler, 'http://kubelet:10250/metrics/probes')
    assert available is True
    assert check._probes_available is True
    assert mock_request.call_count == 1


def test_detect_probes_cached(monkeypatch, mock_request):
    mock_request.head('http://kubelet:10250/metrics/probes', status_code=200)
    instance = dict({'prometheus_url': 'http://kubelet:10250', 'namespace': 'kubernetes'})
    check = mock_kubelet_check(monkeypatch, [instance])
    scraper_config = check.get_scraper_config(instance)
    http_handler = check.get_http_handler(scraper_config)
    available = check.detect_probes(http_handler, 'http://kubelet:10250/metrics/probes')
    assert available is True
    assert check._probes_available is True
    assert mock_request.call_count == 1
    available = check.detect_probes(http_handler, 'http://kubelet:10250/metrics/probes')
    assert available is True
    assert check._probes_available is True
    assert mock_request.call_count == 1


def test_detect_probes_404(monkeypatch, mock_request):
    mock_request.head('http://kubelet:10250/metrics/probes', status_code=404)
    instance = dict({'prometheus_url': 'http://kubelet:10250', 'namespace': 'kubernetes'})
    check = mock_kubelet_check(monkeypatch, [instance])
    scraper_config = check.get_scraper_config(instance)
    http_handler = check.get_http_handler(scraper_config)
    available = check.detect_probes(http_handler, 'http://kubelet:10250/metrics/probes')
    assert available is False
    assert check._probes_available is False
    assert mock_request.call_count == 1


def test_detect_probes_404_cached(monkeypatch, mock_request):
    mock_request.head('http://kubelet:10250/metrics/probes', status_code=404)
    instance = dict({'prometheus_url': 'http://kubelet:10250', 'namespace': 'kubernetes'})
    check = mock_kubelet_check(monkeypatch, [instance])
    scraper_config = check.get_scraper_config(instance)
    http_handler = check.get_http_handler(scraper_config)
    available = check.detect_probes(http_handler, 'http://kubelet:10250/metrics/probes')
    assert available is False
    assert check._probes_available is False
    assert mock_request.call_count == 1
    available = check.detect_probes(http_handler, 'http://kubelet:10250/metrics/probes')
    assert available is False
    assert check._probes_available is False
    assert mock_request.call_count == 1


def test_detect_probes_req_exception(monkeypatch, mock_request):
    mock_request.head('http://kubelet:10250/metrics/probes', exc=requests.exceptions.ConnectTimeout)
    instance = dict({'prometheus_url': 'http://kubelet:10250', 'namespace': 'kubernetes'})
    check = mock_kubelet_check(monkeypatch, [instance])
    scraper_config = check.get_scraper_config(instance)
    http_handler = check.get_http_handler(scraper_config)
    available = check.detect_probes(http_handler, 'http://kubelet:10250/metrics/probes')
    assert available is False
    assert check._probes_available is None
    assert mock_request.call_count == 1


def test_sanitize_url_label():
    input = (
        "https://35.242.243.158/api/v1/namespaces/%7Bnamespace%7D/configmaps"
        + "?fieldSelector=%7Bvalue%7D&limit=%7Bvalue%7D&resourceVersion=%7Bvalue%7D"
    )
    expected = "/api/v1/namespaces/%7Bnamespace%7D/configmaps"
    assert KubeletCheck._sanitize_url_label(input) == expected
