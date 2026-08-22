# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from collections.abc import Iterator

import mock
import pytest
import requests
from urllib3.exceptions import ReadTimeoutError

from datadog_checks.base.utils.http import (
    _COMPAT_EXCEPTIONS,
    RequestsWrapper,
    ResponseWrapper,
    _backend_compat_type,
    _translate_requests_exception,
)
from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPConnectTimeoutError,
    HTTPError,
    HTTPInvalidURLError,
    HTTPReadTimeoutError,
    HTTPRequestError,
    HTTPSSLError,
    HTTPStatusError,
    HTTPTimeoutError,
)


@pytest.mark.parametrize(
    'raised, expected',
    [
        pytest.param(requests.exceptions.ConnectTimeout('boom'), HTTPConnectTimeoutError, id='connect-timeout'),
        pytest.param(requests.exceptions.ReadTimeout('slow'), HTTPReadTimeoutError, id='read-timeout'),
        pytest.param(requests.exceptions.Timeout('generic'), HTTPTimeoutError, id='generic-timeout'),
        pytest.param(requests.exceptions.ProxyError('proxy'), HTTPConnectionError, id='proxy-error'),
        pytest.param(requests.exceptions.ConnectionError('refused'), HTTPConnectionError, id='connection-error'),
        pytest.param(requests.exceptions.InvalidURL('bad-url'), HTTPInvalidURLError, id='invalid-url'),
        pytest.param(requests.exceptions.MissingSchema('no-scheme'), HTTPInvalidURLError, id='missing-schema'),
    ],
)
def test_transport_exception_mapping(raised, expected):
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', side_effect=raised):
        with pytest.raises(expected) as exc_info:
            http.get('http://example.test/')

    assert type(exc_info.value) is _COMPAT_EXCEPTIONS[expected]


def test_phase_specific_timeouts_share_generic_base():
    assert isinstance(HTTPConnectTimeoutError('connect'), HTTPTimeoutError)
    assert isinstance(HTTPReadTimeoutError('read'), HTTPTimeoutError)
    assert not isinstance(HTTPConnectTimeoutError('connect'), HTTPConnectionError)


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
        with pytest.raises(HTTPStatusError) as exc_info:
            wrapped.raise_for_status()
    assert exc_info.value.response is wrapped


@pytest.mark.parametrize(
    'raised, expected',
    [
        pytest.param(requests.exceptions.InvalidURL('bad'), HTTPInvalidURLError, id='invalid-url'),
        pytest.param(requests.exceptions.MissingSchema('no-scheme'), HTTPInvalidURLError, id='missing-schema'),
        pytest.param(requests.exceptions.InvalidSchema('bad-scheme'), HTTPInvalidURLError, id='invalid-schema'),
        pytest.param(requests.exceptions.URLRequired('no-url'), HTTPInvalidURLError, id='url-required'),
        pytest.param(requests.exceptions.SSLError('cert'), HTTPSSLError, id='ssl'),
        pytest.param(requests.exceptions.ConnectTimeout('boom'), HTTPConnectTimeoutError, id='connect-timeout'),
        pytest.param(requests.exceptions.ReadTimeout('slow'), HTTPReadTimeoutError, id='read-timeout'),
        pytest.param(requests.exceptions.Timeout('generic'), HTTPTimeoutError, id='generic-timeout'),
        pytest.param(requests.exceptions.ConnectionError('refused'), HTTPConnectionError, id='connection-error'),
        pytest.param(requests.exceptions.ProxyError('proxy'), HTTPConnectionError, id='proxy-error'),
        pytest.param(requests.exceptions.ContentDecodingError('decode'), HTTPRequestError, id='content-decoding'),
        pytest.param(requests.exceptions.InvalidHeader('multiple values'), HTTPRequestError, id='invalid-header'),
        pytest.param(requests.exceptions.HTTPError('500'), HTTPStatusError, id='http-error'),
        pytest.param(requests.exceptions.RequestException('generic'), HTTPRequestError, id='request-exception'),
        pytest.param(RuntimeError('not-requests'), HTTPError, id='non-requests-fallback'),
    ],
)
def test_translate_maps_requests_to_agnostic(raised, expected):
    result = _translate_requests_exception(raised)
    assert type(result) is _COMPAT_EXCEPTIONS[expected], (
        f"{type(raised).__name__} -> {type(result).__name__}, expected {expected.__name__}"
    )


