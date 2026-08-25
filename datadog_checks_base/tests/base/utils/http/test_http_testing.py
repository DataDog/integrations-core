# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.http import FakeHTTPResponse, RecordedRequest
from datadog_checks.dev import http as http_testing
from datadog_checks.dev.http import MockHTTPResponse


def test_mock_http_patches_agentcheck(mock_http):
    check = AgentCheck('test', {}, [{}])
    assert check.http is mock_http


def test_mock_http_patches_explicit_agentcheck_client(mock_http):
    check = AgentCheck('test', {}, [{}])
    assert check.create_http_client({'url': 'https://example.test'}) is mock_http


def test_fake_http_installs_registered_response_and_records_request(fake_http):
    url = 'https://example.test/items'
    response = FakeHTTPResponse(json_result={'items': []})
    fake_http.register_response('GET', url, response)
    check = AgentCheck('test', {}, [{}])

    assert check.http.get(url, stream=True) is response
    fake_http.assert_requests([RecordedRequest(method='GET', url=url, options={'stream': True})])
    fake_http.assert_all_responses_consumed()


def test_mock_http_supports_options(mock_http):
    response = FakeHTTPResponse()
    mock_http.options_method.return_value = response
    check = AgentCheck('test', {}, [{}])

    assert check.http.options_method('https://example.test') is response


@pytest.mark.parametrize('default', [None, 'fallback'])
def test_mock_http_absent_cookie_returns_default(mock_http, default):
    assert mock_http.get_cookie('missing', default) == default


def test_mock_http_get_cookie_accepts_keyword_arguments(mock_http):
    assert mock_http.get_cookie(name='missing', default='fallback') == 'fallback'


def test_mock_http_get_cookie_return_value_is_configurable(mock_http):
    mock_http.get_cookie.return_value = 'token'
    assert mock_http.get_cookie('csrftoken') == 'token'


def test_mock_http_exposes_tls_config(mock_http):
    assert mock_http.tls_config == {}


def test_legacy_mock_response_is_a_requests_response():
    with pytest.warns(DeprecationWarning, match='FakeHTTPResponse'):
        legacy = http_testing.MockResponse

    assert issubclass(legacy, requests.Response)


def test_legacy_mock_response_raises_on_the_requests_exception_tree():
    with pytest.warns(DeprecationWarning):
        legacy = http_testing.MockResponse

    with pytest.raises(requests.HTTPError):
        legacy(json_data={'message': 'Session expired.'}, status_code=401).raise_for_status()


def test_legacy_mock_response_reads_json_and_headers():
    with pytest.warns(DeprecationWarning):
        legacy = http_testing.MockResponse

    response = legacy(json_data={'key': 'value'}, headers={'X-Custom': 'value'}, status_code=200)

    assert response.json() == {'key': 'value'}
    assert response.headers['x-custom'] == 'value'
    assert response.status_code == 200


def test_legacy_mock_response_reads_a_file(tmp_path):
    path = tmp_path / 'payload.json'
    path.write_text('{"key": "value"}')

    with pytest.warns(DeprecationWarning):
        legacy = http_testing.MockResponse

    assert legacy(file_path=str(path)).json() == {'key': 'value'}


def test_mock_http_response_compatibility_builder_returns_base_fake(tmp_path):
    path = tmp_path / 'payload.txt'
    path.write_text('line one\nline two')

    response = MockHTTPResponse(file_path=str(path), headers={'X-Test': 'value'})

    assert isinstance(response, FakeHTTPResponse)
    assert response.content == b'line one\nline two'
    assert list(response.iter_lines()) == ['line one', 'line two']
    assert response.headers['x-test'] == 'value'


def test_mock_http_response_per_endpoint_accepts_base_fakes(mock_http_response_per_endpoint):
    url = 'https://example.test/items'
    response = FakeHTTPResponse()
    mock_http_response_per_endpoint({url: [response]}, mode='exhaust')

    assert requests.Session().get(url) is response


def test_unknown_module_attribute_still_raises():
    absent = 'MockNonsense'
    with pytest.raises(AttributeError, match=absent):
        getattr(http_testing, absent)
