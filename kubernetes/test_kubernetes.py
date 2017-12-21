# # (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import mock
import unittest
import os

# 3p
import simplejson as json
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest, Fixtures
from checks import AgentCheck
from utils.kubernetes.kubeutil import KubeUtil, detect_is_k8s

CPU = "CPU"
MEM = "MEM"
FS = "fs"
NET = "net"
NET_ERRORS = "net_errors"
DISK = "disk"
DISK_USAGE = "disk_usage"
PODS = "pods"
LIM = "limits"
REQ = "requests"
CAP = "capacity"

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'ci')

METRICS = [
    ('kubernetes.memory.usage', MEM),
    ('kubernetes.filesystem.usage', FS),
    ('kubernetes.filesystem.usage_pct', FS),
    ('kubernetes.cpu.usage.total', CPU),
    ('kubernetes.network.tx_bytes', NET),
    ('kubernetes.network.rx_bytes', NET),
    ('kubernetes.network_errors', NET_ERRORS),
    ('kubernetes.diskio.io_service_bytes.stats.total', DISK),
    ('kubernetes.filesystem.usage_pct', DISK_USAGE),
    ('kubernetes.filesystem.usage', DISK_USAGE),
    ('kubernetes.pods.running', PODS),
    ('kubernetes.cpu.limits', LIM),
    ('kubernetes.cpu.requests', REQ),
    ('kubernetes.cpu.capacity', CAP),
    ('kubernetes.memory.limits', LIM),
    ('kubernetes.memory.requests', REQ),
    ('kubernetes.memory.capacity', CAP),
]


class MockResponse:
    """
    Helper class to mock a json response from requests
    """
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


class MockIterLinesResponse:
    """
    Helper class to mock a text response from requests
    """
    def __init__(self, lines_array, status_code):
        self.lines_array = lines_array
        self.status_code = status_code

    def iter_lines(self):
        for line in self.lines_array:
            yield line

def KubeUtil_fake_retrieve_json_auth(url, timeout=10, params=None):
    if url.endswith("/namespaces"):
        return MockResponse(json.loads(Fixtures.read_file("namespaces.json", sdk_dir=FIXTURE_DIR, string_escape=False)), 200)
    if url.endswith("/events"):
        return MockResponse(json.loads(Fixtures.read_file("events.json", sdk_dir=FIXTURE_DIR, string_escape=False)), 200)
    return {}


