# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import sys
from collections import namedtuple

import pytest
from datadog_checks.kubelet import KubeletCheck
from datadog_checks.kubelet.prometheus import CadvisorPrometheusScraper
from datadog_checks.kubelet.common import PodListUtils

# Skip the whole tests module on Windows
pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='tests for linux only')

# Constants
HERE = os.path.abspath(os.path.dirname(__file__))

Label = namedtuple('Label', 'name value')


class MockMetric(object):
    def __init__(self, name, labels=None, value=None):
        self.name = name
        self.label = labels if labels else []
        self.value = value


def mock_from_file(fname):
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return f.read()


@pytest.fixture
def check():
    return KubeletCheck('kubelet', None, {}, [{}])


@pytest.fixture
def cadvisor_scraper(check):
    scraper = CadvisorPrometheusScraper(check)
    pod_list = json.loads(mock_from_file('podlist_containerd.json'))
    scraper.pod_list = pod_list
    scraper.pod_list_utils = PodListUtils(pod_list)

    return scraper


def test_cadvisor_default_options():
    check = KubeletCheck('kubelet', None, {}, [{}])
    scraper = CadvisorPrometheusScraper(check)
    assert scraper.NAMESPACE == 'kubernetes'
    assert scraper.fs_usage_bytes == {}
    assert scraper.mem_usage_bytes == {}
    assert scraper.metrics_mapper == {}


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
        assert CadvisorPrometheusScraper._is_container_metric(metric.label) is False

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
    assert CadvisorPrometheusScraper._is_container_metric(true_metric.label) is True


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
        assert CadvisorPrometheusScraper._is_pod_metric(metric.label) is False

    for metric in true_metrics:
        assert CadvisorPrometheusScraper._is_pod_metric(metric.label) is True


def test_get_container_label():
    labels = [
        Label("container_name", value="POD"),
        Label("id", value="/kubepods/burstable/pod531c80d9-9fc4-11e7-ba8b-42010af002bb"),
    ]
    assert CadvisorPrometheusScraper._get_container_label(labels, "container_name") == "POD"
    assert CadvisorPrometheusScraper._get_container_label([], "not-in") is None


def test_get_container_id(cadvisor_scraper):
    labels = [
        Label("container_name", value="datadog-agent"),
        Label("namespace", value="default"),
        Label("pod_name", value="datadog-agent-pbqt2"),
        Label("container_name", value="datadog-agent"),
    ]
    container_id = cadvisor_scraper._get_container_id(labels)
    assert container_id == "containerd://51cba2ca229069039575750d44ed3a67e9b5ead651312ba7ff218dd9202fde64"
    assert cadvisor_scraper._get_container_id([]) is None


def test_get_pod_uid(cadvisor_scraper):
    labels = [
        Label("container_name", value="POD"),
        Label("namespace", value="default"),
        Label("pod_name", value="datadog-agent-pbqt2"),
    ]
    assert cadvisor_scraper._get_pod_uid(labels) == "b66c40af-997d-11e8-96a3-42010a840157"
    assert cadvisor_scraper._get_pod_uid([]) is None


def test_is_pod_host_networked(cadvisor_scraper):
    assert len(cadvisor_scraper.pod_list) == 4
    assert cadvisor_scraper._is_pod_host_networked("not-here") is False
    assert cadvisor_scraper._is_pod_host_networked('8abf1ed0-94c4-11e8-96a3-42010a840157') is True
    assert cadvisor_scraper._is_pod_host_networked('b66c40af-997d-11e8-96a3-42010a840157') is False


def test_get_pod_by_metric_label(cadvisor_scraper):
    assert len(cadvisor_scraper.pod_list) == 4
    kube_proxy = cadvisor_scraper._get_pod_by_metric_label([
        Label("container_name", value="POD"),
        Label("namespace", value="kube-system"),
        Label("pod_name", value="kube-proxy-2d2bq")
    ])
    fluentd = cadvisor_scraper._get_pod_by_metric_label([
        Label("container_name", value="POD"),
        Label("namespace", value="kube-system"),
        Label("pod_name", value="fluentd-gcp-v3.0.0-z55q5")
    ])
    assert kube_proxy["metadata"]["uid"] == "8abf1ed0-94c4-11e8-96a3-42010a840157"
    assert fluentd["metadata"]["uid"] == "fe3d57c4-94c4-11e8-96a3-42010a840157"


def test_get_kube_container_name():
    tags = CadvisorPrometheusScraper._get_kube_container_name([
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

    tags = CadvisorPrometheusScraper._get_kube_container_name([])
    assert tags == []
