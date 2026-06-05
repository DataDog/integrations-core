# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import httpx2
import pytest

from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPInvalidURLError,
    HTTPRequestError,
    HTTPTimeoutError,
)
from datadog_checks.base.utils.httpx2 import HTTPX2Wrapper, _map_httpx2_exception


@pytest.mark.parametrize(
    'raised,expected',
    [
        pytest.param(httpx2.ConnectTimeout('boom'), HTTPTimeoutError, id='connect-timeout'),
        pytest.param(httpx2.ReadTimeout('slow'), HTTPTimeoutError, id='read-timeout'),
        pytest.param(httpx2.PoolTimeout('pool'), HTTPTimeoutError, id='pool-timeout'),
        pytest.param(httpx2.ConnectError('refused'), HTTPConnectionError, id='connect-error'),
        pytest.param(httpx2.ReadError('mid-stream'), HTTPConnectionError, id='read-error'),
        pytest.param(httpx2.WriteError('broken-pipe'), HTTPConnectionError, id='write-error'),
        pytest.param(httpx2.CloseError('half-closed'), HTTPConnectionError, id='close-error'),
        pytest.param(httpx2.LocalProtocolError('bad'), HTTPRequestError, id='local-protocol-error'),
        pytest.param(httpx2.RequestError('generic'), HTTPRequestError, id='request-error'),
    ],
)
def test_request_exception_mapping(raising_transport_factory, raised, expected):
    transport = raising_transport_factory(raised)
    http = HTTPX2Wrapper({}, {}, transport=transport)
    with pytest.raises(expected):
        http.get('http://example.test/')


def test_map_httpx2_exception_routes_invalid_url():
    mapped = _map_httpx2_exception(httpx2.InvalidURL('bad url'))
    assert isinstance(mapped, HTTPInvalidURLError)


def test_request_raises_invalid_url_error(raising_transport_factory):
    transport = raising_transport_factory(httpx2.InvalidURL('bad url'))
    http = HTTPX2Wrapper({}, {}, transport=transport)
    with pytest.raises(HTTPInvalidURLError):
        http.get('http://example.test/')


@pytest.mark.parametrize(
    'raised,expected',
    [
        pytest.param(httpx2.ReadError('mid-stream'), HTTPConnectionError, id='read-error'),
        pytest.param(httpx2.ReadTimeout('slow'), HTTPTimeoutError, id='read-timeout'),
    ],
)
@pytest.mark.parametrize(
    'iter_method,iter_kwargs',
    [
        pytest.param('iter_lines', {}, id='iter_lines'),
        pytest.param('iter_lines', {'decode_unicode': True}, id='iter_lines-decoded'),
        pytest.param('iter_content', {}, id='iter_content-bytes'),
        pytest.param('iter_content', {'decode_unicode': True}, id='iter_content-decoded'),
    ],
)
def test_iter_methods_map_mid_stream_exceptions(
    mid_stream_raising_transport_factory, raised, expected, iter_method, iter_kwargs
):
    transport = mid_stream_raising_transport_factory(raised)
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    with pytest.raises(expected):
        list(getattr(response, iter_method)(**iter_kwargs))