def test_invalid_header_leaves_the_value_error_family():
    assert isinstance(requests.exceptions.InvalidHeader('multiple values'), ValueError)

    translated = _translate_requests_exception(requests.exceptions.InvalidHeader('multiple values'))

    assert not isinstance(translated, ValueError)


@pytest.mark.parametrize(
    'raised, still_caught_by',
    [
        pytest.param(
            requests.exceptions.ConnectTimeout('boom'),
            [requests.exceptions.Timeout, requests.exceptions.ConnectionError],
            id='connect-timeout',
        ),
        pytest.param(
            requests.exceptions.ReadTimeout('slow'),
            [requests.exceptions.Timeout, requests.exceptions.ReadTimeout],
            id='read-timeout-header-phase',
        ),
        pytest.param(
            requests.exceptions.ConnectionError('refused'),
            [requests.exceptions.ConnectionError],
            id='connection-error',
        ),
        pytest.param(
            requests.exceptions.SSLError('cert'),
            [requests.exceptions.SSLError, requests.exceptions.ConnectionError],
            id='ssl',
        ),
        pytest.param(requests.exceptions.HTTPError('500'), [requests.exceptions.HTTPError], id='status'),
        pytest.param(
            requests.exceptions.MissingSchema('no-scheme'),
            [requests.exceptions.MissingSchema, requests.exceptions.InvalidURL, ValueError],
            id='missing-schema',
        ),
        pytest.param(
            requests.exceptions.TooManyRedirects('loop'),
            [requests.exceptions.RequestException],
            id='fallthrough',
        ),
    ],
)
def test_translated_exceptions_keep_matching_the_requests_arms(raised, still_caught_by):
    translated = _translate_requests_exception(raised)

    assert isinstance(translated, requests.exceptions.RequestException)
    assert isinstance(translated, OSError)

    for arm in still_caught_by:
        assert isinstance(translated, arm), f'{type(raised).__name__} no longer caught by except {arm.__name__}'


def test_body_phase_read_timeout_keeps_matching_connection_error():
    raised = requests.exceptions.ConnectionError(ReadTimeoutError(None, 'http://example.test/', 'timed out'))

    translated = _translate_requests_exception(raised)

    assert isinstance(translated, HTTPReadTimeoutError)
    assert isinstance(translated, requests.exceptions.ConnectionError)


def test_compat_bases_do_not_leak_into_the_agnostic_tree():
    assert not isinstance(_translate_requests_exception(requests.exceptions.HTTPError('500')), HTTPRequestError)
    assert not isinstance(
        _translate_requests_exception(requests.exceptions.ConnectTimeout('boom')), HTTPConnectionError
    )
    for agnostic, compat in _COMPAT_EXCEPTIONS.items():
        assert compat.__bases__[0] is agnostic
        assert compat.__name__ == agnostic.__name__
        assert compat.__module__ == agnostic.__module__


def test_backend_compat_type_supports_backend_subclassing_agnostic():
    class BackendSubclass(json.JSONDecodeError):
        pass

    compat = _backend_compat_type(json.JSONDecodeError, BackendSubclass)

    assert issubclass(compat, json.JSONDecodeError)
    assert issubclass(compat, BackendSubclass)


def requests_exception_types():
    """Return requests' own RequestException subclasses."""
    found: dict[str, type] = {}
    pending = [requests.exceptions.RequestException]
    while pending:
        exc_type = pending.pop()
        if exc_type.__module__.split('.')[0] != 'requests':
            continue
        found[exc_type.__name__] = exc_type
        pending.extend(exc_type.__subclasses__())

    return sorted(found.values(), key=lambda exc_type: exc_type.__name__)