@attr(requires='kubernetes')
class TestKubernetes(AgentCheckTest):

    CHECK_NAME = 'kubernetes'

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.1.json", sdk_dir=FIXTURE_DIR)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.1.json", sdk_dir=FIXTURE_DIR, string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def test_fail_1_1(self, *args):
        # To avoid the disparition of some gauges during the second check
        config = {
            "instances": [{"host": "foo"}]
        }

        # Can't use run_check_twice due to specific metrics
        self.run_check(config, force_reload=True)
        self.assertServiceCheck("kubernetes.kubelet.check", status=AgentCheck.CRITICAL, tags=None, count=1)

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.1.json", sdk_dir=FIXTURE_DIR)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.1.json", sdk_dir=FIXTURE_DIR, string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def test_metrics_1_1(self, *args):
        # To avoid the disparition of some gauges during the second check
        mocks = {
            '_perform_kubelet_checks': lambda x,y: None,
        }
        config = {
            "instances": [
                {
                    "host": "foo",
                    "enable_kubelet_checks": False
                }
            ]
        }
        # Can't use run_check_twice due to specific metrics
        self.run_check_twice(config, mocks=mocks, force_reload=True)

        expected_tags = [
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'container_name:k8s_POD.e4cc795_propjoe-dhdzk_default_ba151259-36e0-11e5-84ce-42010af01c62_ef0ed5f9', 'pod_name:default/propjoe-dhdzk'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'container_name:k8s_POD.2688308a_kube-dns-v8-smhcb_kube-system_b80ffab3-3619-11e5-84ce-42010af01c62_295f14ff', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'container_name:k8s_etcd.2e44beff_kube-dns-v8-smhcb_kube-system_b80ffab3-3619-11e5-84ce-42010af01c62_e3e504ad', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:fluentd-cloud-logging-kubernetes-minion', 'kube_namespace:kube-system', 'container_name:k8s_POD.e4cc795_fluentd-cloud-logging-kubernetes-minion-mu4w_kube-system_d0feac1ad02da9e97c4bf67970ece7a1_49dd977d', 'pod_name:kube-system/fluentd-cloud-logging-kubernetes-minion-mu4w'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'container_name:k8s_skydns.1e752dc0_kube-dns-v8-smhcb_kube-system_b80ffab3-3619-11e5-84ce-42010af01c62_7c1345a1', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'container_name:k8s_propjoe.21f63023_propjoe-dhdzk_default_ba151259-36e0-11e5-84ce-42010af01c62_19879457', 'pod_name:default/propjoe-dhdzk'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-ui-v1', 'kube_namespace:kube-system', 'container_name:k8s_POD.3b46e8b9_kube-ui-v1-sv2sq_kube-system_b7e8f250-3619-11e5-84ce-42010af01c62_209ed1dc', 'pod_name:kube-system/kube-ui-v1-sv2sq'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'container_name:k8s_kube2sky.1afa6a47_kube-dns-v8-smhcb_kube-system_b80ffab3-3619-11e5-84ce-42010af01c62_624bc34c', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'container_name:k8s_POD.e4cc795_propjoe-lkc3l_default_3a9b1759-4055-11e5-84ce-42010af01c62_45d1185b', 'pod_name:default/propjoe-lkc3l'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:haproxy-6db79c7bbcac01601ac35bcdb18868b3', 'kube_namespace:default', 'container_name:k8s_POD.e4cc795_haproxy-6db79c7bbcac01601ac35bcdb18868b3-rr7la_default_86527bf8-36cd-11e5-84ce-42010af01c62_5ad59bf3', 'pod_name:default/haproxy-6db79c7bbcac01601ac35bcdb18868b3-rr7la'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:haproxy-6db79c7bbcac01601ac35bcdb18868b3', 'kube_namespace:default', 'container_name:k8s_haproxy.69b6303b_haproxy-6db79c7bbcac01601ac35bcdb18868b3-rr7la_default_86527bf8-36cd-11e5-84ce-42010af01c62_a35b9731', 'pod_name:default/haproxy-6db79c7bbcac01601ac35bcdb18868b3-rr7la'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-ui-v1','kube_namespace:kube-system', 'container_name:k8s_kube-ui.c17839c_kube-ui-v1-sv2sq_kube-system_b7e8f250-3619-11e5-84ce-42010af01c62_d2b9aa90', 'pod_name:kube-system/kube-ui-v1-sv2sq'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:propjoe','kube_namespace:default', 'container_name:k8s_propjoe.21f63023_propjoe-lkc3l_default_3a9b1759-4055-11e5-84ce-42010af01c62_9fe8b7b0', 'pod_name:default/propjoe-lkc3l'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-dns-v8','kube_namespace:kube-system', 'container_name:k8s_healthz.4469a25d_kube-dns-v8-smhcb_kube-system_b80ffab3-3619-11e5-84ce-42010af01c62_241c34d1', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:fluentd-cloud-logging-kubernetes-minion','kube_namespace:kube-system', 'container_name:k8s_fluentd-cloud-logging.7721935b_fluentd-cloud-logging-kubernetes-minion-mu4w_kube-system_d0feac1ad02da9e97c4bf67970ece7a1_2c3c0879', 'pod_name:kube-system/fluentd-cloud-logging-kubernetes-minion-mu4w'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['container_name:dd-agent', 'pod_name:no_pod'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:l7-lb-controller', 'kube_namespace:kube-system'], [PODS]),
            (['kube_replication_controller:redis-slave', 'kube_namespace:default'], [PODS]),
            (['kube_replication_controller:frontend', 'kube_namespace:default'], [PODS]),
            (['kube_namespace:kube-system'], [PODS]),
            (['kube_replication_controller:heapster-v11', 'kube_namespace:kube-system'], [PODS]),
            ([], [LIM, REQ, CAP])  # container from kubernetes api doesn't have a corresponding entry in Cadvisor
        ]
        for m, _type in METRICS:
            for tags, types in expected_tags:
                if _type in types:
                    self.assertMetric(m, count=1, tags=tags)

        self.coverage_report()

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.1.json", sdk_dir=FIXTURE_DIR)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.1.json", sdk_dir=FIXTURE_DIR, string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def test_historate_1_1(self, *args):
        # To avoid the disparition of some gauges during the second check
        mocks = {
            '_perform_kubelet_checks': lambda x,y: None,
        }
        config = {
            "instances": [
                {
                    "host": "foo",
                    "enable_kubelet_checks": False,
                    "use_histogram": True,
                }
            ]
        }
        # Can't use run_check_twice due to specific metrics
        self.run_check_twice(config, mocks=mocks, force_reload=True)

        metric_suffix = ["count", "avg", "median", "max", "95percentile"]

        expected_tags = [
            (['pod_name:no_pod'], [MEM, CPU, NET, DISK, DISK_USAGE, NET_ERRORS]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'pod_name:default/propjoe-dhdzk'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:fluentd-cloud-logging-kubernetes-minion', 'kube_namespace:kube-system', 'pod_name:kube-system/fluentd-cloud-logging-kubernetes-minion-mu4w'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'pod_name:default/propjoe-dhdzk'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-ui-v1','kube_namespace:kube-system', 'pod_name:kube-system/kube-ui-v1-sv2sq'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'pod_name:default/propjoe-lkc3l'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:haproxy-6db79c7bbcac01601ac35bcdb18868b3', 'kube_namespace:default', 'pod_name:default/haproxy-6db79c7bbcac01601ac35bcdb18868b3-rr7la'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:l7-lb-controller', 'kube_namespace:kube-system'], [PODS]),
            (['kube_replication_controller:redis-slave', 'kube_namespace:default'], [PODS]),
            (['kube_replication_controller:frontend', 'kube_namespace:default'], [PODS]),
            (['kube_replication_controller:heapster-v11', 'kube_namespace:kube-system'], [PODS]),
            (['kube_namespace:kube-system'], [PODS]),
            ([], [LIM, REQ, CAP])  # container from kubernetes api doesn't have a corresponding entry in Cadvisor
        ]

        for m, _type in METRICS:
            for m_suffix in metric_suffix:
                for tags, types in expected_tags:
                    if _type in types:
                        self.assertMetric("{0}.{1}".format(m, m_suffix), count=1, tags=tags)

        self.coverage_report()

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info',
                side_effect=lambda: json.loads(Fixtures.read_file("machine_info_1.2.json", sdk_dir=FIXTURE_DIR)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.2.json", sdk_dir=FIXTURE_DIR)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", sdk_dir=FIXTURE_DIR, string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def test_fail_1_2(self, *args):
        # To avoid the disparition of some gauges during the second check
        config = {
            "instances": [{"host": "foo"}]
        }

        # Can't use run_check_twice due to specific metrics
        self.run_check(config, force_reload=True)
        self.assertServiceCheck("kubernetes.kubelet.check", status=AgentCheck.CRITICAL)

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info',
                side_effect=lambda: json.loads(Fixtures.read_file("machine_info_1.2.json", sdk_dir=FIXTURE_DIR)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.2.json", sdk_dir=FIXTURE_DIR)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", sdk_dir=FIXTURE_DIR, string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def test_metrics_1_2(self, *args):
        mocks = {
            '_perform_kubelet_checks': lambda x,y: None,
        }
        config = {
            "instances": [
                {
                    "host": "foo",
                    "enable_kubelet_checks": False
                }
            ]
        }
        # Can't use run_check_twice due to specific metrics
        self.run_check_twice(config, mocks=mocks, force_reload=True)

        expected_tags = [
            (['container_name:k8s_POD.35220667_dd-agent-1rxlh_default_12c7be82-33ca-11e6-ac8f-42010af00003_f5cf585f',
              'container_image:gcr.io/google_containers/pause:2.0', 'image_name:gcr.io/google_containers/pause',
              'image_tag:2.0', 'pod_name:dd-agent-1rxlh', 'kube_namespace:default', 'kube_app:dd-agent',
              'kube_foo:bar','kube_bar:baz', 'kube_replication_controller:dd-agent', 'kube_daemon_set:dd-agent', 'kube_container_name:POD'],
            [MEM, CPU, FS, NET, NET_ERRORS]),
            (['container_name:k8s_dd-agent.7b520f3f_dd-agent-1rxlh_default_12c7be82-33ca-11e6-ac8f-42010af00003_321fecb4',
              'container_image:datadog/docker-dd-agent:massi_ingest_k8s_events', 'image_name:datadog/docker-dd-agent',
              'image_tag:massi_ingest_k8s_events','pod_name:dd-agent-1rxlh',
              'kube_namespace:default', 'kube_app:dd-agent', 'kube_foo:bar',
              'kube_bar:baz', 'kube_replication_controller:dd-agent', 'kube_daemon_set:dd-agent', 'kube_container_name:dd-agent'], [LIM, REQ, MEM, CPU, NET, DISK, DISK_USAGE]),
            (['kube_replication_controller:dd-agent', 'kube_namespace:default', 'kube_daemon_set:dd-agent'], [PODS]),
            ([], [LIM, REQ, CAP])  # container from kubernetes api doesn't have a corresponding entry in Cadvisor
        ]

        for m, _type in METRICS:
            for tags, types in expected_tags:
                if _type in types:
                    self.assertMetric(m, count=1, tags=tags)

        # Verify exact capacity values read from machine_info_1.2.json fixture.
        self.assertMetric('kubernetes.cpu.capacity', value=2)
        self.assertMetric('kubernetes.memory.capacity', value=8391204864)

        self.coverage_report()

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info',
                side_effect=lambda: json.loads(Fixtures.read_file("machine_info_1.2.json", sdk_dir=FIXTURE_DIR)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.2.json", sdk_dir=FIXTURE_DIR)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", sdk_dir=FIXTURE_DIR, string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def test_historate_1_2(self, *args):
        # To avoid the disparition of some gauges during the second check
        mocks = {
            '_perform_kubelet_checks': lambda x,y: None,
        }
        config = {
            "instances": [
                {
                    "host": "foo",
                    "enable_kubelet_checks": False,
                    "use_histogram": True,
                }
            ]
        }

        # Can't use run_check_twice due to specific metrics
        self.run_check_twice(config, mocks=mocks, force_reload=True)

        metric_suffix = ["count", "avg", "median", "max", "95percentile"]

        expected_tags = [
            (['container_image:datadog/docker-dd-agent:massi_ingest_k8s_events', 'image_name:datadog/docker-dd-agent',
              'image_tag:massi_ingest_k8s_events', 'pod_name:dd-agent-1rxlh',
              'kube_namespace:default', 'kube_app:dd-agent', 'kube_foo:bar','kube_bar:baz',
              'kube_replication_controller:dd-agent', 'kube_daemon_set:dd-agent', 'kube_container_name:dd-agent'], [MEM, CPU, NET, DISK, DISK_USAGE, LIM, REQ]),
            (['container_image:gcr.io/google_containers/pause:2.0', 'image_name:gcr.io/google_containers/pause',
              'image_tag:2.0', 'pod_name:dd-agent-1rxlh',
              'kube_namespace:default', 'kube_app:dd-agent', 'kube_foo:bar','kube_bar:baz',
              'kube_replication_controller:dd-agent', 'kube_daemon_set:dd-agent', 'kube_container_name:POD'], [MEM, CPU, NET, NET_ERRORS, DISK_USAGE]),
            (['kube_replication_controller:dd-agent', 'kube_namespace:default', 'kube_daemon_set:dd-agent'], [PODS]),
            ([], [LIM, REQ, CAP])  # container from kubernetes api doesn't have a corresponding entry in Cadvisor
        ]

        for m, _type in METRICS:
            for m_suffix in metric_suffix:
                for tags, types in expected_tags:
                    if _type in types:
                        self.assertMetric("{0}.{1}".format(m, m_suffix), count=1, tags=tags)

        self.coverage_report()

    @mock.patch('utils.kubernetes.KubeUtil.get_node_info',
                side_effect=lambda: ('Foo', 'Bar'))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth',
            side_effect=KubeUtil_fake_retrieve_json_auth)
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", sdk_dir=FIXTURE_DIR, string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def test_events(self, *args):
        # default value for collect_events is False
        config = {'instances': [{'host': 'foo'}]}
        self.run_check(config, force_reload=True)
        self.assertEvent('hello-node-47289321-91tfd Scheduled on Bar', count=0, exact_match=False)

        # again, with the feature enabled
        config = {'instances': [{'host': 'bar', 'collect_events': True}]}
        self.run_check(config, force_reload=True)
        self.assertEvent('hello-node-47289321-91tfd Scheduled on Bar', count=1, exact_match=False)

        # with no namespaces, only catch event from 'default'
        self.assertEvent('dd-agent-a769 SuccessfulDelete on Bar', count=0, exact_match=False)

        # again, now the timestamp is set and the event is discarded b/c too old
        self.run_check(config)
        self.assertEvent('hello-node-47289321-91tfd Scheduled on Bar', count=0, exact_match=False)

    @mock.patch('utils.kubernetes.KubeUtil.get_node_info',
                side_effect=lambda: ('Foo', 'Bar'))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth',
            side_effect=KubeUtil_fake_retrieve_json_auth)
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list')
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def test_namespaced_events(self, *args):
        # reset last event pulling time
        KubeUtil().last_event_collection_ts = 0

        # Verify that we are retro compatible with the old 'namespace' configuration key
        config = {'instances': [{'host': 'bar', 'collect_events': True, 'namespace': 'test-namespace-1'}]}
        self.run_check(config, force_reload=True)
        self.assertEvent('dd-agent-a769 SuccessfulDelete on Bar', count=1, exact_match=False)
        self.assertEvent('hello-node-47289321-91tfd Scheduled on Bar', count=1, exact_match=False)

        # reset last event pulling time
        KubeUtil().last_event_collection_ts = 0

        # Using 'namespaces' list
        config = {'instances': [{'host': 'bar', 'collect_events': True, 'namespaces': ['test-namespace-1', 'test-namespace-2']}]}
        self.run_check(config, force_reload=True)
        self.assertEvent('dd-agent-a769 SuccessfulDelete on Bar', count=1, exact_match=False)
        self.assertEvent('hello-node-47289321-91tfd Scheduled on Bar', count=0, exact_match=False)

        # reset last event pulling time
        KubeUtil().last_event_collection_ts = 0

        # Using 'namespace_name_regexp' (since 'namespaces' is not set it should
        # fallback to ['default'] and add any namespaces that matched with the regexp
        config = {'instances': [{'host': 'bar', 'collect_events': True, 'namespace_name_regexp': 'test-namespace.*'}]}
        self.run_check(config, force_reload=True)
        self.assertEvent('dd-agent-a769 SuccessfulDelete on Bar', count=1, exact_match=False)
        self.assertEvent('hello-node-47289321-91tfd Scheduled on Bar', count=1, exact_match=False)

        # reset last event pulling time
        KubeUtil().last_event_collection_ts = 0

        # muting the 'default' namespace
        config = {'instances': [{'host': 'bar', 'collect_events': True, 'namespaces': [], 'namespace_name_regexp': 'test-namespace.*'}]}
        self.run_check(config, force_reload=True)
        self.assertEvent('dd-agent-a769 SuccessfulDelete on Bar', count=1, exact_match=False)
        self.assertEvent('hello-node-47289321-91tfd Scheduled on Bar', count=0, exact_match=False)

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics',
                side_effect=Exception("Connection error"))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=Exception("Connection error"))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def test_kubelet_fail(self, *args):
        # To avoid the disparition of some gauges during the second check
        config = {
            "instances": [{"host": "foo"}]
        }

        # Can't use run_check_twice due to specific metrics
        self.run_check(config, force_reload=True)
        self.assertServiceCheck("kubernetes.kubelet.check", status=AgentCheck.CRITICAL, tags=None, count=1)

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics',
                side_effect=Exception("Connection error"))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=Exception("Connection error"))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def test_fail_service_check_tagging(self, *args):
        # To avoid the disparition of some gauges during the second check
        config = {
            "instances": [{"host": "foo", "tags":["tag:foo","tag:bar"]}]
        }

        # Can't use run_check_twice due to specific metrics
        self.run_check(config, force_reload=True)
        self.assertServiceCheck("kubernetes.kubelet.check", status=AgentCheck.CRITICAL, tags=["tag:foo","tag:bar"], count=1)

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics',
                side_effect=Exception("Connection error"))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=Exception("Connection error"))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet',
                return_value='http://172.17.0.1:10255')
    @mock.patch('utils.kubernetes.KubeUtil.perform_kubelet_query',
                return_value=MockIterLinesResponse(["[+]ping ok","healthz check passed"], 200))
    def test_ok_service_check_tagging(self, *args):
        # To avoid the disparition of some gauges during the second check
        config = {
            "instances": [{"host": "foo", "tags":["tag:foo","tag:bar"]}]
        }

        # Can't use run_check_twice due to specific metrics
        self.run_check(config, force_reload=True)

        self.assertServiceCheck("kubernetes.kubelet.check", status=AgentCheck.OK, tags=["tag:foo","tag:bar"], count=1)
        self.assertServiceCheck("kubernetes.kubelet.check.ping", status=AgentCheck.OK, tags=["tag:foo","tag:bar"], count=1)


    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_metrics',
                side_effect=Exception("Connection error"))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=Exception("Connection error"))
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet',
                return_value='http://172.17.0.1:10255')
    @mock.patch('utils.kubernetes.KubeUtil.perform_kubelet_query',
                return_value=MockIterLinesResponse(["[-]ping failed: reason withheld",
                                                   "healthz check failed"], 200))
    def test_critical_service_check_tagging(self, *args):
        # To avoid the disparition of some gauges during the second check
        config = {
            "instances": [{"host": "foo", "tags":["tag:foo","tag:bar"]}]
        }

        # Can't use run_check_twice due to specific metrics
        self.run_check(config, force_reload=True)

        self.assertServiceCheck("kubernetes.kubelet.check", status=AgentCheck.CRITICAL, tags=["tag:foo","tag:bar"], count=1)
        self.assertServiceCheck("kubernetes.kubelet.check.ping", status=AgentCheck.CRITICAL, tags=["tag:foo","tag:bar"], count=1)


