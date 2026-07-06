# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import mock
import pytest
import requests

from datadog_checks.base.utils.http import RequestsWrapper, _translate_requests_exception
from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPError,
    HTTPInvalidURLError,
    HTTPRequestError,
    HTTPSSLError,
    HTTPStatusError,
    HTTPTimeoutError,
)


@pytest.mark.parametrize(
    'raised, expected',
    [
        pytest.param(requests.exceptions.ConnectTimeout('boom'), HTTPTimeoutError, id='connect-timeout'),
        pytest.param(requests.exceptions.ReadTimeout('slow'), HTTPTimeoutError, id='read-timeout'),
        pytest.param(requests.exceptions.ProxyError('proxy'), HTTPConnectionError, id='proxy-error'),
        pytest.param(requests.exceptions.ConnectionError('refused'), HTTPConnectionError, id='connection-error'),
        pytest.param(requests.exceptions.InvalidURL('bad-url'), HTTPInvalidURLError, id='invalid-url'),
        pytest.param(requests.exceptions.MissingSchema('no-scheme'), HTTPInvalidURLError, id='missing-schema'),
    ],
)
def test_transport_exception_mapping(raised, expected):
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', side_effect=raised):
        with pytest.raises(expected):
            http.get('http://example.test/')


def test_ssl_error_maps_to_http_ssl_error():
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', side_effect=requests.exceptions.SSLError('bad cert')):
        with mock.patch.object(RequestsWrapper, 'fetch_intermediate_certs', return_value=[]):
            with pytest.raises(HTTPSSLError):
                http.get('https://example.test/')


def test_raise_for_status_maps_to_status_error():
    response = mock.MagicMock()
    response.raise_for_status.side_effect = requests.exceptions.HTTPError('404 Client Error')
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', return_value=response):
        wrapped = http.get('http://example.test/')
        with pytest.raises(HTTPStatusError):
            wrapped.raise_for_status()


# Group A: the translator as a pure function, over the full mapping table.
@pytest.mark.parametrize(
    'raised, expected',
    [
        pytest.param(requests.exceptions.InvalidURL('bad'), HTTPInvalidURLError, id='invalid-url'),
        pytest.param(requests.exceptions.MissingSchema('no-scheme'), HTTPInvalidURLError, id='missing-schema'),
        pytest.param(requests.exceptions.InvalidSchema('bad-scheme'), HTTPInvalidURLError, id='invalid-schema'),
        pytest.param(requests.exceptions.URLRequired('no-url'), HTTPInvalidURLError, id='url-required'),
        pytest.param(requests.exceptions.SSLError('cert'), HTTPSSLError, id='ssl'),
        pytest.param(requests.exceptions.ConnectTimeout('boom'), HTTPTimeoutError, id='connect-timeout'),
        pytest.param(requests.exceptions.ConnectionError('refused'), HTTPConnectionError, id='connection-error'),
        pytest.param(requests.exceptions.ProxyError('proxy'), HTTPConnectionError, id='proxy-error'),
        pytest.param(requests.exceptions.ContentDecodingError('decode'), HTTPRequestError, id='content-decoding'),
        pytest.param(requests.exceptions.HTTPError('500'), HTTPStatusError, id='http-error'),
        pytest.param(requests.exceptions.RequestException('generic'), HTTPRequestError, id='request-exception'),
        pytest.param(RuntimeError('not-requests'), HTTPError, id='non-requests-fallback'),
    ],
)
def test_translate_maps_requests_to_agnostic(raised, expected):
    result = _translate_requests_exception(raised)
    assert type(result) is expected, f"{type(raised).__name__} -> {type(result).__name__}, expected {expected.__name__}"


def test_translate_status_error_carries_response():
    sentinel = object()
    err = requests.exceptions.HTTPError('500 Server Error')
    err.response = sentinel
    result = _translate_requests_exception(err)
    assert isinstance(result, HTTPStatusError)
    assert result.response is sentinel


# Group B: the streaming seam. The failure surfaces only when the generator is consumed.
@pytest.mark.parametrize(
    'raised, expected',
    [
        pytest.param(requests.exceptions.ConnectionError('dropped'), HTTPConnectionError, id='connection-error'),
        pytest.param(requests.exceptions.ReadTimeout('slow'), HTTPTimeoutError, id='read-timeout'),
    ],
)
@pytest.mark.parametrize('iter_method', ['iter_content', 'iter_lines'])
def test_stream_seam_maps_mid_stream_exceptions(raised, expected, iter_method):
    response = mock.MagicMock()
    getattr(response, iter_method).side_effect = raised
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', return_value=response):
        wrapped = http.get('http://example.test/', stream=True)
        with pytest.raises(expected):
            list(getattr(wrapped, iter_method)())


class FailingRead:
    """Raw-response stand-in whose buffered reads raise the injected exception."""

    def __init__(self, exc):
        self._exc = exc

    @property
    def content(self):
        raise self._exc

    @property
    def text(self):
        raise self._exc

    def json(self, **kwargs):
        raise self._exc


# Group C: the buffered seam. content and text are properties, json is a method.
@pytest.mark.parametrize(
    'read',
    [
        pytest.param(lambda r: r.content, id='content'),
        pytest.param(lambda r: r.text, id='text'),
        pytest.param(lambda r: r.json(), id='json'),
    ],
)
def test_buffered_seam_maps_exceptions(read):
    response = FailingRead(requests.exceptions.ConnectionError('dropped'))
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', return_value=response):
        wrapped = http.get('http://example.test/')
        with pytest.raises(HTTPConnectionError):
            read(wrapped)


# Group D: a malformed body must converge to the stdlib json.JSONDecodeError, not an agnostic type.
def test_json_parse_error_converges_to_stdlib():
    response = FailingRead(requests.exceptions.JSONDecodeError('Expecting value', 'not json', 0))
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', return_value=response):
        wrapped = http.get('http://example.test/')
        with pytest.raises(json.JSONDecodeError) as exc_info:
            wrapped.json()
    assert exc_info.value.msg == 'Expecting value'
    assert exc_info.value.doc == 'not json'
    assert exc_info.value.pos == 0
