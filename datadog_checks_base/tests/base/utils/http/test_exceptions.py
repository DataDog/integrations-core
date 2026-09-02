# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import mock
import pytest
import requests
from urllib3.exceptions import ReadTimeoutError

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientError,
    HTTPClientInvalidURLError,
    HTTPClientReadTimeoutError,
    HTTPClientRequestError,
    HTTPClientSSLError,
    HTTPClientStatusError,
    HTTPClientTimeoutError,
)
from datadog_checks.base.utils.requests_adapter import (
    _COMPAT_EXCEPTIONS,
    RequestsResponseAdapter,
    _backend_compat_type,
    _translate_requests_exception,
)

from . import common


@pytest.mark.parametrize(
    'raised, expected',
    [
        pytest.param(requests.exceptions.ConnectTimeout('boom'), HTTPClientConnectTimeoutError, id='connect-timeout'),
        pytest.param(requests.exceptions.ReadTimeout('slow'), HTTPClientReadTimeoutError, id='read-timeout'),
        pytest.param(requests.exceptions.Timeout('generic'), HTTPClientTimeoutError, id='generic-timeout'),
        pytest.param(requests.exceptions.ProxyError('proxy'), HTTPClientConnectionError, id='proxy-error'),
        pytest.param(requests.exceptions.ConnectionError('refused'), HTTPClientConnectionError, id='connection-error'),
        pytest.param(requests.exceptions.InvalidURL('bad-url'), HTTPClientInvalidURLError, id='invalid-url'),
        pytest.param(requests.exceptions.MissingSchema('no-scheme'), HTTPClientInvalidURLError, id='missing-schema'),
    ],
)
def test_transport_exception_mapping(raised, expected):
    transport = common.RequestsTransport()
    transport.raise_exception(raised)
    http = common.create_requests_client(transport)

    with pytest.raises(expected) as exc_info:
        http.get('http://example.test/')

    assert type(exc_info.value) is _COMPAT_EXCEPTIONS[expected]
    assert exc_info.value.request.method == 'GET'
    assert exc_info.value.request.url == 'http://example.test/'


def test_phase_specific_timeouts_share_generic_base():
    assert isinstance(HTTPClientConnectTimeoutError('connect'), HTTPClientTimeoutError)
    assert isinstance(HTTPClientReadTimeoutError('read'), HTTPClientTimeoutError)
    assert not isinstance(HTTPClientConnectTimeoutError('connect'), HTTPClientConnectionError)


def test_ssl_error_maps_to_http_ssl_error():
    transport = common.RequestsTransport()
    transport.raise_exception(requests.exceptions.SSLError('bad cert'))
    http = common.create_requests_client(transport)

    with pytest.raises(HTTPClientSSLError):
        http.get('http://example.test/')


def test_raise_for_status_maps_to_status_error():
    transport = common.RequestsTransport()
    transport.respond(status_code=404, content=b'missing')
    http = common.create_requests_client(transport)
    wrapped = http.get('http://example.test/')

    with pytest.raises(HTTPClientStatusError) as exc_info:
        wrapped.raise_for_status()

    assert exc_info.value.response is wrapped


@pytest.mark.parametrize(
    'raised, expected',
    [
        pytest.param(requests.exceptions.InvalidURL('bad'), HTTPClientInvalidURLError, id='invalid-url'),
        pytest.param(requests.exceptions.MissingSchema('no-scheme'), HTTPClientInvalidURLError, id='missing-schema'),
        pytest.param(requests.exceptions.InvalidSchema('bad-scheme'), HTTPClientInvalidURLError, id='invalid-schema'),
        pytest.param(requests.exceptions.URLRequired('no-url'), HTTPClientInvalidURLError, id='url-required'),
        pytest.param(requests.exceptions.SSLError('cert'), HTTPClientSSLError, id='ssl'),
        pytest.param(requests.exceptions.ConnectTimeout('boom'), HTTPClientConnectTimeoutError, id='connect-timeout'),
        pytest.param(requests.exceptions.ReadTimeout('slow'), HTTPClientReadTimeoutError, id='read-timeout'),
        pytest.param(requests.exceptions.Timeout('generic'), HTTPClientTimeoutError, id='generic-timeout'),
        pytest.param(requests.exceptions.ConnectionError('refused'), HTTPClientConnectionError, id='connection-error'),
        pytest.param(requests.exceptions.ProxyError('proxy'), HTTPClientConnectionError, id='proxy-error'),
        pytest.param(requests.exceptions.ContentDecodingError('decode'), HTTPClientRequestError, id='content-decoding'),
        pytest.param(requests.exceptions.HTTPError('500'), HTTPClientStatusError, id='http-error'),
        pytest.param(requests.exceptions.RequestException('generic'), HTTPClientRequestError, id='request-exception'),
        pytest.param(RuntimeError('not-requests'), HTTPClientError, id='non-requests-fallback'),
    ],
)
def test_translate_maps_requests_to_agnostic(raised, expected):
    result = _translate_requests_exception(raised)
    assert type(result) is _COMPAT_EXCEPTIONS[expected], (
        f"{type(raised).__name__} -> {type(result).__name__}, expected {expected.__name__}"
    )


