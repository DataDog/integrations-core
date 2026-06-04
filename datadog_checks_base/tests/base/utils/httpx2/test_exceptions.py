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
from datadog_checks.base.utils.httpx2 import HTTPXWrapper, _map_httpx_exception


@pytest.mark.parametrize(
    'raised,expected',
    [
        pytest.param(httpx2.ConnectTimeout('boom'), HTTPTimeoutError, id='connect-timeout'),
        pytest.param(httpx2.ReadTimeout('slow'), HTTPTimeoutError, id='read-timeout'),
        pytest.param(httpx2.PoolTimeout('pool'), HTTPTimeoutError, id='pool-timeout'),
        pytest.param(httpx2.ConnectError('refused'), HTTPConnectionError, id='connect-error'),
        pytest.param(httpx2.ReadError('mid-stream'), HTTPRequestError, id='read-error'),
        pytest.param(httpx2.LocalProtocolError('bad'), HTTPRequestError, id='local-protocol-error'),
        pytest.param(httpx2.RequestError('generic'), HTTPRequestError, id='request-error'),
    ],
)
def test_request_exception_mapping(raising_transport_factory, raised, expected):
    transport = raising_transport_factory(raised)
    http = HTTPXWrapper({}, {}, transport=transport)
    with pytest.raises(expected):
        http.get('http://example.test/')


def test_map_httpx_exception_routes_invalid_url():
    mapped = _map_httpx_exception(httpx2.InvalidURL('bad url'))
    assert isinstance(mapped, HTTPInvalidURLError)


def test_request_raises_invalid_url_error(raising_transport_factory):
    transport = raising_transport_factory(httpx2.InvalidURL('bad url'))
    http = HTTPXWrapper({}, {}, transport=transport)
    with pytest.raises(HTTPInvalidURLError):
        http.get('http://example.test/')
