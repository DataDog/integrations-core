# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import importlib
import sys
import threading
from datetime import timedelta
from typing import Any

import pytest
import requests

import datadog_checks.dev
from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.openmetrics.base_check import OpenMetricsBaseCheck
from datadog_checks.base.checks.prometheus.prometheus_base import PrometheusCheck
from datadog_checks.base.stubs.http import FakeHTTPResponse, RecordedRequest
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError
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


@pytest.mark.parametrize(
    ('disable_auth', 'expected_auth'),
    [
        pytest.param(False, 'Basic dTpw', id='instance-auth'),
        pytest.param(True, None, id='auth-disabled'),
    ],
)
def test_fake_http_sends_the_check_instance_config(fake_http, fake_http_response, disable_auth, expected_auth):
    url = 'https://example.test/items'
    fake_http_response(url)
    check = FixtureCheck('test', {}, [{'username': 'u', 'password': 'p', 'headers': {'X-Team': 'agint'}}])
    if disable_auth:
        check.http.disable_auth()

    check.http.get(url)

    [sent] = fake_http.sent
    assert (sent.method, sent.url) == ('GET', url)
    assert sent.headers['x-team'] == 'agint'
    assert sent.headers.get('Authorization') == expected_auth


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


def test_fake_http_aggregates_interactions_from_isolated_clients(fake_http):
    first_url = 'https://example.test/first'
    second_url = 'https://example.test/second'
    fake_http.register_response('GET', first_url, FakeHTTPResponse(content=b'first'))
    fake_http.register_response('GET', second_url, FakeHTTPResponse(content=b'second'))
    check = FixtureCheck('test', {}, [{}])

    default_client = check.http
    explicit_client = check.create_http_client()

    assert default_client is not explicit_client
    assert default_client.get(first_url).content == b'first'
    assert explicit_client.get(second_url).content == b'second'
    fake_http.assert_requests([RecordedRequest('GET', first_url), RecordedRequest('GET', second_url)])
    fake_http.assert_all_responses_consumed()


def test_fake_http_installs_registered_response_and_records_request(fake_http):
    url = 'https://example.test/items'
    fake_http.register_response('GET', url, FakeHTTPResponse(json_result={'items': []}))
    check = FixtureCheck('test', {}, [{}])

    assert check.http.get(url, stream=True).json() == {'items': []}
    fake_http.assert_requests([RecordedRequest(method='GET', url=url, options={'stream': True})])
    fake_http.assert_all_responses_consumed()


def test_fake_http_response_builds_and_registers_text_response(fake_http_response: Any):
    url = 'https://example.test/metrics'
    fake_http_response(url, 'first\nsecond', match_options={'stream': True})
    check = FixtureCheck('test', {}, [{}])

    response = check.http.get(url, stream=True)
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
    payload: Any, expected_content: bytes, fake_http: Any, fake_http_response: Any
):
    url = 'https://example.test/items'
    fake_http_response(
        url,
        method='POST',
        json_data=payload,
        status_code=201,
        match_options={'json': payload},
        reason='Created',
    )
    check = FixtureCheck('test', {}, [{}])

    response = check.http.post(url, json=payload)
    assert response.content == expected_content
    assert response.json() == payload
    assert response.status_code == 201
    assert response.reason == 'Created'
    fake_http.assert_all_responses_consumed()


def test_fake_http_routes_openmetrics_send_request(fake_http):
    url = 'https://example.test/metrics'
    headers = {'Authorization': 'Bearer token'}
    fake_http.register_response('GET', url, FakeHTTPResponse(text='metric 1'))
    check = OpenMetricsFixtureCheck('test', {}, {}, [])
    scraper_config = check.create_scraper_configuration({'prometheus_url': url, 'namespace': 'test'})

    result = check.send_request(url, scraper_config, headers=headers)

    assert result.text == 'metric 1'
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
    fake_http.register_response('GET', url, FakeHTTPResponse(text='metric 1'))
    check = PrometheusFixtureCheck('test', {}, {}, [])

    result = check.poll(url, headers={'X-Test': 'value'})

    assert result.text == 'metric 1'
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


class BlockingBody(str):
    """A request body that pauses its thread while the fixture compares it against a registration."""

    def __new__(cls, value: str) -> 'BlockingBody':
        body = super().__new__(cls, value)
        body.comparing = threading.Event()
        body.release = threading.Event()
        return body

    def __eq__(self, other: object) -> bool:
        self.comparing.set()
        self.release.wait(5)
        return str.__eq__(self, other)

    __hash__ = str.__hash__


@pytest.mark.parametrize('second_client', ['same', 'created'])
def test_fake_http_serves_each_concurrent_request_its_own_registration(fake_http, fake_http_response, second_client):
    fake_http_response('https://example.test/a', b'A')
    fake_http_response('https://example.test/b', b'B', method='POST', match_options={'data': 'b-body'})
    fake_http_response('https://example.test/c', b'C')
    check = FixtureCheck('test', {}, [{}])
    first = check.http
    second = first if second_client == 'same' else check.create_http_client()
    body = BlockingBody('b-body')
    results = {}

    def call(name, send):
        try:
            results[name] = send().content
        except Exception as e:
            results[name] = e

    matching = threading.Thread(target=call, args=('b', lambda: first.post('https://example.test/b', data=body)))
    matching.start()
    assert body.comparing.wait(5)
    # While the first request is between matching its registration and consuming it, another request must not
    # consume a registration out from under it. Give that request a bounded window to run, then let matching finish.
    other = threading.Thread(target=call, args=('a', lambda: second.get('https://example.test/a')))
    other.start()
    other.join(0.3)
    body.release.set()
    matching.join(5)
    other.join(5)

    assert results == {'a': b'A', 'b': b'B'}