@pytest.mark.parametrize('exc_type', requests_exception_types(), ids=lambda exc_type: exc_type.__name__)
def test_every_requests_exception_lands_under_a_handled_agnostic_type(exc_type):
    translated = _translate_requests_exception(exc_type.__new__(exc_type))

    assert isinstance(translated, (HTTPRequestError, HTTPStatusError))


def test_a_non_requests_failure_reaches_the_caller_untranslated():
    http = RequestsWrapper({}, {})

    with mock.patch('requests.Session.get', side_effect=RuntimeError('not a requests failure')):
        with pytest.raises(RuntimeError, match='not a requests failure'):
            http.get('http://example.test/')


def test_translate_does_not_leak_raw_response():
    err = requests.exceptions.HTTPError('500 Server Error')
    err.response = object()
    result = _translate_requests_exception(err)
    assert isinstance(result, HTTPStatusError)
    assert result.response is None


def test_translate_converts_raw_request_to_agnostic_snapshot():
    request = requests.Request('GET', 'https://example.test/resource', headers={'X-Test-Header': 'original'}).prepare()
    err = requests.exceptions.HTTPError('500 Server Error', request=request)

    result = _translate_requests_exception(err)

    assert not isinstance(result.request, (requests.Request, requests.PreparedRequest))
    assert result.request.method == 'GET'
    assert result.request.url == 'https://example.test/resource'
    assert result.request.headers == {'X-Test-Header': 'original'}
    assert result.request.headers['x-test-header'] == 'original'

    request.headers['X-Test-Header'] = 'changed'
    assert result.request.headers == {'X-Test-Header': 'original'}


@pytest.mark.parametrize(
    'raised, expected',
    [
        pytest.param(requests.exceptions.ConnectionError('dropped'), HTTPConnectionError, id='connection-error'),
        pytest.param(requests.exceptions.ReadTimeout('slow'), HTTPReadTimeoutError, id='read-timeout'),
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


class TimeoutRawStream:
    def stream(self, chunk_size: int, decode_content: bool = False) -> Iterator[bytes]:
        assert chunk_size > 0
        assert decode_content
        yield b'first\n'
        raise ReadTimeoutError(None, None, 'slow')


def test_response_wrapper_maps_requests_wrapped_mid_stream_read_timeout() -> None:
    response = requests.Response()
    response.encoding = 'utf-8'
    response.raw = TimeoutRawStream()
    stream = ResponseWrapper(response, 1024).iter_lines(decode_unicode=True)

    assert next(stream) == 'first'
    with pytest.raises(HTTPReadTimeoutError, match='slow'):
        next(stream)


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


def test_json_parse_error_keeps_matching_requests_arms():
    response = FailingRead(requests.exceptions.JSONDecodeError('Expecting value', 'not json', 0))
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', return_value=response):
        wrapped = http.get('http://example.test/')
        with pytest.raises(requests.exceptions.JSONDecodeError):
            wrapped.json()


def test_auth_token_fetch_error_maps_to_agnostic():
    http = RequestsWrapper({}, {})
    http.auth_token_handler = mock.MagicMock()
    http.auth_token_handler.poll.side_effect = requests.exceptions.ConnectionError('token endpoint refused')
    with pytest.raises(HTTPConnectionError):
        http.get('http://example.test/')


class IterableFailingResponse:
    """Raw-response stand-in mirroring requests.Response.__iter__, which delegates to iter_content."""

    def __init__(self, exc):
        self._exc = exc

    def iter_content(self, chunk_size=1, decode_unicode=False):
        yield b'first'
        raise self._exc

    def __iter__(self):
        return self.iter_content(128)


def test_direct_iteration_maps_mid_stream_exceptions():
    response = IterableFailingResponse(requests.exceptions.ConnectionError('dropped'))
    http = RequestsWrapper({}, {})
    with mock.patch('requests.Session.get', return_value=response):
        wrapped = http.get('http://example.test/', stream=True)
        with pytest.raises(HTTPConnectionError):
            list(wrapped)