@attr(requires='kubernetes')
class TestKubeutil(unittest.TestCase):
    @mock.patch('utils.kubernetes.KubeUtil._locate_kubelet', return_value='http://172.17.0.1:10255')
    def setUp(self, _locate_kubelet):
        self.kubeutil = KubeUtil()
        self.kubeutil.__init__()  # It's a singleton, force re-init

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list', side_effect=['foo'])
    @mock.patch('utils.kubernetes.KubeUtil.extract_kube_pod_tags')
    def test_get_kube_pod_tags(self, extract_kube_pod_tags, retrieve_pods_list):
        self.kubeutil.get_kube_pod_tags(excluded_keys='bar')
        retrieve_pods_list.assert_called_once()
        extract_kube_pod_tags.assert_called_once_with('foo', excluded_keys='bar')

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('utils.kubernetes.kubeutil.KubeUtil.get_auth_token', return_value='tkn')
    def test_init_tls_settings(self, *args):
        # kubelet
        instances = [
            # (instance, expected_result)
            ({}, {'kubelet_verify': True, 'bearer_token': 'tkn'}),
            ({'kubelet_tls_verify': False}, {'kubelet_verify': False, 'bearer_token': 'tkn'}),
            ({'kubelet_tls_verify': True}, {'kubelet_verify': True, 'bearer_token': 'tkn'}),
            ({'kubelet_tls_verify': 'foo.pem'}, {'kubelet_verify': 'foo.pem', 'bearer_token': 'tkn'}),
            ({'kubelet_cert': 'foo.pem'}, {'kubelet_verify': 'foo.pem', 'bearer_token': 'tkn'}),
            ({'kubelet_client_crt': 'client.crt', 'kubelet_client_key': 'client.key'},
                {'kubelet_verify': True, 'kubelet_client_cert': ('client.crt', 'client.key'), 'bearer_token': 'tkn'}),
            ({'kubelet_tls_verify': True, 'kubelet_client_crt': 'client.crt'}, {'kubelet_verify': True, 'bearer_token': 'tkn'}),
            ({'kubelet_client_crt': 'client.crt'}, {'kubelet_verify': True, 'bearer_token': 'tkn'})
        ]
        for instance, result in instances:
            self.assertEqual(self.kubeutil._init_tls_settings(instance), result)

        # apiserver
        instance = {'apiserver_client_crt': 'foo.crt', 'apiserver_client_key': 'foo.key'}
        expected_res = {'apiserver_client_cert': ('foo.crt', 'foo.key'), 'kubelet_verify': True, 'bearer_token': 'tkn'}
        self.assertEqual(self.kubeutil._init_tls_settings(instance), expected_res)
        with mock.patch('utils.kubernetes.kubeutil.os.path.exists', return_value=False):
            self.assertEqual(self.kubeutil._init_tls_settings(instance), {'kubelet_verify': True, 'bearer_token': 'tkn'})

        self.assertEqual(self.kubeutil._init_tls_settings(
            {'apiserver_client_crt': 'foo.crt'}), {'kubelet_verify': True, 'bearer_token': 'tkn'})

    ##### Test _locate_kubelet #####

    # we support connection to kubelet in 3 modes
    # -  no auth/no  ssl  --> over the --no-auth port
    # -  no auth/yes ssl (no verify)  --> over the port used by apiserver if anonymous requests are accepted
    # -  yes auth/yes ssl (yes verify)  --> same, but the user provided a way to verify kubelet's
    #                                       cert and we attach a bearer token if available

    @mock.patch('utils.kubernetes.kubeutil.DockerUtil.get_hostname', return_value='test_docker_host')
    def test_locate_kubelet_no_auth_no_ssl(self, _get_hostname):
        no_auth_no_ssl_instances = [
            # instance, expected_result
            ({}, 'http://test_docker_host:10255'),
            ({'host': 'test_explicit_host'}, 'http://test_explicit_host:10255'),
            ({'kubelet_port': '1337'}, 'http://test_docker_host:1337'),
            ({'host': 'test_explicit_host', 'kubelet_port': '1337'}, 'http://test_explicit_host:1337')
        ]
        with mock.patch('utils.kubernetes.kubeutil.KubeUtil.perform_kubelet_query', return_value=True):
            for instance, result in no_auth_no_ssl_instances:
                self.assertEqual(self.kubeutil._locate_kubelet(instance), result)

    @mock.patch('utils.kubernetes.kubeutil.DockerUtil.get_hostname', return_value='test_docker_host')
    def test_locate_kubelet_no_auth_no_verify(self, _get_hostname):
        no_auth_no_verify_instances = [
            # instance, expected_result
            ({}, 'https://test_docker_host:10250'),
            ({'kubelet_port': '1337'}, 'https://test_docker_host:1337'),
            ({'host': 'test_explicit_host'}, 'https://test_explicit_host:10250'),
            ({'host': 'test_explicit_host', 'kubelet_port': '1337'}, 'https://test_explicit_host:1337'),
        ]

        def side_effect(url):
            """Mock KubeUtil.perform_kubelet_query"""
            if url.startswith('https://'):
                return True
            else:
                raise Exception()

        with mock.patch('utils.kubernetes.kubeutil.KubeUtil.perform_kubelet_query', side_effect=side_effect):
            for instance, result in no_auth_no_verify_instances:
                self.assertEqual(self.kubeutil._locate_kubelet(instance), result)

    @mock.patch('utils.kubernetes.kubeutil.DockerUtil.get_hostname', return_value='test_docker_host')
    @mock.patch('utils.kubernetes.kubeutil.KubeUtil.get_node_hostname', return_value='test_k8s_host')
    @mock.patch('utils.kubernetes.kubeutil.KubeUtil.get_auth_token', return_value='foo')
    def test_locate_kubelet_verify_and_auth(self, *args):
        """
        Test kubelet connection with TLS. Also look for auth token.
        """
        no_auth_instances = [
            # instance, tls_settings, expected_result
            (
                {},
                {'bearer_token': 'foo', 'kubelet_verify': True},
                'https://test_k8s_host:10250'),
            (
                {'kubelet_port': '1337'},
                {'bearer_token': 'foo', 'kubelet_verify': 'test.pem'},
                'https://test_k8s_host:1337'),
            (
                {'host': 'test_explicit_host'},
                {'bearer_token': 'foo', 'kubelet_verify': True, 'kubelet_client_cert': ('client.crt', 'client.key')},
                'https://test_explicit_host:10250'
            ),
            (
                {'host': 'test_explicit_host', 'kubelet_port': '1337'},
                {'bearer_token': 'foo', 'kubelet_verify': True},
                'https://test_explicit_host:1337'
            ),
        ]

        def side_effect(url, **kwargs):
            """Mock KubeUtil.perform_kubelet_query"""
            if url.startswith('https://') and '10255' not in url:
                return True
            else:
                raise Exception()

        # no auth / TLS with verify
        for instance, tls_settings, result in no_auth_instances:
            with mock.patch('utils.kubernetes.kubeutil.requests') as req:
                req.get = mock.MagicMock(side_effect=side_effect)
                self.kubeutil.tls_settings = tls_settings
                self.assertEqual(self.kubeutil._locate_kubelet(instance), result)
                req.get.assert_called_with(result + '/healthz',  # test endpoint
                    timeout=10,
                    verify=tls_settings.get('kubelet_verify', True),
                    headers={'Authorization': 'Bearer foo'} if 'kubelet_client_cert' not in tls_settings else None,
                    cert=tls_settings.get('kubelet_client_cert'),
                    params={'verbose': True}
                )

    @mock.patch('utils.kubernetes.kubeutil.KubeUtil.get_auth_token', return_value='foo')
    def test_get_node_hostname(self, _get_auth_tkn):
        node_lists = [
            (json.loads(Fixtures.read_file('filtered_node_list_1_4.json', sdk_dir=FIXTURE_DIR, string_escape=False)), 'ip-10-0-0-179'),
            ({'items': [{'foo': 'bar'}]}, None),
            ({'items': []}, None),
            ({'items': [{'foo': 'bar'}, {'bar': 'foo'}]}, None)
        ]

        for node_list, expected_result in node_lists:
            with mock.patch('utils.kubernetes.kubeutil.KubeUtil.retrieve_json_auth', return_value=MockResponse(node_list, 200)):
                self.assertEqual(self.kubeutil.get_node_hostname('ip-10-0-0-179'), expected_result)

    def test_extract_kube_pod_tags(self):
        """
        Test kube_pod_tags with both 1.1 and 1.2 version payloads
        """
        res = self.kubeutil.extract_kube_pod_tags({}, ['foo'])
        self.assertEqual(len(res), 0)

        pods = json.loads(Fixtures.read_file("pods_list_1.1.json", sdk_dir=FIXTURE_DIR, string_escape=False))
        res = self.kubeutil.extract_kube_pod_tags(pods, ['foo'])
        labels = set(inn for out in res.values() for inn in out)
        self.assertEqual(len(labels), 8 + 4)
        res = self.kubeutil.extract_kube_pod_tags(pods, ['k8s-app'])
        labels = set(inn for out in res.values() for inn in out)
        self.assertEqual(len(labels), 6 + 4)

        pods = json.loads(Fixtures.read_file("pods_list_1.2.json", sdk_dir=FIXTURE_DIR, string_escape=False))
        res = self.kubeutil.extract_kube_pod_tags(pods, ['foo'])
        labels = set(inn for out in res.values() for inn in out)
        self.assertEqual(len(labels), 3 + 1)
        res = self.kubeutil.extract_kube_pod_tags(pods, ['k8s-app'])
        labels = set(inn for out in res.values() for inn in out)
        self.assertEqual(len(labels), 3 + 1)

    @mock.patch('utils.kubernetes.kubeutil.KubeUtil.perform_kubelet_query')
    def test_retrieve_pods_list(self, retrieve_pods):
        self.kubeutil.retrieve_pods_list()
        self.assertTrue(retrieve_pods.call_args_list[0].endswith('/pods/'))

    @mock.patch('utils.kubernetes.kubeutil.retrieve_json')
    def test_retrieve_machine_info(self, retrieve_json):
        self.kubeutil.retrieve_machine_info()
        retrieve_json.assert_called_once_with(self.kubeutil.machine_info_url)

    @mock.patch('utils.kubernetes.kubeutil.retrieve_json')
    def test_retrieve_metrics(self, retrieve_json):
        self.kubeutil.retrieve_metrics()
        retrieve_json.assert_called_once_with(self.kubeutil.metrics_url)

    @mock.patch('utils.kubernetes.kubeutil.requests')
    def test_perform_kubelet_query(self, req):
        base_params = {'timeout': 10, 'verify': False,
            'params': {'verbose': True}, 'cert': None, 'headers': None}

        auth_token_header = {'headers': {'Authorization': 'Bearer foo'}}
        verify_true = {'verify': True}
        verify_cert = {'verify': 'kubelet.pem'}
        client_cert = {'cert': ('client.crt', 'client.key')}

        instances = [
            ('http://test.com', {'bearer_token': 'foo'}, dict(base_params.items() + verify_true.items())),
            ('https://test.com', {'bearer_token': 'foo'}, dict(base_params.items() + verify_true.items() + auth_token_header.items())),
            ('https://test.com', {'bearer_token': 'foo', 'kubelet_verify': True}, dict(base_params.items() + verify_true.items() + auth_token_header.items())),
            ('https://test.com', {'bearer_token': 'foo', 'kubelet_verify': 'kubelet.pem'}, dict(base_params.items() + verify_cert.items() + auth_token_header.items())),
            ('https://test.com', {'bearer_token': 'foo', 'kubelet_client_cert': ('client.crt', 'client.key')},
                dict(base_params.items() + verify_true.items() + client_cert.items())),
        ]
        for url, ssl_context, expected_params in instances:
            req.get.reset_mock()
            self.kubeutil.tls_settings = ssl_context
            self.kubeutil.perform_kubelet_query(url)
            req.get.assert_called_with(url, **expected_params)

    @mock.patch('utils.kubernetes.kubeutil.requests')
    def test_retrieve_json_auth(self, r):
        instances = [
            # tls_settings, expected_params
            (
                {},
                {'verify': False, 'timeout': 3, 'params': None, 'headers': {'content-type': 'application/json'}, 'cert': None}
            ), (
                {'bearer_token': 'foo_tok'},
                {'verify': False, 'timeout': 3, 'params': None, 'headers': {'Authorization': 'Bearer foo_tok', 'content-type': 'application/json'}, 'cert': None}
            ), (
                {'bearer_token': 'foo_tok','apiserver_client_cert': ('foo.crt', 'foo.key')},
                {'verify': False, 'timeout': 3, 'params': None, 'headers': {'content-type': 'application/json'}, 'cert': ('foo.crt', 'foo.key')}
            ),
        ]

        for tls_settings, expected_params in instances:
            r.get.reset_mock()
            self.kubeutil.tls_settings = tls_settings
            self.kubeutil.retrieve_json_auth('url')
            r.get.assert_called_once_with('url', **expected_params)

        r.get.reset_mock()
        self.kubeutil.tls_settings = {'bearer_token': 'foo_tok'}
        self.kubeutil.CA_CRT_PATH = __file__
        self.kubeutil.retrieve_json_auth('url')
        r.get.assert_called_with('url', verify=__file__, timeout=3, params=None, headers={'Authorization': 'Bearer foo_tok', 'content-type': 'application/json'}, cert=None)

    def test_get_node_info(self):
        with mock.patch('utils.kubernetes.KubeUtil._fetch_host_data') as f:
            self.kubeutil._node_ip = None
            self.kubeutil._node_name = None
            self.kubeutil.get_node_info()
            f.assert_called_once()

            f.reset_mock()

            self.kubeutil._node_ip = 'foo'
            self.kubeutil._node_name = 'bar'
            ip, name = self.kubeutil.get_node_info()
            self.assertEqual(ip, 'foo')
            self.assertEqual(name, 'bar')
            f.assert_not_called()

    def test__fetch_host_data_1_1(self):
        """
        Test with 1.1 version payload
        """
        with mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list') as mock_pods:
            self.kubeutil.pod_name = 'heapster-v11-l8sh1'
            mock_pods.return_value = json.loads(Fixtures.read_file("pods_list_1.1.json", sdk_dir=FIXTURE_DIR, string_escape=False))
            self.kubeutil._fetch_host_data()
            self.assertEqual(self.kubeutil._node_ip, '10.240.0.9')
            self.assertEqual(self.kubeutil._node_name, 'gke-cluster-1-8046fdfa-node-ld35')

    def test__fetch_host_data_1_2(self):
        """
        Test with 1.2 version payload
        """
        with mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list') as mock_pods:
            self.kubeutil.pod_name = 'dd-agent-1rxlh'
            mock_pods.return_value = json.loads(Fixtures.read_file("pods_list_1.2.json", sdk_dir=FIXTURE_DIR, string_escape=False))
            self.kubeutil._fetch_host_data()
            self.assertEqual(self.kubeutil._node_ip, '10.240.0.9')
            self.assertEqual(self.kubeutil._node_name, 'kubernetes-massi-minion-k23m')

    def test_get_auth_token(self):
        KubeUtil.AUTH_TOKEN_PATH = '/foo/bar'
        self.assertIsNone(KubeUtil.get_auth_token({}))
        KubeUtil.AUTH_TOKEN_PATH = Fixtures.file('events.json', sdk_dir=FIXTURE_DIR,)  # any file could do the trick
        self.assertIsNotNone(KubeUtil.get_auth_token({}))

    def test_is_k8s(self):
        os.unsetenv('KUBERNETES_PORT')
        self.assertFalse(detect_is_k8s())
        os.environ['KUBERNETES_PORT'] = '999'
        self.assertTrue(detect_is_k8s())

    def test_extract_event_tags(self):
        events = json.loads(Fixtures.read_file("events.json", sdk_dir=FIXTURE_DIR, string_escape=False))['items']
        for ev in events:
            tags = KubeUtil().extract_event_tags(ev)
            # there should be 6 tags except for some events where source.host is missing
            self.assertTrue(len(tags) >= 5)

            tag_names = [tag.split(':')[0] for tag in tags]
            self.assertIn('reason', tag_names)
            self.assertIn('namespace', tag_names)
            self.assertIn('object_type', tag_names)
            self.assertIn('object_name', tag_names)
            self.assertIn('source_component', tag_names)
            if len(tags) == 6:
                self.assertIn('node_name', tag_names)