def test_invalid_header_keeps_the_value_error_family():
    assert isinstance(requests.exceptions.InvalidHeader('multiple values'), ValueError)

    translated = _translate_requests_exception(requests.exceptions.InvalidHeader('multiple values'))

    assert isinstance(translated, HTTPClientRequestError)
    assert isinstance(translated, requests.exceptions.InvalidHeader)
    assert isinstance(translated, ValueError)


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

    assert isinstance(translated, HTTPClientReadTimeoutError)
    assert isinstance(translated, requests.exceptions.ConnectionError)


def test_compat_bases_do_not_leak_into_the_agnostic_tree():
    assert not isinstance(_translate_requests_exception(requests.exceptions.HTTPError('500')), HTTPClientRequestError)
    assert not isinstance(
        _translate_requests_exception(requests.exceptions.ConnectTimeout('boom')), HTTPClientConnectionError
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

    assert isinstance(translated, (HTTPClientRequestError, HTTPClientStatusError))


def test_a_non_requests_failure_reaches_the_caller_untranslated():
    transport = common.RequestsTransport()
    transport.raise_exception(RuntimeError('not a requests failure'))
    http = common.create_requests_client(transport)

    with pytest.raises(RuntimeError, match='not a requests failure'):
        http.get('http://example.test/')


def test_translate_adapts_attached_backend_response():
    response = requests.Response()
    response.status_code = 401
    response._content = b'unauthorized'
    error = requests.HTTPError('401 Client Error', response=response)

    translated = _translate_requests_exception(error)

    assert isinstance(translated.response, RequestsResponseAdapter)
    assert translated.response.status_code == 401
    assert translated.response.content == b'unauthorized'


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
        pytest.param(requests.exceptions.ConnectionError('dropped'), HTTPClientConnectionError, id='connection-error'),
        pytest.param(requests.exceptions.ReadTimeout('slow'), HTTPClientReadTimeoutError, id='read-timeout'),
    ],
)
@pytest.mark.parametrize('iter_method', ['iter_content', 'iter_lines'])
def test_stream_seam_maps_mid_stream_exceptions(raised, expected, iter_method):
    transport = common.RequestsTransport()
    transport.respond(stream_error=raised)
    http = common.create_requests_client(transport)
    wrapped = http.get('http://example.test/', stream=True)

    with pytest.raises(expected):
        list(getattr(wrapped, iter_method)())


def test_response_adapter_maps_requests_wrapped_mid_stream_read_timeout() -> None:
    transport = common.RequestsTransport()
    transport.respond(
        headers={'Content-Type': 'text/plain; charset=utf-8'},
        content_chunks=(b'first\n',),
        stream_error=ReadTimeoutError(None, None, 'slow'),
    )
    http = common.create_requests_client(transport)
    response = http.get('http://example.test/', stream=True)
    stream = response.iter_lines(decode_unicode=True)

    assert next(stream) == 'first'
    with pytest.raises(HTTPClientReadTimeoutError, match='slow'):
        next(stream)


@pytest.mark.parametrize(
    'read',
    [
        pytest.param(lambda r: r.content, id='content'),
        pytest.param(lambda r: r.text, id='text'),
        pytest.param(lambda r: r.json(), id='json'),
    ],
)
def test_buffered_seam_maps_exceptions(read):
    transport = common.RequestsTransport()
    transport.respond(stream_error=requests.exceptions.ConnectionError('dropped'))
    http = common.create_requests_client(transport)
    wrapped = http.get('http://example.test/', stream=True)

    with pytest.raises(HTTPClientConnectionError):
        read(wrapped)


def test_json_parse_error_converges_to_stdlib():
    transport = common.RequestsTransport()
    transport.respond(content=b'not json')
    http = common.create_requests_client(transport)
    wrapped = http.get('http://example.test/')

    with pytest.raises(json.JSONDecodeError) as exc_info:
        wrapped.json()

    assert exc_info.value.msg == 'Expecting value'
    assert exc_info.value.doc == 'not json'
    assert exc_info.value.pos == 0


def test_json_parse_error_keeps_matching_requests_arms():
    transport = common.RequestsTransport()
    transport.respond(content=b'not json')
    http = common.create_requests_client(transport)
    wrapped = http.get('http://example.test/')

    with pytest.raises(requests.exceptions.JSONDecodeError):
        wrapped.json()


def test_auth_token_fetch_error_maps_to_agnostic():
    http = RequestsWrapper({}, {})
    http.auth_token_handler = mock.MagicMock()
    http.auth_token_handler.poll.side_effect = requests.exceptions.ConnectionError('token endpoint refused')
    with pytest.raises(HTTPClientConnectionError):
        http.get('http://example.test/')


def test_direct_iteration_maps_mid_stream_exceptions():
    transport = common.RequestsTransport()
    transport.respond(
        content_chunks=(b'first',),
        stream_error=requests.exceptions.ConnectionError('dropped'),
    )
    http = common.create_requests_client(transport)
    wrapped = http.get('http://example.test/', stream=True)

    with pytest.raises(HTTPClientConnectionError):
        list(wrapped)
