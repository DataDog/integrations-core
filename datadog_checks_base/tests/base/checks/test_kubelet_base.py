# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from datetime import datetime, timezone

import mock
import pytest

from datadog_checks.base.checks.kubelet_base.base import KubeletBase, KubeletCredentials, urljoin
from datadog_checks.dev import get_here
from datadog_checks.dev.http import MockHTTPResponse

HERE = get_here()


def get_fixture_path(filename):
    return os.path.join(HERE, '..', '..', 'fixtures', filename)


def mock_from_file(filename):
    with open(get_fixture_path(filename)) as f:
        return f.read()


def test_retrieve_pod_list_success(mock_http):
    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = "dummyurl"
    check.kubelet_credentials = KubeletCredentials({})
    mock_http.get.return_value = MockHTTPResponse(file_path=get_fixture_path('kubelet_base/pod_list_raw.dat'))

    retrieved = check.retrieve_pod_list()
    expected = json.loads(mock_from_file("kubelet_base/pod_list_raw.json"))
    assert json.dumps(retrieved, sort_keys=True) == json.dumps(expected, sort_keys=True)


def test_retrieve_pod_list_parses_via_json(mock_http):
    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = 'http://kubelet:10255/pods'
    check.kubelet_credentials = KubeletCredentials({})
    mock_http.get.return_value = MockHTTPResponse(json_data={'items': [{'name': 'p1'}]})

    pod_list = check.retrieve_pod_list()
    assert pod_list['items'] == [{'name': 'p1'}]


@pytest.mark.parametrize('verbose', [True, False], ids=['verbose', 'terse'])
def test_perform_kubelet_query_forwards_credentials_and_verbosity(mock_http, verbose):
    # Shared by KubeletCheck and EksFargateCheck. Losing the credentials sends unauthenticated
    # requests to an https kubelet, which 401s; losing the parameter silences every per-component
    # kubelet service check and leaves only the aggregate.
    check = KubeletBase('kubelet', {}, [{}])
    check.kubelet_credentials = KubeletCredentials(
        {'token': 'tkn', 'ca_cert': '/ca.pem', 'client_crt': '/crt.pem', 'client_key': '/key.pem'}
    )
    mock_http.get.return_value = MockHTTPResponse(status_code=200)

    check.perform_kubelet_query('https://kubelet:10250/healthz', verbose=verbose)

    kwargs = mock_http.get.call_args.kwargs
    assert kwargs['params'] == {'verbose': verbose}
    assert kwargs['verify'] == '/ca.pem'
    assert kwargs['cert'] == ('/crt.pem', '/key.pem')
    # A client certificate suppresses the token, so no Authorization header is offered alongside it.
    assert kwargs['headers'] is None


def test_perform_kubelet_query_forwards_the_bearer_token(mock_http):
    check = KubeletBase('kubelet', {}, [{}])
    check.kubelet_credentials = KubeletCredentials({'token': 'tkn'})
    mock_http.get.return_value = MockHTTPResponse(status_code=200)

    check.perform_kubelet_query('https://kubelet:10250/healthz')

    assert mock_http.get.call_args.kwargs['headers'] == {'Authorization': 'Bearer tkn'}


@pytest.mark.parametrize('expiration_duration', ['0', '900'], ids=['no_expiration_filter', 'expiration_filter'])
def test_retrieve_pod_list_decodes_a_utf8_body_under_a_non_utf8_encoding(mock_http, expiration_duration):
    # A kubelet, or a proxy in front of one, can answer /pods with a text/* content type carrying no
    # charset, which settles the response encoding on ISO-8859-1 and mangles every non-ASCII label.
    # The pod list therefore has to come from the response bytes and not from its decoded text.
    labels = {'owner': 'café-münchen'}
    body = json.dumps({'items': [{'metadata': {'labels': labels}}]}, ensure_ascii=False).encode('utf-8')
    assert max(body) > 127, 'the body must carry multibyte UTF-8 for this test to mean anything'

    response = MockHTTPResponse(content=body, headers={'Content-Type': 'text/plain'})
    response.encoding = 'ISO-8859-1'
    # Without a divergence between the bytes and the decoded text this test would prove nothing.
    assert 'café-münchen' not in response.text
    mock_http.get.return_value = response

    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = 'http://kubelet:10255/pods'
    check.kubelet_credentials = KubeletCredentials({})

    with mock.patch('datadog_checks.base.checks.kubelet_base.base.get_config', return_value=expiration_duration):
        pod_list = check.retrieve_pod_list()

    assert pod_list['items'][0]['metadata']['labels'] == labels


def test_retrieved_pod_list_failure(monkeypatch):
    def mock_perform_kubelet_query(s, stream=False):
        raise Exception("network error")

    check = KubeletBase('kubelet', {}, [{}])
    check.pod_list_url = "dummyurl"
    monkeypatch.setattr(check, 'perform_kubelet_query', mock_perform_kubelet_query)

    retrieved = check.retrieve_pod_list()
    assert retrieved == {}


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
