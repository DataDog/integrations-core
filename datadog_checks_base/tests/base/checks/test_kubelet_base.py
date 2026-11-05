# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import gzip
import io
import json
import os
from datetime import datetime, timezone

import mock
import pytest
import requests
import urllib3

from datadog_checks.base.checks.kubelet_base.base import KubeletBase, KubeletCredentials, urljoin
from datadog_checks.base.stubs.http import RecordedRequest
from datadog_checks.dev import get_here

pytestmark = pytest.mark.usefixtures('agnostic_http')

HERE = get_here()


def get_fixture_path(filename):
    return os.path.join(HERE, '..', '..', 'fixtures', filename)


def mock_from_file(filename):
    with open(get_fixture_path(filename)) as f:
        return f.read()


def test_retrieve_pod_list_success(monkeypatch, mock_http_response):
    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = "dummyurl"
    monkeypatch.setattr(
        check, 'perform_kubelet_query', mock_http_response(file_path=get_fixture_path('kubelet_base/pod_list_raw.dat'))
    )

    retrieved = check.retrieve_pod_list()
    expected = json.loads(mock_from_file("kubelet_base/pod_list_raw.json"))
    assert json.dumps(retrieved, sort_keys=True) == json.dumps(expected, sort_keys=True)


@pytest.mark.parametrize(
    'credentials, expected_options',
    [
        pytest.param(
            {'token': 'tkn', 'ca_cert': '/ca.pem', 'client_crt': '/crt.pem', 'client_key': '/key.pem'},
            {'verify': '/ca.pem', 'cert': ('/crt.pem', '/key.pem'), 'headers': None},
            id='client-cert-wins-over-token',
        ),
        pytest.param(
            {'token': 'tkn'},
            {'verify': None, 'cert': None, 'headers': {'Authorization': 'Bearer tkn'}},
            id='bearer-token',
        ),
    ],
)
@pytest.mark.parametrize('verbose', [True, False], ids=['verbose', 'terse'])
def test_perform_kubelet_query_forwards_credentials_and_verbosity(
    fake_http, fake_http_response, credentials, expected_options, verbose
):
    url = 'https://kubelet:10250/healthz'
    fake_http_response(url, b'ok', status_code=200)
    check = KubeletBase('kubelet', {}, [{}])
    check.kubelet_credentials = KubeletCredentials(credentials)

    assert check.perform_kubelet_query(url, verbose=verbose).content == b'ok'

    fake_http.assert_requests(
        [
            RecordedRequest(
                method='GET',
                url=url,
                options={**expected_options, 'params': {'verbose': verbose}, 'stream': False},
            )
        ]
    )
    fake_http.assert_all_responses_consumed()


@pytest.mark.parametrize('expiration_duration', ['0', '900'], ids=['no_expiration_filter', 'expiration_filter'])
def test_retrieve_pod_list_decodes_a_gzip_encoded_body(monkeypatch, expiration_duration):
    pod_list = {'items': [{'metadata': {'name': 'pod'}}]}
    response = requests.Response()
    response.status_code = 200
    response.headers['Content-Encoding'] = 'gzip'
    response.raw = urllib3.HTTPResponse(
        body=io.BytesIO(gzip.compress(json.dumps(pod_list).encode())),
        headers={'Content-Encoding': 'gzip'},
        preload_content=False,
        decode_content=False,
    )
    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = "dummyurl"
    monkeypatch.setattr(check, 'perform_kubelet_query', lambda url, stream=False: response)

    with mock.patch('datadog_checks.base.checks.kubelet_base.base.get_config', return_value=expiration_duration):
        retrieved = check.retrieve_pod_list()

    assert retrieved['items'] == pod_list['items']


def test_retrieved_pod_list_failure(caplog, monkeypatch):
    def mock_perform_kubelet_query(s, stream=False):
        raise Exception("network error")

    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = 'https://kubelet:10250/pods'
    monkeypatch.setattr(check, 'perform_kubelet_query', mock_perform_kubelet_query)

    retrieved = check.retrieve_pod_list()
    assert retrieved == {}
    assert 'failed to retrieve pod list from the kubelet at https://kubelet:10250/pods : network error' in caplog.text


def test_compute_pod_expiration_datetime(monkeypatch):
    # Invalid input
    with mock.patch("datadog_checks.base.checks.kubelet_base.base.get_config", return_value="") as p:
        assert KubeletBase.compute_pod_expiration_datetime() is None
        p.assert_called_with("kubernetes_pod_expiration_duration")

    with mock.patch("datadog_checks.base.checks.kubelet_base.base.get_config", return_value="invalid"):
        assert KubeletBase.compute_pod_expiration_datetime() is None

    # Disabled
    with mock.patch("datadog_checks.base.checks.kubelet_base.base.get_config", return_value="0"):
        assert KubeletBase.compute_pod_expiration_datetime() is None

    # Set to 15 minutes
    with mock.patch("datadog_checks.base.checks.kubelet_base.base.get_config", return_value="900"):
        expire = KubeletBase.compute_pod_expiration_datetime()
        assert expire is not None
        now = datetime.now(timezone.utc)
        assert abs((now - expire).seconds - 60 * 15) < 2


def test_urljoin():
    base = 'https://www.example.com'
    base_with_slash = base + '/'
    one_level = 'https://www.example.com/test'
    two_levels = one_level + '/another'

    result = urljoin(base, 'test')
    assert result == one_level
    result = urljoin(base, '/test')
    assert result == one_level
    result = urljoin(base, '/test/')
    assert result == one_level

    result = urljoin(base_with_slash, 'test')
    assert result == one_level
    result = urljoin(base_with_slash, '/test')
    assert result == one_level
    result = urljoin(base_with_slash, '/test/')
    assert result == one_level

    result = urljoin(base, 'test', 'another')
    assert result == two_levels
    result = urljoin(base, 'test/', 'another/')
    assert result == two_levels
    result = urljoin(base, '/test/', '/another/')
    assert result == two_levels
