# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import sys

import mock
import pytest
import requests_mock
from requests.exceptions import HTTPError

from datadog_checks.kubelet import KubeletCheck

from .test_kubelet import EXPECTED_METRICS_COMMON, NODE_SPEC, mock_from_file

# Skip the whole tests module on Windows
pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='tests for linux only')

EXPECTED_METRICS_CADVISOR = ['kubernetes.network_errors', 'kubernetes.diskio.io_service_bytes.stats.total']


@pytest.fixture()
def mock_request():
    with requests_mock.Mocker() as m:
        yield m


@pytest.fixture
def tagger():
    from datadog_checks.base.stubs import tagger

    tagger.reset()
    # We filter out slices unknown by the tagger, mock a non-empty taglist
    tagger.set_default_tags(["foo:bar"])
    return tagger


def test_detect_cadvisor_nominal(mock_request):
    mock_request.head('http://kubelet:4192/api/v1.3/subcontainers/', text='{}')
    url = KubeletCheck.detect_cadvisor("http://kubelet:10250", 4192)
    assert url == "http://kubelet:4192/api/v1.3/subcontainers/"


def test_detect_cadvisor_404(mock_request):
    mock_request.head('http://kubelet:4192/api/v1.3/subcontainers/', status_code=404)
    with pytest.raises(HTTPError):
        url = KubeletCheck.detect_cadvisor("http://kubelet:10250", 4192)
        assert url == ""


def test_detect_cadvisor_port_zero():
    with pytest.raises(ValueError):
        url = KubeletCheck.detect_cadvisor("http://kubelet:10250", 0)
        assert url == ""


def test_kubelet_check_cadvisor(monkeypatch, aggregator, tagger):
    instance_with_tag = {"tags": ["instance:tag"], "cadvisor_port": 4194}
    cadvisor_url = "http://valid:port/url"
    check = KubeletCheck('kubelet', {}, [instance_with_tag])
    monkeypatch.setattr(
        check, 'retrieve_pod_list', mock.Mock(return_value=json.loads(mock_from_file('pods_list_1.2.json')))
    )
    mock_resp = mock.Mock(status_code=200, raise_for_status=mock.Mock())
    mock_resp.json = mock.Mock(return_value=NODE_SPEC)
    monkeypatch.setattr(check, '_retrieve_node_spec', mock.Mock(return_value=mock_resp))
    monkeypatch.setattr(
        check, '_retrieve_stats', mock.Mock(return_value=json.loads(mock_from_file('stats_summary.json')))
    )
    monkeypatch.setattr(check, '_perform_kubelet_check', mock.Mock(return_value=None))
    monkeypatch.setattr(
        check, '_retrieve_cadvisor_metrics', mock.Mock(return_value=json.loads(mock_from_file('cadvisor_1.2.json')))
    )
    monkeypatch.setattr(check, 'detect_cadvisor', mock.Mock(return_value=cadvisor_url))
    monkeypatch.setattr(check, 'process', mock.Mock(return_value=None))

    check.check(instance_with_tag)
    assert check.cadvisor_legacy_url == cadvisor_url
    check.retrieve_pod_list.assert_called_once()
    check._retrieve_node_spec.assert_called_once()
    check._retrieve_stats.assert_called_once()
    check._retrieve_cadvisor_metrics.assert_called_once()
    check._perform_kubelet_check.assert_called_once()

    # called twice so pct metrics are guaranteed to be there
    check.check(instance_with_tag)
    for metric in EXPECTED_METRICS_COMMON:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, "instance:tag")
    for metric in EXPECTED_METRICS_CADVISOR:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, "instance:tag")

    assert aggregator.metrics_asserted_pct == 100.0
