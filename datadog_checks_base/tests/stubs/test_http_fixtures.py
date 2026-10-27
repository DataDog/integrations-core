# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import importlib
import sys
from typing import Any

import pytest
import requests

import datadog_checks.dev
from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.openmetrics.base_check import OpenMetricsBaseCheck
from datadog_checks.base.checks.prometheus.prometheus_base import PrometheusCheck
from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse, RecordedRequest
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev import http as http_testing


class FixtureCheck(AgentCheck):
    AGNOSTIC_HTTP_CLIENT = True


class OpenMetricsFixtureCheck(OpenMetricsBaseCheck):
    AGNOSTIC_HTTP_CLIENT = True


class PrometheusFixtureCheck(PrometheusCheck):
    AGNOSTIC_HTTP_CLIENT = True


def test_fake_http_requires_the_check_to_opt_in(fake_http):
    check = AgentCheck('test', {}, [{}])

    with pytest.raises(AssertionError, match='AGNOSTIC_HTTP_CLIENT = True'):
        check.create_http_client()


def test_fake_http_does_not_construct_backend_clients(fake_http, mocker):
    backend_client = mocker.patch('datadog_checks.base.utils.http.RequestsWrapper')
    check = FixtureCheck('test', {}, [{}])

    assert isinstance(check.http, FakeHTTPClient)
    assert isinstance(check.create_http_client(), FakeHTTPClient)

    backend_client.assert_not_called()


@pytest.mark.parametrize(
    ('instance', 'init_config', 'remapper'),
    [
        pytest.param({}, {}, None, id='defaults'),
        pytest.param({'tls_verify': False}, {}, None, id='disable-verification'),
        pytest.param({'tls_verify': 'false'}, {}, None, id='string-boolean'),
        pytest.param({'tls_ciphers': 'ECDHE+AESGCM'}, {}, None, id='custom-ciphers'),
        pytest.param({'tls_ca_cert': '/test/ca.pem'}, {}, None, id='ca-bundle'),
        pytest.param({'tls_cert': '/test/cert.pem', 'tls_private_key': '/test/key.pem'}, {}, None, id='client-cert'),
        pytest.param({}, {'tls_ignore_warning': True}, None, id='init-default'),
        pytest.param({'tls_ignore_warning': False}, {'tls_ignore_warning': True}, None, id='instance-precedence'),
        pytest.param(
            {'disable_ssl_validation': True},
            {},
            {'disable_ssl_validation': {'name': 'tls_verify', 'invert': True}},
            id='legacy-alias',
        ),
        pytest.param({}, {}, {'verify': {'name': 'tls_verify', 'default': False}}, id='remapped-default'),
        pytest.param(
            {'tls_verify': True, 'disable_ssl_validation': True},
            {},
            {'disable_ssl_validation': {'name': 'tls_verify', 'invert': True}},
            id='standard-field-precedence',
        ),
    ],
)
def test_fake_http_resolves_check_tls_config(fake_http, instance: dict, init_config: dict, remapper: dict | None):
    check = FixtureCheck('test', init_config, [instance])
    check.HTTP_CONFIG_REMAPPER = remapper
    real_client = RequestsWrapper(check.instance, check.init_config, remapper)

    for client in (check.http, check.create_http_client()):
        assert client.tls_config == real_client.tls_config
        assert client.options['verify'] == real_client.options['verify']
        assert client.options['cert'] == real_client.options['cert']
        assert client.ignore_tls_warning == real_client.ignore_tls_warning


def test_fake_http_respects_explicit_factory_config(fake_http):
    check = FixtureCheck('test', {'tls_ignore_warning': True}, [{'tls_ciphers': 'ECDHE+AESGCM'}])
    check.HTTP_CONFIG_REMAPPER = {'verify': {'name': 'tls_verify', 'default': False}}

    client = check.create_http_client({'tls_validate_hostname': False}, init_config={}, remapper={})
    real_client = RequestsWrapper({'tls_validate_hostname': False}, {}, {})

    assert client.tls_config == real_client.tls_config
    assert check.http.tls_config['tls_verify'] is False
    assert check.http.tls_config['tls_ciphers'] == 'ECDHE+AESGCM'
    assert check.http.ignore_tls_warning is True


def test_fake_http_tls_config_is_isolated_per_check_and_client(fake_http):
    first = FixtureCheck('test', {}, [{'tls_verify': False, 'tls_protocols_allowed': ['TLSv1.2']}])
    second = FixtureCheck('test', {}, [{}])
    sibling = first.create_http_client()

    first.http.tls_config['tls_protocols_allowed'].append('TLSv1.3')
    first.http.tls_config['tls_verify'] = True

    assert sibling.tls_config['tls_verify'] is False
    assert sibling.tls_config['tls_protocols_allowed'] == ['TLSv1.2']
    assert first.instance['tls_protocols_allowed'] == ['TLSv1.2']
    assert second.http.tls_config['tls_verify'] is True
    assert fake_http.tls_config['tls_verify'] is True


def test_fake_http_creates_isolated_clients(fake_http):
    check = FixtureCheck('test', {}, [{}])

    default_client = check.http
    explicit_client = check.create_http_client()

    assert check.http is default_client
    assert default_client is not explicit_client
    assert default_client is not fake_http
    assert explicit_client is not fake_http

    default_client.set_header('X-Default-Only', 'value')
    assert explicit_client.get_header('X-Default-Only') is None

    default_client.close()
    assert default_client.closed
    assert not explicit_client.closed


