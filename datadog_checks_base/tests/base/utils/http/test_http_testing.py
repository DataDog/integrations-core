# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.openmetrics.mixins import OpenMetricsScraperMixin
from datadog_checks.base.checks.prometheus.mixins import PrometheusScraperMixin
from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse, RecordedRequest
from datadog_checks.dev import http as http_testing


class OpenMetricsFixtureCheck(OpenMetricsScraperMixin, AgentCheck):
    pass


class PrometheusFixtureCheck(PrometheusScraperMixin, AgentCheck):
    pass


def test_fake_http_patches_explicit_agentcheck_client(fake_http):
    check = AgentCheck('test', {}, [{}])
    assert check.create_http_client({'url': 'https://example.test'}) is fake_http


def test_http_module_reexports_base_fakes():
    assert http_testing.FakeHTTPClient is FakeHTTPClient
    assert http_testing.FakeHTTPResponse is FakeHTTPResponse
    assert http_testing.MockHTTPResponse is FakeHTTPResponse
    assert http_testing.RecordedRequest is RecordedRequest


def test_fake_http_installs_registered_response_and_records_request(fake_http):
    url = 'https://example.test/items'
    response = FakeHTTPResponse(json_result={'items': []})
    fake_http.register_response('GET', url, response)
    check = AgentCheck('test', {}, [{}])

    assert check.http.get(url, stream=True) is response
    fake_http.assert_requests([RecordedRequest(method='GET', url=url, options={'stream': True})])
    fake_http.assert_all_responses_consumed()


def test_fake_openmetrics_http_routes_send_request(fake_openmetrics_http):
    url = 'https://example.test/metrics'
    response = FakeHTTPResponse(text='metric 1')
    headers = {'Authorization': 'Bearer token'}
    fake_openmetrics_http.register_response('GET', url, response)
    check = OpenMetricsFixtureCheck('test', {}, [{}])

    result = check.send_request(url, {'prometheus_url': url}, headers=headers)

    assert result is response
    fake_openmetrics_http.assert_requests(
        [RecordedRequest(method='GET', url=url, options={'headers': headers, 'stream': True})]
    )
    fake_openmetrics_http.assert_all_responses_consumed()


def test_fake_prometheus_http_routes_poll(fake_prometheus_http):
    url = 'https://example.test/metrics'
    response = FakeHTTPResponse(text='metric 1')
    fake_prometheus_http.register_response('GET', url, response)
    check = PrometheusFixtureCheck('test', {}, [{}])

    result = check.poll(url, headers={'X-Test': 'value'})

    assert result is response
    fake_prometheus_http.assert_requests(
        [
            RecordedRequest(
                method='GET',
                url=url,
                options={
                    'extra_headers': {
                        'X-Test': 'value',
                        'Accept-Encoding': 'gzip',
                        'accept': (
                            'application/vnd.google.protobuf; '
                            'proto=io.prometheus.client.MetricFamily; encoding=delimited'
                        ),
                    },
                    'stream': False,
                },
            )
        ]
    )
    fake_prometheus_http.assert_all_responses_consumed()


def test_legacy_mock_response_is_a_requests_response_without_loading_base_fakes(mocker):
    real_import_module = http_testing.importlib.import_module

    def import_legacy(name):
        if name == 'datadog_checks.base.stubs.http':
            raise AssertionError('legacy compatibility must not load the base HTTP fakes')
        return real_import_module(name)

    mocker.patch.object(http_testing.importlib, 'import_module', side_effect=import_legacy)
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


def test_mock_response_fixture_builds_requests_response(tmp_path, mock_response):
    path = tmp_path / 'payload.txt'
    path.write_bytes(b'line one\nline two')

    response = mock_response(file_path=str(path), headers={'X-Test': 'value'})

    assert isinstance(response, requests.Response)
    assert response.content == b'line one\nline two'
    assert list(response.iter_lines()) == [b'line one', b'line two']
    assert response.headers['x-test'] == 'value'


def test_mock_response_fixture_preserves_requests_status_errors(mock_response):
    response = mock_response(json_data={'error': 'unavailable'}, status_code=503)

    assert response.json() == {'error': 'unavailable'}
    with pytest.raises(requests.HTTPError, match='503 Server Error') as exc_info:
        response.raise_for_status()
    assert exc_info.value.response is response


def test_mock_http_response_preserves_requests_responses(mock_http_response):
    url = 'https://example.test/items'
    mock_http_response(content='payload')

    response = requests.Session().get(url)

    assert isinstance(response, requests.Response)
    assert response.text == 'payload'


def test_mock_http_response_per_endpoint_preserves_requests_responses(mock_http_response_per_endpoint, mock_response):
    url = 'https://example.test/items'
    response = mock_response()
    mock_http_response_per_endpoint({url: [response]}, mode='exhaust')

    assert isinstance(response, requests.Response)
    assert requests.Session().get(url) is response


def test_unknown_module_attribute_still_raises():
    absent = 'MockNonsense'
    with pytest.raises(AttributeError, match=absent):
        getattr(http_testing, absent)
