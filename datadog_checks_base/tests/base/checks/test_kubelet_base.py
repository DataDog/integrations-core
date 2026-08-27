# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from datetime import datetime, timezone

import mock
import pytest

from datadog_checks.base.checks.kubelet_base.base import KubeletBase, KubeletCredentials, urljoin
from datadog_checks.base.stubs.http import FakeHTTPResponse, RecordedRequest
from datadog_checks.dev import get_here

HERE = get_here()


def get_fixture_path(filename):
    return os.path.join(HERE, '..', '..', 'fixtures', filename)


def mock_from_file(filename):
    with open(get_fixture_path(filename)) as f:
        return f.read()


def test_retrieve_pod_list_success(fake_http):
    url = 'https://kubelet:10250/pods'
    response = FakeHTTPResponse(content=mock_from_file('kubelet_base/pod_list_raw.dat').encode('utf-8'))
    fake_http.register_response('GET', url, response)
    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = url
    check.kubelet_credentials = KubeletCredentials({})

    retrieved = check.retrieve_pod_list()
    expected = json.loads(mock_from_file("kubelet_base/pod_list_raw.json"))
    assert json.dumps(retrieved, sort_keys=True) == json.dumps(expected, sort_keys=True)
    fake_http.assert_requests(
        [
            RecordedRequest(
                method='GET',
                url=url,
                options={'verify': None, 'cert': None, 'headers': None, 'params': {'verbose': True}, 'stream': True},
            )
        ]
    )
    fake_http.assert_all_responses_consumed()


def test_retrieve_pod_list_parses_via_json(fake_http):
    url = 'http://kubelet:10255/pods'
    fake_http.register_response('GET', url, FakeHTTPResponse(content=b'{"items": [{"name": "p1"}]}'))
    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = url
    check.kubelet_credentials = KubeletCredentials({})

    pod_list = check.retrieve_pod_list()
    assert pod_list['items'] == [{'name': 'p1'}]
    fake_http.assert_requests(
        [
            RecordedRequest(
                method='GET',
                url=url,
                options={'verify': None, 'cert': None, 'headers': None, 'params': {'verbose': True}, 'stream': True},
            )
        ]
    )
    fake_http.assert_all_responses_consumed()


@pytest.mark.parametrize('verbose', [True, False], ids=['verbose', 'terse'])
def test_perform_kubelet_query_forwards_credentials_and_verbosity(fake_http, verbose):
    url = 'https://kubelet:10250/healthz'
    response = FakeHTTPResponse(status_code=200)
    fake_http.register_response('GET', url, response)
    check = KubeletBase('kubelet', {}, [{}])
    check.kubelet_credentials = KubeletCredentials(
        {'token': 'tkn', 'ca_cert': '/ca.pem', 'client_crt': '/crt.pem', 'client_key': '/key.pem'}
    )

    assert check.perform_kubelet_query(url, verbose=verbose) is response

    fake_http.assert_requests(
        [
            RecordedRequest(
                method='GET',
                url=url,
                options={
                    'verify': '/ca.pem',
                    'cert': ('/crt.pem', '/key.pem'),
                    'headers': None,
                    'params': {'verbose': verbose},
                    'stream': False,
                },
            )
        ]
    )
    fake_http.assert_all_responses_consumed()


def test_perform_kubelet_query_forwards_the_bearer_token(fake_http):
    url = 'https://kubelet:10250/healthz'
    fake_http.register_response('GET', url, FakeHTTPResponse(status_code=200))
    check = KubeletBase('kubelet', {}, [{}])
    check.kubelet_credentials = KubeletCredentials({'token': 'tkn'})

    check.perform_kubelet_query(url)

    fake_http.assert_requests(
        [
            RecordedRequest(
                method='GET',
                url=url,
                options={
                    'verify': None,
                    'cert': None,
                    'headers': {'Authorization': 'Bearer tkn'},
                    'params': {'verbose': True},
                    'stream': False,
                },
            )
        ]
    )
    fake_http.assert_all_responses_consumed()


@pytest.mark.parametrize('expiration_duration', ['0', '900'], ids=['no_expiration_filter', 'expiration_filter'])
def test_retrieve_pod_list_decodes_a_utf8_body_under_a_non_utf8_encoding(fake_http, expiration_duration):
    url = 'http://kubelet:10255/pods'
    labels = {'owner': 'café-münchen'}
    body = json.dumps({'items': [{'metadata': {'labels': labels}}]}, ensure_ascii=False).encode('utf-8')
    assert max(body) > 127, 'the body must carry multibyte UTF-8 for this test to mean anything'

    response = FakeHTTPResponse(
        content=body,
        text=body.decode('ISO-8859-1'),
        headers={'Content-Type': 'text/plain'},
        encoding='ISO-8859-1',
    )
    assert 'café-münchen' not in response.text
    fake_http.register_response('GET', url, response)

    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = url
    check.kubelet_credentials = KubeletCredentials({})

    with mock.patch('datadog_checks.base.checks.kubelet_base.base.get_config', return_value=expiration_duration):
        pod_list = check.retrieve_pod_list()

    assert pod_list['items'][0]['metadata']['labels'] == labels
    fake_http.assert_requests(
        [
            RecordedRequest(
                method='GET',
                url=url,
                options={'verify': None, 'cert': None, 'headers': None, 'params': {'verbose': True}, 'stream': True},
            )
        ]
    )
    fake_http.assert_all_responses_consumed()


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
