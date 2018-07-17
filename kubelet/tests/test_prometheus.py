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
    scraper.pod_list = json.loads(mock_from_file('pods.json'))

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


def test_get_container_id():
    labels = [
        Label("container_name", value="datadog-agent"),
        Label("id",
              value="/kubepods/burstable/"
                    "podc2319815-10d0-11e8-bd5a-42010af00137/"
                    "a335589109ce5506aa69ba7481fc3e6c943abd23c5277016c92dac15d0f40479"),
    ]
    container_id = CadvisorPrometheusScraper._get_container_id(labels)
    assert container_id == "a335589109ce5506aa69ba7481fc3e6c943abd23c5277016c92dac15d0f40479"
    assert CadvisorPrometheusScraper._get_container_id([]) is None


def test_get_pod_uid():
    labels = [
        Label("container_name", value="POD"),
        Label("id",
              value="/kubepods/burstable/"
                    "pod260c2b1d43b094af6d6b4ccba082c2db/"
                    "0bce0ef7e6cd073e8f9cec3027e1c0057ce1baddce98113d742b816726a95ab1"),
    ]
    assert CadvisorPrometheusScraper._get_pod_uid(labels) == "260c2b1d43b094af6d6b4ccba082c2db"
    assert CadvisorPrometheusScraper._get_pod_uid([]) is None


def test_is_pod_host_networked(monkeypatch, cadvisor_scraper):
    assert len(cadvisor_scraper.pod_list) == 4
    assert cadvisor_scraper._is_pod_host_networked("not-here") is False
    assert cadvisor_scraper._is_pod_host_networked('260c2b1d43b094af6d6b4ccba082c2db') is True
    assert cadvisor_scraper._is_pod_host_networked('2edfd4d9-10ce-11e8-bd5a-42010af00137') is False


def test_get_pod_by_metric_label(monkeypatch, cadvisor_scraper):
    assert len(cadvisor_scraper.pod_list) == 4
    kube_proxy = cadvisor_scraper._get_pod_by_metric_label([
        Label("container_name", value="POD"),
        Label("id",
              value="/kubepods/burstable/"
                    "pod260c2b1d43b094af6d6b4ccba082c2db/"
                    "0bce0ef7e6cd073e8f9cec3027e1c0057ce1baddce98113d742b816726a95ab1"),
    ])
    fluentd = cadvisor_scraper._get_pod_by_metric_label([
        Label("container_name", value="POD"),
        Label("id",
              value="/kubepods/burstable/"
                    "pod2edfd4d9-10ce-11e8-bd5a-42010af00137/"
                    "7990c0e549a1a578b1313475540afc53c91081c32e735564da6244ddf0b86030"),
    ])
    assert kube_proxy["metadata"]["name"] == "kube-proxy-gke-haissam-default-pool-be5066f1-wnvn"
    assert fluentd["metadata"]["name"] == "fluentd-gcp-v2.0.10-9q9t4"


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