def test_fake_http_aggregates_interactions_from_isolated_clients(fake_http):
    first_url = 'https://example.test/first'
    second_url = 'https://example.test/second'
    first_response = FakeHTTPResponse()
    second_response = FakeHTTPResponse()
    fake_http.register_response('GET', first_url, first_response)
    fake_http.register_response('GET', second_url, second_response)
    check = FixtureCheck('test', {}, [{}])

    default_client = check.http
    explicit_client = check.create_http_client()

    assert default_client is not explicit_client
    assert default_client.get(first_url) is first_response
    assert explicit_client.get(second_url) is second_response
    fake_http.assert_requests([RecordedRequest('GET', first_url), RecordedRequest('GET', second_url)])
    fake_http.assert_all_responses_consumed()


def test_fake_http_installs_registered_response_and_records_request(fake_http):
    url = 'https://example.test/items'
    response = FakeHTTPResponse(json_result={'items': []})
    fake_http.register_response('GET', url, response)
    check = FixtureCheck('test', {}, [{}])

    assert check.http.get(url, stream=True) is response
    fake_http.assert_requests([RecordedRequest(method='GET', url=url, options={'stream': True})])
    fake_http.assert_all_responses_consumed()


def test_fake_http_response_builds_and_registers_text_response(fake_http_response: Any):
    url = 'https://example.test/metrics'
    response = fake_http_response(url, 'first\nsecond', match_options={'stream': True})
    check = FixtureCheck('test', {}, [{}])

    assert check.http.get(url, stream=True) is response
    assert response.content == b'first\nsecond'
    assert response.text == 'first\nsecond'
    assert list(response.iter_content()) == [b'first\nsecond']
    assert list(response.iter_lines(decode_unicode=True)) == ['first', 'second']


@pytest.mark.parametrize(
    ('payload', 'expected_content'),
    [
        ({'items': []}, b'{"items": []}'),
        (None, b'null'),
    ],
)
def test_fake_http_response_builds_and_registers_json_response(
    payload: Any, expected_content: bytes, fake_http: FakeHTTPClient, fake_http_response: Any
):
    url = 'https://example.test/items'
    response = fake_http_response(
        url,
        method='POST',
        json_data=payload,
        status_code=201,
        match_options={'json': payload},
        reason='Created',
    )
    check = FixtureCheck('test', {}, [{}])

    assert check.http.post(url, json=payload) is response
    assert response.content == expected_content
    assert response.json() is payload
    assert response.status_code == 201
    assert response.reason == 'Created'
    fake_http.assert_all_responses_consumed()


def test_fake_http_routes_openmetrics_send_request(fake_http):
    url = 'https://example.test/metrics'
    response = FakeHTTPResponse(text='metric 1')
    headers = {'Authorization': 'Bearer token'}
    fake_http.register_response('GET', url, response)
    check = OpenMetricsFixtureCheck('test', {}, {}, [])
    scraper_config = check.create_scraper_configuration({'prometheus_url': url, 'namespace': 'test'})

    result = check.send_request(url, scraper_config, headers=headers)

    assert result is response
    fake_http.assert_requests([RecordedRequest(method='GET', url=url, options={'headers': headers, 'stream': True})])
    fake_http.assert_all_responses_consumed()


def test_fake_http_preserves_openmetrics_handler_cache_and_isolation(fake_http):
    first_config = {'prometheus_url': 'https://example.test/first', 'namespace': 'test'}
    second_config = {'prometheus_url': 'https://example.test/second', 'namespace': 'test'}
    check = OpenMetricsFixtureCheck('test', {}, {}, [])
    first_config = check.create_scraper_configuration(first_config)
    second_config = check.create_scraper_configuration(second_config)

    first_handler = check.get_http_handler(first_config)
    second_handler = check.get_http_handler(second_config)

    assert check.get_http_handler(first_config) is first_handler
    assert first_handler is not second_handler
    first_handler.set_header('X-First-Only', 'value')
    assert second_handler.get_header('X-First-Only') is None


def test_fake_http_routes_prometheus_poll(fake_http):
    url = 'https://example.test/metrics'
    response = FakeHTTPResponse(text='metric 1')
    fake_http.register_response('GET', url, response)
    check = PrometheusFixtureCheck('test', {}, {}, [])

    result = check.poll(url, headers={'X-Test': 'value'})

    assert result is response
    fake_http.assert_requests(
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
    fake_http.assert_all_responses_consumed()


def test_fake_http_preserves_prometheus_handler_cache_and_isolation(fake_http):
    first_url = 'https://example.test/first'
    second_url = 'https://example.test/second'
    check = PrometheusFixtureCheck('test', {}, {}, [])

    first_handler = check.get_http_handler(first_url, {})
    second_handler = check.get_http_handler(second_url, {})

    assert check.get_http_handler(first_url, {}) is first_handler
    assert first_handler is not second_handler
    first_handler.set_header('X-First-Only', 'value')
    assert second_handler.get_header('X-First-Only') is None


def test_legacy_mock_response_is_a_requests_response_without_loading_base_fakes(monkeypatch):
    # Suites testing against an older base, which lacks the fakes, still import MockResponse.
    for name in ('datadog_checks.dev.http', 'datadog_checks.dev.http_legacy', 'datadog_checks.base.stubs.http'):
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setattr(datadog_checks.dev, 'http', http_testing)

    fresh_http_testing = importlib.import_module('datadog_checks.dev.http')
    with pytest.warns(DeprecationWarning, match='FakeHTTPResponse'):
        legacy = fresh_http_testing.MockResponse

    assert issubclass(legacy, requests.Response)
    assert 'datadog_checks.base.stubs.http' not in sys.modules


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