def test_fake_http_serves_matching_registrations_in_order_then_repeats_the_last(fake_http, fake_http_response):
    url = 'https://example.test/items'
    fake_http_response(url, b'first')
    fake_http_response(url, b'second')
    check = FixtureCheck('test', {}, [{}])

    assert check.http.get(url).content == b'first'
    with pytest.raises(AssertionError, match='1 registered response was not consumed'):
        fake_http.assert_all_responses_consumed()

    assert [check.http.get(url).content for _ in range(2)] == [b'second', b'second']
    fake_http.assert_all_responses_consumed()


def test_fake_http_rejects_requests_that_bypass_the_check_client(fake_http, fake_http_response):
    url = 'https://example.test/items'
    fake_http_response(url)

    with pytest.raises(AssertionError, match='bypassed the check HTTP client'):
        requests.get(url)


def test_fake_http_rejects_a_followed_redirect(fake_http, fake_http_response):
    fake_http_response('https://example.test/old', status_code=302, headers={'Location': 'https://example.test/new'})
    fake_http_response('https://example.test/new', b'moved')
    check = FixtureCheck('test', {}, [{}])

    with pytest.raises(AssertionError, match='GET https://example.test/old sent GET https://example.test/new'):
        check.http.get('https://example.test/old')


def test_fake_http_rejects_a_token_request_sent_during_a_check_call(fake_http, fake_http_response, mocker):
    url = 'https://example.test/metrics'
    fake_http_response(url, b'metric 1')
    check = FixtureCheck('test', {}, [{}])
    # Stands in for an auth token reader, such as dcos_auth, that fetches its token with requests mid-call.
    check.http.auth_token_handler = mocker.Mock(poll=lambda **_: requests.post('https://login.test/token'))

    with pytest.raises(AssertionError, match=f'GET {url} sent POST https://login.test/token'):
        check.http.get(url)


def test_fake_http_serves_a_retry_of_the_same_call(fake_http, fake_http_response, mocker):
    # The client retries the same call after renewing an auth token that the first response rejected.
    url = 'https://example.test/metrics'
    fake_http_response(url, status_code=401)
    fake_http_response(url, b'metric 1')
    check = FixtureCheck('test', {}, [{}])
    check.http.auth_token_handler = mocker.Mock()

    assert check.http.get(url).content == b'metric 1'
    fake_http.assert_requests([RecordedRequest('GET', url)])
    assert [sent.url for sent in fake_http.sent] == [url, url]
    fake_http.assert_all_responses_consumed()


@pytest.mark.parametrize(
    ('url', 'sent_url'),
    [
        pytest.param('https://Example.TEST/a b', 'https://example.test/a%20b', id='normalized'),
        pytest.param('unix:///var/run/test.sock/info', 'unix://%2Fvar%2Frun%2Ftest.sock/info', id='unix-socket'),
    ],
)
def test_fake_http_serves_a_call_whose_url_the_client_rewrites(fake_http, fake_http_response, url, sent_url):
    fake_http_response(url, b'ok')
    check = FixtureCheck('test', {}, [{}])

    assert check.http.get(url).content == b'ok'
    assert [sent.url for sent in fake_http.sent] == [sent_url]


@pytest.mark.parametrize(
    ('response', 'error', 'match'),
    [
        pytest.param(FakeHTTPResponse(elapsed=timedelta(seconds=1)), ValueError, 'elapsed', id='elapsed'),
        pytest.param(
            FakeHTTPResponse(stream_error=HTTPClientConnectionError('cut')),
            ValueError,
            'stream_error',
            id='stream_error',
        ),
        pytest.param(
            FakeHTTPResponse(history=[FakeHTTPResponse(status_code=302)]), ValueError, 'history', id='history'
        ),
        pytest.param(FakeHTTPResponse(peer_cert=b'cert'), ValueError, 'peer_cert', id='peer_cert'),
        pytest.param(FakeHTTPResponse(json_error=ValueError('bad')), ValueError, 'json_error', id='json_error'),
        pytest.param(FakeHTTPResponse(url='https://other.test/'), ValueError, 'url', id='url'),
        pytest.param(
            FakeHTTPResponse(content=b'raw', json_result={'a': 1}), ValueError, 'json_result', id='json_result-and-body'
        ),
        pytest.param(
            FakeHTTPResponse(content_chunks=[b'a', b'b']), ValueError, 'content_chunks', id='several-content_chunks'
        ),
        pytest.param(FakeHTTPResponse(lines=['a', '']), ValueError, 'lines', id='trailing-empty-line'),
        pytest.param(FakeHTTPResponse(lines=['a\n', 'b']), ValueError, 'lines', id='line-with-newline'),
        pytest.param(requests.Response(), TypeError, 'FakeHTTPResponse', id='requests-response'),
    ],
)
def test_fake_http_rejects_responses_it_cannot_send(fake_http, response, error, match):
    with pytest.raises(error, match=match):
        fake_http.register_response('GET', 'https://example.test/items', response)


def test_fake_http_serves_lines(fake_http):
    url = 'https://example.test/stream'
    fake_http.register_response('GET', url, FakeHTTPResponse(lines=[b'first', b'', b'third']))
    check = FixtureCheck('test', {}, [{}])

    assert list(check.http.get(url, stream=True).iter_lines()) == [b'first', b'', b'third']


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
